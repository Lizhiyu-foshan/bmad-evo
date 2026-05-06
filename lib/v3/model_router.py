"""
BMAD-EVO v3.1 - ModelRouter
模型智能路由器 (GLM Coding Plan)

功能:
- 为每个角色选择最优 GLM 模型
- 配置备选模型
- 根据角色职责匹配模型能力
- 考虑上下文窗口预算
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ModelCapability(Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    ARCHITECTURE = "architecture"
    ANALYSIS = "analysis"
    WRITING = "writing"
    CREATIVE = "creative"
    LOGIC = "logic"
    LONG_CONTEXT = "long_context"
    SPEED = "speed"
    COST_EFFICIENT = "cost_efficient"
    MULTIMODAL = "multimodal"
    REASONING = "reasoning"


@dataclass
class ModelConfig:
    id: str
    name: str
    provider: str
    context_window: int
    output_window: int
    capabilities: List[ModelCapability]
    strengths: List[str]
    weaknesses: List[str]
    cost_tier: str
    typical_latency: str


@dataclass
class RoleModelMapping:
    role_id: str
    primary_model: str
    fallback_models: List[str]
    reasoning: str


@dataclass
class RoutingResult:
    mappings: List[RoleModelMapping]
    total_roles: int
    model_usage: Dict[str, int]
    estimated_cost_tier: str
    model_used: str = ""
    execution_time: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mappings": [asdict(m) for m in self.mappings],
            "total_roles": self.total_roles,
            "model_usage": self.model_usage,
            "estimated_cost_tier": self.estimated_cost_tier,
            "model_used": self.model_used,
            "execution_time": self.execution_time,
            "error": self.error,
        }


AVAILABLE_MODELS = {
    "glm-5.1": ModelConfig(
        id="glm-5.1",
        name="GLM-5.1 旗舰 (推理级)",
        provider="zhipu",
        context_window=200000,
        output_window=128000,
        capabilities=[
            ModelCapability.CODE_GENERATION,
            ModelCapability.ARCHITECTURE,
            ModelCapability.REASONING,
            ModelCapability.LONG_CONTEXT,
            ModelCapability.LOGIC,
            ModelCapability.MULTIMODAL,
        ],
        strengths=[
            "复杂代码",
            "深度推理",
            "长程Agent",
            "系统架构",
            "多文件项目",
            "空间/UI理解",
            "Reasoning模式",
        ],
        weaknesses=["成本较高", "延迟较高"],
        cost_tier="high",
        typical_latency="slow",
    ),
    "glm-4.7": ModelConfig(
        id="glm-4.7",
        name="GLM-4.7 全能主力",
        provider="zhipu",
        context_window=200000,
        output_window=128000,
        capabilities=[
            ModelCapability.CODE_GENERATION,
            ModelCapability.CODE_REVIEW,
            ModelCapability.ANALYSIS,
            ModelCapability.WRITING,
            ModelCapability.LOGIC,
            ModelCapability.LONG_CONTEXT,
            ModelCapability.COST_EFFICIENT,
        ],
        strengths=[
            "通用编码",
            "多轮对话",
            "工具调用",
            "前端/后端",
            "文档生成",
            "长上下文",
            "稳定生产级",
        ],
        weaknesses=["极限推理不如GLM-5.1"],
        cost_tier="medium",
        typical_latency="medium",
    ),
    "glm-4.7-flash": ModelConfig(
        id="glm-4.7-flash",
        name="GLM-4.7-Flash 轻量开源",
        provider="zhipu",
        context_window=200000,
        output_window=128000,
        capabilities=[
            ModelCapability.SPEED,
            ModelCapability.COST_EFFICIENT,
            ModelCapability.CODE_GENERATION,
            ModelCapability.CODE_REVIEW,
        ],
        strengths=["低延迟", "轻量Agent", "快速实验", "免费权重"],
        weaknesses=["复杂任务精度略低"],
        cost_tier="low",
        typical_latency="fast",
    ),
    "glm-4.7-flashx": ModelConfig(
        id="glm-4.7-flashx",
        name="GLM-4.7-FlashX 云端极速",
        provider="zhipu",
        context_window=200000,
        output_window=128000,
        capabilities=[
            ModelCapability.SPEED,
            ModelCapability.CODE_GENERATION,
            ModelCapability.COST_EFFICIENT,
        ],
        strengths=["高并发", "生产低延迟", "批量任务", "API优先", "速度最优"],
        weaknesses=["复杂推理能力有限"],
        cost_tier="low",
        typical_latency="fast",
    ),
    "glm-4.6": ModelConfig(
        id="glm-4.6",
        name="GLM-4.6 上一代主力",
        provider="zhipu",
        context_window=200000,
        output_window=128000,
        capabilities=[
            ModelCapability.CODE_GENERATION,
            ModelCapability.LONG_CONTEXT,
            ModelCapability.ANALYSIS,
        ],
        strengths=["稳定编码", "长上下文", "通用编程", "兼容旧工作流"],
        weaknesses=["能力不如GLM-4.7"],
        cost_tier="low",
        typical_latency="medium",
    ),
    "glm-4.6v": ModelConfig(
        id="glm-4.6v",
        name="GLM-4.6V 多模态编码",
        provider="zhipu",
        context_window=128000,
        output_window=128000,
        capabilities=[
            ModelCapability.MULTIMODAL,
            ModelCapability.CODE_GENERATION,
        ],
        strengths=[
            "设计图转代码",
            "视觉调试",
            "截图转HTML/CSS",
            "UI还原",
            "多模态理解",
        ],
        weaknesses=["纯文本任务不如GLM-4.7", "上下文窗口较小(128K)"],
        cost_tier="medium",
        typical_latency="medium",
    ),
    "glm-4.5-air": ModelConfig(
        id="glm-4.5-air",
        name="GLM-4.5-Air 超轻量",
        provider="zhipu",
        context_window=128000,
        output_window=128000,
        capabilities=[
            ModelCapability.SPEED,
            ModelCapability.COST_EFFICIENT,
        ],
        strengths=["极简场景", "快速补全", "低资源", "测试环境"],
        weaknesses=["复杂任务能力有限", "上下文窗口较小(128K)"],
        cost_tier="low",
        typical_latency="fast",
    ),
}


class ModelRouter:
    """
    模型智能路由器 (GLM Coding Plan)

    根据角色特性、任务需求、上下文预算为每个角色选择最优 GLM 模型。
    """

    def __init__(self):
        from ..config_loader import get_model_for_component, get_timeout, get_config
        self.primary_model, self.fallback_model = get_model_for_component("model_router")
        _cfg = get_config()
        self.absolute_fallback = _cfg["models"]["absolute_fallback"]
        self.timeout = get_timeout("model_router")
        self.models = AVAILABLE_MODELS
        logger.info(f"ModelRouter initialized with {len(self.models)} GLM models")

    def route(
        self,
        roles: List[Dict[str, Any]],
        task_type: str,
        complexity_score: int,
        budget_constraint: Optional[str] = None,
    ) -> RoutingResult:
        import time

        start_time = time.time()

        logger.info(
            f"Routing models for {len(roles)} roles "
            f"(task_type={task_type}, complexity={complexity_score})"
        )

        prompt = self._build_routing_prompt(
            roles, task_type, complexity_score, budget_constraint
        )

        try:
            result = self._call_model(self.primary_model, prompt)
            model_used = self.primary_model
        except Exception as e:
            logger.warning(f"Primary model failed: {e}, using fallback")
            try:
                result = self._call_model(self.fallback_model, prompt)
                model_used = self.fallback_model
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}, trying absolute fallback")
                try:
                    result = self._call_model(self.absolute_fallback, prompt)
                    model_used = self.absolute_fallback
                except Exception as e3:
                    logger.error(f"Absolute fallback also failed: {e3}")
                    return self._heuristic_route(
                        roles,
                        task_type,
                        complexity_score,
                        budget_constraint,
                        execution_time=time.time() - start_time,
                        error=f"All models failed: {e}, {e2}, {e3}",
                    )

        execution_time = time.time() - start_time

        try:
            routing_result = self._parse_routing_result(
                result, roles, model_used, execution_time
            )
            logger.info(
                f"Routing completed: {len(routing_result.mappings)} mappings, "
                f"cost_tier={routing_result.estimated_cost_tier}"
            )
            return routing_result
        except Exception as e:
            logger.error(f"Failed to parse routing result: {e}")
            return self._heuristic_route(
                roles,
                task_type,
                complexity_score,
                budget_constraint,
                execution_time=execution_time,
                error=str(e),
            )

    def _build_routing_prompt(
        self,
        roles: List[Dict[str, Any]],
        task_type: str,
        complexity_score: int,
        budget_constraint: Optional[str],
    ) -> str:
        roles_info = []
        for role in roles:
            roles_info.append(
                {
                    "id": role.get("id"),
                    "name": role.get("name"),
                    "description": role.get("description", ""),
                    "responsibilities": role.get("responsibilities", []),
                    "required_skills": role.get("required_skills", []),
                }
            )

        models_info = []
        for model_id, config in self.models.items():
            models_info.append(
                {
                    "id": model_id,
                    "name": config.name,
                    "context_window": config.context_window,
                    "output_window": config.output_window,
                    "strengths": config.strengths,
                    "weaknesses": config.weaknesses,
                    "cost_tier": config.cost_tier,
                    "latency": config.typical_latency,
                }
            )

        budget_str = (
            f"\n- **预算约束**: {budget_constraint}" if budget_constraint else ""
        )

        return f"""你是一个智能模型路由专家。请为每个角色选择最合适的 GLM 模型。

