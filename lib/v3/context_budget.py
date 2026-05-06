"""
BMAD-EVO v3.1 - Context Budget Manager
上下文预算管理器

确保任务分解和执行不超出模型上下文窗口，预留 20% 余量防止幻觉。

功能:
- 管理各模型的上下文窗口限制
- 估算 token 消耗量
- 检查任务预算是否充足
- 提供超限时的拆分建议
"""

import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

from ..config_loader import get_config, get_context_window, get_quality_threshold

logger = logging.getLogger(__name__)


def _build_model_context_windows() -> Dict[str, Dict]:
    cfg = get_config()
    windows = cfg["models"]["context_windows"]
    result = {}
    tier_map = {
        "glm-5.1": ("GLM-5.1 旗舰 (推理级)", "flagship"),
        "glm-4.7": ("GLM-4.7 全能主力", "standard"),
        "glm-4.7-flash": ("GLM-4.7-Flash 轻量开源", "lightweight"),
        "glm-4.7-flashx": ("GLM-4.7-FlashX 云端极速", "fast"),
        "glm-4.6": ("GLM-4.6 上一代主力", "legacy"),
        "glm-4.6v": ("GLM-4.6V 多模态编码", "multimodal"),
        "glm-4.5-air": ("GLM-4.5-Air 超轻量", "ultralight"),
        "kimi-coding/k2.6": ("Kimi K2.6 绝对回退", "absolute_fallback"),
    }
    for model_id, ctx in windows.items():
        name, tier = tier_map.get(model_id, (model_id, "unknown"))
        result[model_id] = {
            "input": ctx["input"],
            "output": ctx["output"],
            "name": name,
            "tier": tier,
        }
    return result


MODEL_CONTEXT_WINDOWS = _build_model_context_windows()

HEADROOM_RATIO = get_quality_threshold("context_headroom_ratio", 0.20)


@dataclass
class TokenBudget:
    model_id: str
    total_input_capacity: int
    reserved_headroom: int
    usable_input: int
    max_output: int
    system_prompt_tokens: int
    context_tokens: int
    available_for_task: int

    @property
    def is_sufficient(self) -> bool:
        return self.available_for_task > 1000

    @property
    def utilization_pct(self) -> float:
        if self.total_input_capacity == 0:
            return 100.0
        consumed = self.total_input_capacity - self.available_for_task
        return round(consumed / self.total_input_capacity * 100, 1)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["is_sufficient"] = self.is_sufficient
        d["utilization_pct"] = self.utilization_pct
        return d


