"""
BMAD-EVO v4.0 - Thinking Chain Engine
思考链引擎 — 增量数据采集 + 双向反馈 + 自我反思

核心改进（相比v3.1单向流）:
1. 增量数据采集: 每个角色执行前自动识别并收集该角色专属的数据需求
2. 双向反馈循环: 后续角色可以向前置角色发送反馈，触发重新分析
3. 自我反思链: 最终环节评估整个报告的立场、观点、遗漏、假设合理性
4. 分析模式分流: 简单分析用单向流，复杂分析用思考链

v3.1:  [数据采集] → R1 → R2 → R3 → ... → Rn → [汇总]
v4.0:  [初始采集] → R1[+新采集] ⇄ R2[+新采集] ⇄ ... ⇄ Rn[+新采集] → [自我反思] → [修正]
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple

from ..config_loader import (
    get_model_for_component,
    get_thinking_chain_config,
)

logger = logging.getLogger(__name__)


class AnalysisMode(Enum):
    SIMPLE = "simple"
    COMPLEX_THINKING_CHAIN = "complex_thinking_chain"


@dataclass
class DataCollectionSpec:
    """单个角色的数据采集规格"""
    role_name: str
    queries: List[str]
    sources: List[str]
    priority: str  # "critical", "important", "supplementary"
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FeedbackMessage:
    """角色间的反馈消息"""
    from_role: str
    to_role: str
    feedback_type: str  # "data_gap", "assumption_challenge", "logic_error", "scope_expansion"
    content: str
    suggested_action: str  # "re_analyze", "supplement_data", "revise_conclusion", "acknowledge"
    priority: str  # "high", "medium", "low"
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReflectionIssue:
    """自我反思发现的问题"""
    category: str  # "data_staleness", "missing_perspective", "unvalidated_assumption",
                   # "logical_gap", "contradiction", "oversimplification", "bias"
    description: str
    affected_roles: List[str]
    severity: str  # "critical", "high", "medium", "low"
    suggested_fix: str
    requires_re_execution: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThinkingChainState:
    """思考链的全局状态"""
    analysis_mode: AnalysisMode
    task_description: str
    role_execution_order: List[str]
    completed_roles: List[str] = field(default_factory=list)
    pending_feedback: List[FeedbackMessage] = field(default_factory=list)
    resolved_feedback: List[FeedbackMessage] = field(default_factory=list)
    data_collection_specs: Dict[str, DataCollectionSpec] = field(default_factory=dict)
    collected_data: Dict[str, str] = field(default_factory=dict)
    role_outputs: Dict[str, str] = field(default_factory=dict)
    reflection_issues: List[ReflectionIssue] = field(default_factory=list)
    re_execution_count: Dict[str, int] = field(default_factory=dict)
    max_re_executions_per_role: int = 2
    max_reflection_rounds: int = 2
    current_reflection_round: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "analysis_mode": self.analysis_mode.value,
            "task_description": self.task_description,
            "role_execution_order": self.role_execution_order,
            "completed_roles": self.completed_roles,
            "pending_feedback": [f.to_dict() for f in self.pending_feedback],
            "resolved_feedback": [f.to_dict() for f in self.resolved_feedback],
            "data_collection_specs": {k: v.to_dict() for k, v in self.data_collection_specs.items()},
            "collected_data": self.collected_data,
            "reflection_issues": [i.to_dict() for i in self.reflection_issues],
            "re_execution_count": self.re_execution_count,
            "max_re_executions_per_role": self.max_re_executions_per_role,
            "max_reflection_rounds": self.max_reflection_rounds,
            "current_reflection_round": self.current_reflection_round,
        }
        d["role_outputs_summary"] = {k: v[:200] + "..." for k, v in self.role_outputs.items()}
        return d


class DataCollectionPlanner:
    """
    为每个角色规划增量数据采集需求，并（通过 DataCollector）执行采集。
    """

    def __init__(self, timeout: Optional[int] = None):
        self.primary_model, self.fallback_model = get_model_for_component("data_collection")
        tc_cfg = get_thinking_chain_config()
        self.timeout = timeout if timeout is not None else tc_cfg.get("data_collection_timeout", 120)

    def plan_for_role(
        self,
        role_name: str,
        role_description: str,
        role_responsibilities: List[str],
        task_description: str,
        existing_data_summary: str,
        previous_roles_output: str,
    ) -> DataCollectionSpec:
        """
        分析角色需求 + 已有数据，输出结构化的数据采集规格。
        通过 LLM 判断该角色需要什么额外数据。
        """
        resp_text = "\n".join(f"- {r}" for r in role_responsibilities) if role_responsibilities else role_description

        prompt = f"""你是一个数据采集规划师。分析以下角色的分析需求，判断该角色需要哪些额外的实时数据来支撑高质量分析。