## 任务信息
- **任务类型**: {task_type}
- **复杂度评分**: {complexity_score}/10
{budget_str}

## 可用 GLM 模型
```json
{json.dumps(models_info, indent=2, ensure_ascii=False)}
```

## 需要分配的角色
```json
{json.dumps(roles_info, indent=2, ensure_ascii=False)}
```

## 路由规则

### 模型选择原则
1. **深度推理角色**（架构设计、系统规划）→ glm-5.1 (旗舰推理级)
2. **代码开发角色**（开发、重构）→ glm-5.1 或 glm-4.7 (代码能力强)
3. **分析规划角色**（需求分析、产品经理）→ glm-4.7 (全能主力)
4. **快速审查角色**（QA、测试）→ glm-4.7-flash 或 glm-4.7-flashx (速度快)
5. **极简单任务** → glm-4.5-air 或 glm-4.7-flash (成本最低)
6. **多模态任务**（UI设计、截图转码）→ glm-4.6v (视觉能力)

### 上下文预算考虑
- 每个模型有 200K 输入窗口（glm-4.6v/glm-4.5-air 为 128K）
- 预留 20% 余量防止幻觉
- 如果上下文积累过多，考虑用更大窗口的模型

### 备选模型配置
每个角色必须配置2-3个备选模型（按优先级排序），当主模型失败时按顺序回退。