@dataclass
class BudgetCheckResult:
    sufficient: bool
    model_id: str
    budget: TokenBudget
    warnings: List[str]
    suggestions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sufficient": self.sufficient,
            "model_id": self.model_id,
            "budget": self.budget.to_dict(),
            "warnings": self.warnings,
            "suggestions": self.suggestions,
        }


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    Conservative: ~1 token per 3 chars for mixed CJK/ASCII content.
    """
    if not text:
        return 0
    return max(1, len(text) // 3)


class ContextBudgetManager:
    """
    Manages context window budgets across the workflow.

    Ensures:
    1. Each sub-task prompt fits within the assigned model context window
    2. 20% headroom reserved to prevent hallucination
    3. Accumulated context from previous roles doesn't overflow
    4. Suggestions for splitting tasks when budget is insufficient
    """

    def __init__(self):
        self.model_windows = MODEL_CONTEXT_WINDOWS

    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        return self.model_windows.get(model_id)

    def get_usable_input(self, model_id: str) -> int:
        info = self.model_windows.get(model_id)
        if not info:
            return 100000
        return int(info["input"] * (1 - HEADROOM_RATIO))

    def get_max_output(self, model_id: str) -> int:
        info = self.model_windows.get(model_id)
        if not info:
            return 32000
        return info["output"]

    def check_budget(
        self,
        model_id: str,
        system_prompt: str,
        context_from_previous: str,
        task_description: str,
        estimated_output_tokens: int = 4000,
    ) -> BudgetCheckResult:
        info = self.model_windows.get(model_id)
        if not info:
            return BudgetCheckResult(
                sufficient=False,
                model_id=model_id,
                budget=TokenBudget(
                    model_id=model_id,
                    total_input_capacity=0,
                    reserved_headroom=0,
                    usable_input=0,
                    max_output=0,
                    system_prompt_tokens=0,
                    context_tokens=0,
                    available_for_task=0,
                ),
                warnings=[f"Unknown model: {model_id}"],
                suggestions=["Use a known GLM model"],
            )

        total_input = info["input"]
        headroom = int(total_input * HEADROOM_RATIO)
        usable = total_input - headroom

        sys_tokens = estimate_tokens(system_prompt)
        ctx_tokens = estimate_tokens(context_from_previous)
        task_tokens = estimate_tokens(task_description)

        total_consumed = sys_tokens + ctx_tokens + task_tokens
        available = usable - total_consumed

        budget = TokenBudget(
            model_id=model_id,
            total_input_capacity=total_input,
            reserved_headroom=headroom,
            usable_input=usable,
            max_output=info["output"],
            system_prompt_tokens=sys_tokens,
            context_tokens=ctx_tokens + task_tokens,
            available_for_task=available,
        )

        warnings = []
        suggestions = []

        if available < estimated_output_tokens:
            warnings.append(
                f"Output budget ({estimated_output_tokens} tokens) may exceed "
                f"available capacity ({available} tokens)"
            )
            suggestions.append("Reduce context from previous phases (summarize)")
            suggestions.append("Split this task into smaller sub-tasks")

        if ctx_tokens > usable * 0.6:
            warnings.append(
                f"Context from previous phases ({ctx_tokens} tokens) occupies "
                f">{int(0.6 * 100)}% of usable input window"
            )
            suggestions.append("Summarize previous outputs before passing as context")

        if available < 1000:
            warnings.append(
                "Very little room left for task execution - high hallucination risk"
            )
            suggestions.append(
                "Switch to a model with larger context window (e.g., glm-5.1)"
            )
            suggestions.append("Split the task and reduce context passing")

        sufficient = available >= estimated_output_tokens and available >= 1000

        return BudgetCheckResult(
            sufficient=sufficient,
            model_id=model_id,
            budget=budget,
            warnings=warnings,
            suggestions=suggestions,
        )

    def check_workflow_budget(
        self,
        roles: List[Dict[str, Any]],
        model_routing: Dict[str, List[str]],
        task_description: str,
    ) -> List[Dict[str, Any]]:
        results = []
        accumulated_context = ""

        for role in roles:
            role_id = role.get("id") or role.get("name")
            model_chain = model_routing.get(role_id, ["glm-4.7"])
            primary_model = model_chain[0] if model_chain else "glm-4.7"

            system_prompt = role.get("description", "") + " ".join(
                role.get("responsibilities", [])
            )

            check = self.check_budget(
                model_id=primary_model,
                system_prompt=system_prompt,
                context_from_previous=accumulated_context,
                task_description=task_description,
            )

            results.append(
                {
                    "role_id": role_id,
                    "role_name": role.get("name") or role.get("title", role_id),
                    "model": primary_model,
                    "check": check.to_dict(),
                }
            )

            accumulated_context += f"\n[{role_id} output placeholder]\n"

        return results

    def suggest_task_split(
        self,
        model_id: str,
        total_estimated_tokens: int,
    ) -> Dict[str, Any]:
        usable = self.get_usable_input(model_id)

        if total_estimated_tokens <= usable:
            return {"needs_split": False, "current_model": model_id}

        for mid, info in sorted(
            self.model_windows.items(),
            key=lambda x: x[1]["input"],
            reverse=True,
        ):
            if int(info["input"] * (1 - HEADROOM_RATIO)) >= total_estimated_tokens:
                return {
                    "needs_split": False,
                    "suggested_model": mid,
                    "reason": f"Switch to {info['name']} for larger context",
                }

        num_splits = (total_estimated_tokens // usable) + 1
        return {
            "needs_split": True,
            "suggested_splits": num_splits,
            "reason": (
                f"Task too large even for largest model, "
                f"split into {num_splits} sub-tasks"
            ),
        }

    def format_budget_report(self, budget_results: List[Dict[str, Any]]) -> str:
        lines = ["\n" + "=" * 70, "Context Budget Report", "=" * 70, ""]

        all_sufficient = True
        for result in budget_results:
            check = result["check"]
            status = "OK" if check["sufficient"] else "OVER"
            if not check["sufficient"]:
                all_sufficient = False

            lines.append(
                f"  [{status}] {result['role_name']:<20} "
                f"Model: {result['model']:<15} "
                f"Available: {check['budget']['available_for_task']:>8} tokens "
                f"({check['budget']['utilization_pct']}% used)"
            )

            for w in check["warnings"]:
                lines.append(f"       WARNING: {w}")

        lines.append("")
        if all_sufficient:
            lines.append("All roles within budget.")
        else:
            lines.append("Some roles exceed budget - see suggestions above.")

        lines.append("=" * 70)
        return "\n".join(lines)