## 总任务
{task_description}

## 当前角色
- 名称: {role_name}
- 描述: {role_description}
- 职责:
{resp_text}

## 已有数据摘要
{existing_data_summary[:2000] if existing_data_summary else '无初始数据'}

## 前置角色已输出的内容摘要
{previous_roles_output[:2000] if previous_roles_output else '无前置角色'}

## 输出格式 (JSON)
请输出该角色额外需要采集的数据。只列出已有数据中**没有覆盖**的、对角色分析**至关重要**的实时数据。

```json
{{{{
    "queries": ["具体数据查询1", "具体数据查询2"],
    "sources": ["数据来源类型，如 commodity_prices / market_prices / economic_data / energy_news"],
    "priority": "critical/important/supplementary",
    "rationale": "为什么需要这些数据"
}}}}
```

如果已有数据完全足够，返回: {{{{ "queries": [], "sources": [], "priority": "supplementary", "rationale": "已有数据充分" }}}}
"""

        try:
            result = self._call_model(self.primary_model, prompt)
            data = self._extract_json(result)
            parsed = json.loads(data)

            return DataCollectionSpec(
                role_name=role_name,
                queries=parsed.get("queries", []),
                sources=parsed.get("sources", []),
                priority=parsed.get("priority", "supplementary"),
                rationale=parsed.get("rationale", ""),
            )
        except Exception as e:
            logger.warning(f"plan_for_role failed for {role_name}: {e}")
            return DataCollectionSpec(
                role_name=role_name,
                queries=[],
                sources=[],
                priority="supplementary",
                rationale=f"规划失败: {e}",
            )

    def generate_feedback(
        self,
        current_role_name: str,
        current_role_output: str,
        previous_roles_outputs: Dict[str, str],
        task_description: str,
    ) -> List[FeedbackMessage]:
        """
        当前角色分析完成后，检查是否需要向前置角色发送反馈
        
        Args:
            current_role_name: 当前角色名称
            current_role_output: 当前角色的输出
            previous_roles_outputs: 前置角色的输出
            task_description: 任务描述
            
        Returns:
            需要发送的反馈消息列表
        """
        if not previous_roles_outputs:
            return []

        prev_summary = "\n\n".join(
            f"【{name}】\n{output[:1500]}"
            for name, output in previous_roles_outputs.items()
        )

        prompt = f"""你是一个分析质量审查员。当前角色刚完成分析，请检查其分析过程中是否发现前置角色的分析存在需要反馈的问题。

## 总任务
{task_description}

## 当前角色
{current_role_name}

## 当前角色输出
{current_role_output[:3000]}

## 前置角色输出
{prev_summary[:4000]}

## 可能的反馈类型
1. data_gap: 前置角色的数据不够新或不够准确，当前角色发现了数据差异
2. assumption_challenge: 前置角色的假设不合理，当前角色有证据质疑
3. logic_error: 前置角色的推理逻辑有漏洞
4. scope_expansion: 当前角色发现需要前置角色扩展分析范围

## 输出格式 (JSON)
```json
{{
    "feedbacks": [
        {{
            "to_role": "前置角色名称",
            "feedback_type": "data_gap/assumption_challenge/logic_error/scope_expansion",
            "content": "具体反馈内容",
            "suggested_action": "re_analyze/supplement_data/revise_conclusion/acknowledge",
            "priority": "high/medium/low"
        }}
    ]
}}
```