### 成本考虑
- 低预算: 优先使用 glm-4.7-flash, glm-4.5-air
- 中等预算: 平衡使用 glm-4.7, glm-4.7-flash
- 高预算: 优先使用 glm-5.1

## 输出格式
必须返回有效的 JSON，不要包含任何其他文字：

```json
{{{{
  "mappings": [
    {{{{
      "role_id": "角色id",
      "primary_model": "主模型id",
      "fallback_models": ["备选1", "备选2"],
      "reasoning": "选择理由"
    }}}}
  ],
  "estimated_cost_tier": "low|medium|high",
  "optimization_notes": "优化建议"
}}}}
```
"""

    def _call_model(self, model: str, prompt: str) -> str:
        from ..opencode_adapter import call_model
        return call_model(model, prompt, timeout=self.timeout)

    def _parse_routing_result(
        self,
        raw_output: str,
        roles: List[Dict[str, Any]],
        model_used: str,
        execution_time: float,
    ) -> RoutingResult:
        json_str = self._extract_json(raw_output)
        data = json.loads(json_str)

        mappings_data = data.get("mappings", [])
        mappings = []
        model_usage = {}

        for mapping_data in mappings_data:
            role_id = mapping_data.get("role_id")
            primary = mapping_data.get("primary_model")

            model_usage[primary] = model_usage.get(primary, 0) + 1

            mapping = RoleModelMapping(
                role_id=role_id,
                primary_model=primary,
                fallback_models=mapping_data.get("fallback_models", []),
                reasoning=mapping_data.get("reasoning", ""),
            )
            mappings.append(mapping)

        mapped_role_ids = {m.role_id for m in mappings}
        for role in roles:
            if role.get("id") not in mapped_role_ids:
                mappings.append(
                    RoleModelMapping(
                        role_id=role.get("id"),
                        primary_model=self.primary_model,
                        fallback_models=[self.fallback_model],
                        reasoning="Default fallback mapping",
                    )
                )
                model_usage[self.primary_model] = model_usage.get(self.primary_model, 0) + 1

        return RoutingResult(
            mappings=mappings,
            total_roles=len(mappings),
            model_usage=model_usage,
            estimated_cost_tier=data.get("estimated_cost_tier", "medium"),
            model_used=model_used,
            execution_time=execution_time,
        )

    def _heuristic_route(
        self,
        roles: List[Dict[str, Any]],
        task_type: str,
        complexity_score: int,
        budget_constraint: Optional[str],
        execution_time: float = 0.0,
        error: Optional[str] = None,
    ) -> RoutingResult:
        mappings = []
        model_usage = {}

        for role in roles:
            role_id = role.get("id")
            role_name = role.get("name", "").lower()
            responsibilities = [r.lower() for r in role.get("responsibilities", [])]
            skills = [s.lower() for s in role.get("required_skills", [])]

            is_code_related = any(
                kw in role_name or any(kw in r for r in responsibilities)
                for kw in [
                    "开发",
                    "代码",
                    "测试",
                    "架构",
                    "programming",
                    "code",
                    "test",
                ]
            )
            is_analysis = any(
                kw in role_name or any(kw in r for r in responsibilities)
                for kw in ["分析", "产品", "需求", "analysis", "product", "requirement"]
            )
            is_architecture = any(
                kw in role_name or any(kw in r for r in responsibilities)
                for kw in ["架构", "设计", "architect", "design", "system"]
            )
            is_multimodal = any(
                kw in role_name or any(kw in r for r in responsibilities)
                for kw in ["UI", "ux", "界面", "视觉", "设计图", "视觉"]
            )

            if budget_constraint == "low":
                primary = self._pick_model_by_tier("low")
            elif is_architecture or complexity_score >= 8:
                primary = self._pick_model_by_tier("high")
            elif is_code_related and complexity_score >= 6:
                primary = self._pick_model_by_tier("high")
            elif is_code_related:
                primary = self.primary_model
            elif is_multimodal:
                primary = self._pick_model_by_capability("multimodal")
            elif is_analysis:
                primary = self.primary_model
            else:
                primary = self.primary_model

            fallbacks = self._build_fallbacks(primary)

            model_usage[primary] = model_usage.get(primary, 0) + 1

            mappings.append(
                RoleModelMapping(
                    role_id=role_id,
                    primary_model=primary,
                    fallback_models=fallbacks,
                    reasoning=(
                        f"Heuristic: code_related={is_code_related}, "
                        f"analysis={is_analysis}, architecture={is_architecture}"
                    ),
                )
            )

        high_tier = [mid for mid, mc in self.models.items() if mc.cost_tier == "high"]
        low_tier = [mid for mid, mc in self.models.items() if mc.cost_tier == "low"]

        if any(m in model_usage and model_usage[m] > len(roles) / 2 for m in high_tier):
            cost_tier = "high"
        elif any(m in model_usage and model_usage[m] > len(roles) / 2 for m in low_tier):
            cost_tier = "low"
        else:
            cost_tier = "medium"

        return RoutingResult(
            mappings=mappings,
            total_roles=len(mappings),
            model_usage=model_usage,
            estimated_cost_tier=cost_tier,
            model_used="heuristic",
            execution_time=execution_time,
            error=error,
        )

    def _extract_json(self, text: str) -> str:
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start : end + 1]

        return text

    def _pick_model_by_tier(self, tier: str) -> str:
        for mid, mc in self.models.items():
            if mc.cost_tier == tier:
                return mid
        return self.primary_model

    def _pick_model_by_capability(self, cap: str) -> str:
        try:
            capability = ModelCapability(cap)
        except ValueError:
            return self.primary_model
        for mid, mc in self.models.items():
            if capability in mc.capabilities:
                return mid
        return self.primary_model

    def _build_fallbacks(self, primary: str) -> List[str]:
        fallbacks = []
        for m in [self.fallback_model, self.primary_model, self.absolute_fallback]:
            if m != primary and m not in fallbacks:
                fallbacks.append(m)
        if not fallbacks:
            fallbacks = [self.fallback_model]
        return fallbacks[:2]

    def get_model_for_role(
        self, role_id: str, routing_result: RoutingResult
    ) -> Optional[RoleModelMapping]:
        for mapping in routing_result.mappings:
            if mapping.role_id == role_id:
                return mapping
        return None

    def get_fallback_chain(
        self, role_id: str, routing_result: Optional[RoutingResult] = None
    ) -> List[str]:
        default_chain = [self.primary_model, self.fallback_model, self.absolute_fallback]

        if routing_result is None:
            return default_chain

        try:
            mapping = self.get_model_for_role(role_id, routing_result)
            if mapping:
                return [mapping.primary_model] + mapping.fallback_models
        except Exception:
            pass

        return default_chain


def route_models(
    roles: List[Dict[str, Any]],
    task_type: str,
    complexity_score: int,
    budget_constraint: Optional[str] = None,
) -> RoutingResult:
    router = ModelRouter()
    return router.route(roles, task_type, complexity_score, budget_constraint)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Model Router (GLM)")
    parser.add_argument("--roles-file", required=True, help="JSON file with roles")
    parser.add_argument("--type", default="general", help="Task type")
    parser.add_argument("--complexity", type=int, default=5, help="Complexity score")
    parser.add_argument("--budget", help="Budget constraint (low/medium/high)")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    with open(args.roles_file, "r") as f:
        roles = json.load(f)

    result = route_models(roles, args.type, args.complexity, args.budget)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