如果前置角色的分析没有问题，返回空数组: {{"feedbacks": []}}
"""

        try:
            result = self._call_model(self.primary_model, prompt)
            data = self._extract_json(result)
            parsed = json.loads(data)

            feedbacks = []
            for fb in parsed.get("feedbacks", []):
                feedbacks.append(FeedbackMessage(
                    from_role=current_role_name,
                    to_role=fb.get("to_role", ""),
                    feedback_type=fb.get("feedback_type", "scope_expansion"),
                    content=fb.get("content", ""),
                    suggested_action=fb.get("suggested_action", "acknowledge"),
                    priority=fb.get("priority", "low"),
                ))
            return feedbacks
        except Exception as e:
            logger.warning(f"Feedback generation failed for {current_role_name}: {e}")
            return []

    def should_trigger_re_execution(
        self, feedback: FeedbackMessage, state: ThinkingChainState
    ) -> bool:
        """判断反馈是否严重到需要触发重新执行"""
        if feedback.suggested_action not in ("re_analyze", "supise_data"):
            return False
        if feedback.priority != "high":
            return False
        target = feedback.to_role
        current_count = state.re_execution_count.get(target, 0)
        if current_count >= state.max_re_executions_per_role:
            return False
        return True

    def _call_model(self, model: str, prompt: str) -> str:
        from ..opencode_adapter import call_model
        return call_model(model, prompt, timeout=self.timeout)

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
            return text[start:end + 1]
        return text


class SelfReflectionEngine:
    """
    自我反思引擎
    
    在所有角色执行完毕后，对整个分析报告进行反思性审查：
    1. 立场是否合理？是否存在系统性偏见？
    2. 观点是否得到数据支撑？
    3. 是否有遗漏的重要维度？
    4. 假设是否经得起推敲？
    5. 是否只是简单汇总，还是真正的综合交叉分析？
    6. 数据是否过时？是否需要更新？
    """

    def __init__(self, timeout: Optional[int] = None):
        self.primary_model, self.fallback_model = get_model_for_component("self_reflection")
        tc_cfg = get_thinking_chain_config()
        self.timeout = timeout if timeout is not None else tc_cfg.get("reflection_timeout", 180)

    def reflect(
        self,
        task_description: str,
        role_outputs: Dict[str, str],
        collected_data: Dict[str, str],
        state: ThinkingChainState,
    ) -> List[ReflectionIssue]:
        """
        执行自我反思
        
        Args:
            task_description: 任务描述
            role_outputs: 所有角色的输出
            collected_data: 收集的数据
            state: 思考链状态
            
        Returns:
            发现的问题列表
        """
        all_outputs = "\n\n---\n\n".join(
            f"## {name}\n{output[:2500]}"
            for name, output in role_outputs.items()
        )

        data_summary = "\n".join(
            f"- {name}: {data[:500]}..."
            for name, data in collected_data.items()
        )

        role_names = list(role_outputs.keys())

        prompt = f"""你是一个高级分析审查专家。请对以下多角色分析结果进行全面反思性审查。

## 原始任务
{task_description}

## 参与角色
{', '.join(role_names)}

## 数据采集时间线
{data_summary[:3000] if data_summary else '无额外数据采集记录'}

## 各角色分析结果
{all_outputs[:12000]}

## 反思检查清单

请逐一检查以下维度，并指出发现的问题：

### 1. 数据时效性
- 各角色使用的数据是否是最新的？有没有明显过时的数据？
- 例如：金价当前实际是$4500，但分析中假设是$3500，这就是数据过时问题

### 2. 立场与偏见
- 分析是否存在系统性偏见（例如过度偏向某个视角）？
- 是否所有重要利益相关方的立场都被考虑了？

### 3. 遗漏的重要维度
- 是否有应该分析但完全遗漏的重要维度？
- 角色之间的交叉影响是否被充分考虑？

### 4. 假设合理性
- 各角色的核心假设是否合理？是否经过验证？
- 有没有"为了简化而过度简化"的问题？

### 5. 逻辑一致性
- 不同角色的结论之间是否存在矛盾？
- 因果推理链是否完整？

### 6. 分析深度（非简单汇总）
- 是否每个角色只是做了独立的单线分析？
- 后续角色是否真正利用了前置角色的结论进行交叉验证和综合分析？
- 是否存在"角色间缺乏对话"的问题？

## 输出格式 (JSON)
```json
{{
    "overall_assessment": "整体评估：一句话总结",
    "quality_score": 85,
    "issues": [
        {{
            "category": "data_staleness/missing_perspective/unvalidated_assumption/logical_gap/contradiction/oversimplification/bias",
            "description": "具体问题描述",
            "affected_roles": ["受影响的角色名"],
            "severity": "critical/high/medium/low",
            "suggested_fix": "建议的修复方式",
            "requires_re_execution": true/false
        }}
    ],
    "strengths": ["分析中的亮点"],
    "recommendations": ["改进建议"]
}}
```
"""

        try:
            result = self._call_model(self.primary_model, prompt)
            data = self._extract_json(result)
            parsed = json.loads(data)

            issues = []
            for issue in parsed.get("issues", []):
                issues.append(ReflectionIssue(
                    category=issue.get("category", "oversimplification"),
                    description=issue.get("description", ""),
                    affected_roles=issue.get("affected_roles", []),
                    severity=issue.get("severity", "medium"),
                    suggested_fix=issue.get("suggested_fix", ""),
                    requires_re_execution=issue.get("requires_re_execution", False),
                ))

            state.reflection_issues = issues
            return issues
        except Exception as e:
            logger.error(f"Self-reflection failed: {e}")
            return []

    def _call_model(self, model: str, prompt: str) -> str:
        from ..opencode_adapter import call_model
        return call_model(model, prompt, timeout=self.timeout)

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
            return text[start:end + 1]
        return text


class ThinkingChainExecutor:
    """
    思考链执行器 — 协调整个v4.0分析流程
    
    职责:
    1. 管理ThinkingChainState
    2. 在每个角色执行前调用DataCollectionPlanner
    3. 在每个角色执行后调用FeedbackProcessor
    4. 处理反馈触发的重新执行
    5. 最终调用SelfReflectionEngine
    """

    def __init__(
        self,
        task_description: str,
        role_execution_order: List[str],
        role_definitions: Dict[str, Dict],
        max_re_executions_per_role: Optional[int] = None,
        max_reflection_rounds: Optional[int] = None,
        enable_data_collection: bool = True,
    ):
        tc_cfg = get_thinking_chain_config()
        if max_re_executions_per_role is None:
            max_re_executions_per_role = tc_cfg.get("max_re_executions_per_role", 2)
        if max_reflection_rounds is None:
            max_reflection_rounds = tc_cfg.get("max_reflection_rounds", 2)
        self.state = ThinkingChainState(
            analysis_mode=AnalysisMode.COMPLEX_THINKING_CHAIN,
            task_description=task_description,
            role_execution_order=role_execution_order,
            max_re_executions_per_role=max_re_executions_per_role,
            max_reflection_rounds=max_reflection_rounds,
        )
        self.role_definitions = role_definitions
        self.enable_data_collection = enable_data_collection
        self.data_planner = DataCollectionPlanner()
        self.feedback_processor = self.data_planner
        self.reflection_engine = SelfReflectionEngine()
        self.data_collector = None
        if enable_data_collection:
            try:
                from .data_collector import DataCollector
                self.data_collector = DataCollector()
            except Exception as e:
                logger.warning(f"DataCollector initialization failed (web fetch disabled): {e}")
                self.data_collector = None

    def get_pre_execution_context(
        self, role_name: str, initial_data: str
    ) -> Tuple[str, DataCollectionSpec]:
        """
        角色执行前：规划数据采集 + 构建上下文
        
        Returns:
            (enhanced_context, collection_spec)
        """
        role_def = self.role_definitions.get(role_name, {})
        previous_outputs_summary = self._get_previous_outputs_summary(role_name)

        if not self.enable_data_collection:
            spec = DataCollectionSpec(
                role_name=role_name,
                queries=[],
                sources=[],
                priority="supplementary",
                rationale="任务不需要实时数据采集",
            )
            collected_raw = ""
        else:
            spec = self.data_planner.plan_for_role(
                role_name=role_name,
                role_description=role_def.get("description", ""),
                role_responsibilities=role_def.get("responsibilities", []),
                task_description=self.state.task_description,
                existing_data_summary=initial_data,
                previous_roles_output=previous_outputs_summary,
            )

            self.state.data_collection_specs[role_name] = spec

            if spec.queries and self.data_collector:
                logger.info(f"Executing data collection for {role_name}: {len(spec.queries)} queries")
                collected_raw = self.data_collector.execute(spec)
                self.state.collected_data[role_name] = collected_raw
            else:
                collected_raw = ""

        context_parts = []
        context_parts.append(f"## 初始采集数据\n{initial_data[:3000]}")

        for other_role, other_data in self.state.collected_data.items():
            if other_role != role_name:
                context_parts.append(f"## {other_role} 额外采集的数据\n{other_data[:2000]}")

        if collected_raw:
            context_parts.append(f"## 本角色实时采集数据\n{collected_raw}")

        for prev_role in self._get_input_roles(role_name):
            if prev_role in self.state.role_outputs:
                context_parts.append(
                    f"## 前置角色 [{prev_role}] 的输出\n{self.state.role_outputs[prev_role][:3000]}"
                )

        pending = [f for f in self.state.pending_feedback if f.to_role == role_name]
        if pending:
            feedback_text = "\n\n".join(
                f"- 来自 [{f.from_role}] ({f.feedback_type}): {f.content}\n  建议操作: {f.suggested_action}"
                for f in pending
            )
            context_parts.append(f"## 来自后续角色的反馈（需要你在分析中回应）\n{feedback_text}")
            for f in pending:
                self.state.pending_feedback.remove(f)
                self.state.resolved_feedback.append(f)

        if spec.queries:
            query_text = "\n".join(f"- {q}" for q in spec.queries)
            context_parts.append(
                f"## 本角色需要额外采集的数据\n以下问题在初始采集中未覆盖，请确保分析中考虑：\n{query_text}\n"
                f"数据来源建议: {', '.join(spec.sources)}\n"
                f"理由: {spec.rationale}"
            )

        enhanced_context = "\n\n---\n\n".join(context_parts)
        return enhanced_context, spec

    def post_execution_process(
        self, role_name: str, role_output: str
    ) -> List[FeedbackMessage]:
        """
        角色执行后：生成反馈 + 检查是否需要重新执行前置角色
        
        Returns:
            生成的反馈消息列表
        """
        self.state.role_outputs[role_name] = role_output
        self.state.completed_roles.append(role_name)

        previous_outputs = {}
        for prev_role in self._get_input_roles(role_name):
            if prev_role in self.state.role_outputs:
                previous_outputs[prev_role] = self.state.role_outputs[prev_role]

        feedbacks = self.feedback_processor.generate_feedback(
            current_role_name=role_name,
            current_role_output=role_output,
            previous_roles_outputs=previous_outputs,
            task_description=self.state.task_description,
        )

        for fb in feedbacks:
            self.state.pending_feedback.append(fb)

        return feedbacks

    def check_re_execution_needed(self) -> Optional[str]:
        """
        检查是否有高优先级反馈需要触发前置角色的重新执行
        
        Returns:
            需要重新执行的角色名，或None
        """
        for fb in self.state.pending_feedback[:]:
            if fb.to_role in self.state.completed_roles:
                if self.feedback_processor.should_trigger_re_execution(fb, self.state):
                    self.state.pending_feedback.remove(fb)
                    self.state.resolved_feedback.append(fb)
                    return fb.to_role
        return None

    def record_re_execution(self, role_name: str):
        """记录重新执行"""
        self.state.re_execution_count[role_name] = (
            self.state.re_execution_count.get(role_name, 0) + 1
        )
        if role_name in self.state.completed_roles:
            self.state.completed_roles.remove(role_name)

    def run_self_reflection(self) -> Tuple[List[ReflectionIssue], bool]:
        """
        执行自我反思
        
        Returns:
            (issues, needs_correction)
            needs_correction: 是否有critical/high问题需要修正
        """
        self.state.current_reflection_round += 1

        issues = self.reflection_engine.reflect(
            task_description=self.state.task_description,
            role_outputs=self.state.role_outputs,
            collected_data=self.state.collected_data,
            state=self.state,
        )

        needs_correction = any(
            issue.severity in ("critical", "high") and issue.requires_re_execution
            for issue in issues
        )

        if needs_correction and self.state.current_reflection_round < self.state.max_reflection_rounds:
            for issue in issues:
                if issue.severity in ("critical", "high") and issue.requires_re_execution:
                    for role in issue.affected_roles:
                        if role in self.state.role_execution_order:
                            fb = FeedbackMessage(
                                from_role="__self_reflection__",
                                to_role=role,
                                feedback_type="scope_expansion",
                                content=f"[自我反思发现] {issue.description}",
                                suggested_action="re_analyze",
                                priority="high",
                            )
                            self.state.pending_feedback.append(fb)

        return issues, needs_correction

    def get_roles_needing_re_execution(self) -> List[str]:
        """获取需要重新执行的角色列表"""
        roles = []
        for fb in self.state.pending_feedback[:]:
            if (fb.to_role in self.state.completed_roles and
                fb.suggested_action in ("re_analyze", "supplement_data") and
                fb.priority == "high"):
                target = fb.to_role
                count = self.state.re_execution_count.get(target, 0)
                if count < self.state.max_re_executions_per_role:
                    roles.append(target)
        return list(set(roles))

    def _get_input_roles(self, role_name: str) -> List[str]:
        """获取角色的前置角色"""
        role_def = self.role_definitions.get(role_name, {})
        return role_def.get("input_from", [])

    def _get_previous_outputs_summary(self, role_name: str) -> str:
        """获取前置角色输出的摘要"""
        input_roles = self._get_input_roles(role_name)
        summaries = []
        for prev in input_roles:
            if prev in self.state.role_outputs:
                output = self.state.role_outputs[prev]
                summaries.append(f"[{prev}]: {output[:1000]}...")
        return "\n\n".join(summaries) if summaries else "无前置角色输出"

    def execute_full_chain(
        self,
        initial_data: str,
        role_executor: callable,
    ) -> Dict[str, Any]:
        """
        完整思考链执行入口。

        Args:
            initial_data: 初始采集数据文本
            role_executor: 角色执行回调 (role_name, enhanced_context) -> output

        Returns:
            dict with keys: role_outputs, collected_data, reflection_issues, state
        """
        roles_to_execute = list(self.state.role_execution_order)
        executed_set = set()
        iteration = 0
        max_iterations = len(roles_to_execute) * 3

        while roles_to_execute and iteration < max_iterations:
            iteration += 1
            role_name = roles_to_execute.pop(0)

            if role_name in executed_set:
                continue

            input_roles = self._get_input_roles(role_name)
            if not all(r in executed_set for r in input_roles):
                roles_to_execute.append(role_name)
                continue

            enhanced_context, spec = self.get_pre_execution_context(
                role_name, initial_data
            )

            logger.info(
                f"Executing role: {role_name} "
                f"(data_collection: {len(spec.queries)} queries, "
                f"priority: {spec.priority})"
            )

            output = role_executor(role_name, enhanced_context)

            self.post_execution_process(role_name, output)

            re_exec_role = self.check_re_execution_needed()
            if re_exec_role and re_exec_role not in roles_to_execute:
                self.record_re_execution(re_exec_role)
                roles_to_execute.insert(0, re_exec_role)
                logger.info(f"Re-execution triggered for {re_exec_role}")

            executed_set.add(role_name)

        issues, needs_correction = self.run_self_reflection()

        if needs_correction and self.state.current_reflection_round < self.state.max_reflection_rounds:
            re_exec_roles = self.get_roles_needing_re_execution()
            for role in re_exec_roles:
                if role not in roles_to_execute:
                    roles_to_execute.append(role)
                    self.record_re_execution(role)
                    executed_set.discard(role)

            if roles_to_execute:
                return self.execute_full_chain(initial_data, role_executor)

        return {
            "role_outputs": dict(self.state.role_outputs),
            "collected_data": dict(self.state.collected_data),
            "reflection_issues": [i.to_dict() for i in self.state.reflection_issues],
            "state": self.state.to_dict(),
        }
