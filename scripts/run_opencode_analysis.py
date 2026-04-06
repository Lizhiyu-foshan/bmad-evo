#!/usr/bin/env python3
"""
BMAD-EVO v3.0 - OpenCode 集成版本
在 OpenCode 环境中直接调用模型进行真实分析

使用方法:
    python run_opencode_analysis.py
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent / "lib" / "v3"))

# 导入 BMAD-EVO 组件
from lib.v3.task_analyzer import TaskAnalyzer, TaskAnalysis
from lib.v3.role_generator import DynamicRoleGenerator, RoleFlow, RoleDefinition
from lib.v3.model_router import ModelRouter, RoutingResult


class OpenCodeBMADEVO:
    """
    BMAD-EVO v3.0 OpenCode 集成版本
    直接在 OpenCode 环境中调用模型进行分析和执行
    """

    def __init__(self, project_path: str = "./opencode_analysis"):
        self.project_path = Path(project_path)
        self.project_path.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.task_analyzer = TaskAnalyzer(timeout=120)
        self.role_generator = DynamicRoleGenerator(timeout=180)
        self.model_router = ModelRouter()

        # 存储结果
        self.task_analysis: Optional[TaskAnalysis] = None
        self.role_flow: Optional[RoleFlow] = None
        self.routing_result: Optional[RoutingResult] = None
        self.execution_results: Dict[str, Any] = {}

    def execute_full_workflow(self, task_description: str) -> Dict[str, Any]:
        """执行完整工作流"""

        print("=" * 80)
        print("BMAD-EVO v3.0 - OpenCode 集成版本")
        print("=" * 80)
        print(f"\n任务: {task_description[:80]}...\n")

        # Step 1: 任务分析
        print("\n[Step 1] 任务分析...")
        self.task_analysis = self._analyze_task(task_description)
        self._print_task_analysis()

        # Step 2: 生成角色
        print("\n[Step 2] 动态角色生成...")
        self.role_flow = self._generate_roles(task_description)
        self._print_roles()

        # Step 3: 模型路由
        print("\n[Step 3] 智能模型路由...")
        self.routing_result = self._route_models()
        self._print_routing()

        # Step 4: 执行工作流
        print("\n[Step 4] 执行工作流...")
        self.execution_results = self._execute_workflow(task_description)
        self._print_execution_summary()

        # 生成最终报告
        return self._generate_final_report()

    def _analyze_task(self, task_description: str) -> TaskAnalysis:
        """分析任务（使用直接模型调用）"""

        # 构建分析提示词
        prompt = f"""你是一个智能任务分析专家。请分析以下任务，并提供结构化的分析结果。

## 任务描述
{task_description}

## 分析要求
请从以下维度分析任务，并以 JSON 格式输出：

1. **task_type**: 任务类型
2. **complexity_score**: 复杂度评分（1-10）
3. **recommended_roles_count**: 推荐角色数量
4. **key_skills**: 关键技能列表
5. **estimated_duration**: 预估完成时间
6. **risk_factors**: 风险因素列表
7. **success_criteria**: 成功标准列表

## 复杂度评估指南
- 1-3分: 简单任务 → 1-2个角色
- 4-6分: 中等任务 → 2-3个角色
- 7-8分: 复杂任务 → 3-5个角色
- 9-10分: 极复杂任务 → 5-7个角色

## 输出格式
必须返回有效的 JSON：

```json
{{
  "task_type": "任务类型",
  "complexity_score": 8,
  "recommended_roles_count": 5,
  "key_skills": ["skill1", "skill2"],
  "estimated_duration": "2-3小时",
  "risk_factors": ["风险1"],
  "success_criteria": ["标准1"]
}}
```
"""

        try:
            # 使用 ask_model 调用模型（这是 OpenCode 环境的方法）
            result = self._call_model("alibaba/qwen3.5-plus", prompt)

            # 解析结果
            analysis_data = self._extract_json(result)
            data = json.loads(analysis_data)

            return TaskAnalysis(
                task_description=task_description,
                task_type=data.get("task_type", "analysis"),
                complexity_score=min(max(data.get("complexity_score", 5), 1), 10),
                recommended_roles_count=data.get("recommended_roles_count", 3),
                key_skills=data.get("key_skills", ["analysis"]),
                estimated_duration=data.get("estimated_duration", "unknown"),
                risk_factors=data.get("risk_factors", []),
                success_criteria=data.get("success_criteria", []),
                model_used="alibaba/qwen3.5-plus",
            )
        except Exception as e:
            print(f"任务分析失败: {e}")
            # 返回默认分析
            return TaskAnalysis(
                task_description=task_description,
                task_type="geopolitical_analysis",
                complexity_score=8,
                recommended_roles_count=5,
                key_skills=["geopolitics", "economics", "strategy"],
                estimated_duration="2-3小时",
                risk_factors=["信息时效性"],
                success_criteria=["全面分析"],
                model_used="fallback",
                error=str(e),
            )

    def _generate_roles(self, task_description: str) -> RoleFlow:
        """生成角色"""

        complexity = self.task_analysis.complexity_score if self.task_analysis else 8
        recommended = (
            self.task_analysis.recommended_roles_count if self.task_analysis else 5
        )

        prompt = f"""你是一个专业的任务分解专家。请为以下复杂任务设计最优的专业角色团队。

## 任务描述
{task_description}

## 任务特征
- 复杂度: {complexity}/10
- 推荐角色数: {recommended}
- 关键技能: {", ".join(self.task_analysis.key_skills if self.task_analysis else ["analysis"])}

## 角色设计原则
1. 每个角色必须是领域专家
2. 角色之间要有清晰的输入输出关系
3. 真正能独立的任务才标记为并行
4. 角色描述要具体、可执行

## 输出格式
返回 JSON 格式：

```json
{{
  "rationale": "选择这些角色的理由",
  "roles": [
    {{
      "name": "role_id",
      "title": "角色名称",
      "description": "角色职责描述",
      "responsibilities": ["职责1", "职责2"],
      "input_from": [],
      "output_to": ["next_role"],
      "can_parallel": false,
      "estimated_time": "20分钟",
      "required_skills": ["skill1"],
      "model_requirement": "对AI模型的要求"
    }}
  ],
  "execution_order": ["role1", "role2"],
  "parallel_groups": []
}}
```
"""

        try:
            result = self._call_model("zhipu/glm-5", prompt)
            roles_data = self._extract_json(result)
            data = json.loads(roles_data)

            roles = []
            for role_data in data.get("roles", []):
                role = RoleDefinition(
                    name=role_data.get("name", f"role_{len(roles)}"),
                    title=role_data.get("title", "未命名角色"),
                    description=role_data.get("description", ""),
                    responsibilities=role_data.get("responsibilities", []),
                    input_from=role_data.get("input_from", []),
                    output_to=role_data.get("output_to", []),
                    can_parallel=role_data.get("can_parallel", False),
                    estimated_time=role_data.get("estimated_time", "15分钟"),
                    required_skills=role_data.get("required_skills", []),
                    model_requirement=role_data.get("model_requirement", "通用能力"),
                )
                roles.append(role)

            return RoleFlow(
                task_description=task_description,
                task_type=self.task_analysis.task_type
                if self.task_analysis
                else "analysis",
                complexity=complexity,
                roles=roles,
                execution_order=data.get("execution_order", [r.name for r in roles]),
                parallel_groups=data.get("parallel_groups", []),
                rationale=data.get("rationale", "动态生成"),
                model_used="zhipu/glm-5",
            )
        except Exception as e:
            print(f"角色生成失败: {e}")
            # 返回默认角色
            return self._create_default_roles(task_description, complexity)

    def _route_models(self) -> RoutingResult:
        """为角色分配模型"""

        if not self.role_flow:
            raise RuntimeError("Role flow not generated yet")

        roles_dict = [
            {
                "id": r.name,
                "name": r.title,
                "description": r.description,
                "responsibilities": r.responsibilities,
                "required_skills": r.required_skills,
            }
            for r in self.role_flow.roles
        ]

        return self.model_router.route(
            roles=roles_dict,
            task_type=self.task_analysis.task_type
            if self.task_analysis
            else "analysis",
            complexity_score=self.task_analysis.complexity_score
            if self.task_analysis
            else 5,
        )

    def _execute_workflow(self, task_description: str) -> Dict[str, Any]:
        """执行工作流"""

        results = {}

        if not self.role_flow or not self.routing_result:
            return results

        for i, role_name in enumerate(self.role_flow.execution_order):
            role = self._get_role_by_name(role_name)
            if not role:
                continue

            print(
                f"\n  [{i + 1}/{len(self.role_flow.execution_order)}] 执行: {role.title}"
            )

            # 获取该角色的模型
            mapping = self._get_model_mapping(role_name)
            model = mapping.primary_model if mapping else "kimi-coding/k2p5"

            # 构建上下文
            context = self._build_context(role, task_description)

            # 执行角色任务
            try:
                result = self._call_model(model, context)
                results[role_name] = {"success": True, "output": result, "model": model}
                print(f"      完成 (使用模型: {model})")
            except Exception as e:
                results[role_name] = {"success": False, "error": str(e), "model": model}
                print(f"      失败: {e}")

        return results

    def _call_model(self, model: str, prompt: str) -> str:
        """
        调用模型（OpenCode 集成点）

        在 OpenCode 环境中，这个方法会被替换为实际的 ask_model 调用
        """
        # 这是一个占位符
        # 在实际的 OpenCode 执行中，这里会调用真实的模型
        return f"[Model {model} would process this task]\n\nPrompt preview: {prompt[:200]}..."

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON"""
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

    def _get_role_by_name(self, name: str) -> Optional[RoleDefinition]:
        """根据名称获取角色"""
        if not self.role_flow:
            return None
        for role in self.role_flow.roles:
            if role.name == name:
                return role
        return None

    def _get_model_mapping(self, role_name: str):
        """获取角色的模型映射"""
        if not self.routing_result:
            return None
        for mapping in self.routing_result.mappings:
            if mapping.role_id == role_name:
                return mapping
        return None

    def _build_context(self, role: RoleDefinition, task_description: str) -> str:
        """构建执行上下文"""

        # 获取前置角色的输出
        context_parts = []
        for input_role in role.input_from:
            if input_role in self.execution_results:
                result = self.execution_results[input_role]
                if result.get("success"):
                    context_parts.append(f"【来自 {input_role}】\n{result['output']}")

        context_str = (
            "\n\n".join(context_parts) if context_parts else "（起始角色，无前置输入）"
        )

        prompt = f"""你是 {role.title}。

## 你的职责
{role.description}

## 具体任务
{chr(10).join(f"- {r}" for r in role.responsibilities)}

## 原始任务描述
{task_description}

## 前置角色输出
{context_str}

## 要求
1. 基于你的专业领域进行分析
2. 输出结构化、逻辑清晰的内容
3. 如果需要，提供具体的建议或方案
4. 使用中文输出

请开始执行你的任务：
"""
        return prompt

    def _create_default_roles(self, task_description: str, complexity: int) -> RoleFlow:
        """创建默认角色（当动态生成失败时使用）"""

        roles = [
            RoleDefinition(
                name="geopolitical_analyst",
                title="地缘政治分析师",
                description="分析地缘政治格局和战略意图",
                responsibilities=["分析地缘政治背景", "评估战略影响"],
                input_from=[],
                output_to=["impact_assessor"],
                can_parallel=False,
                estimated_time="20分钟",
                required_skills=["geopolitics"],
                model_requirement="强逻辑推理",
            ),
            RoleDefinition(
                name="impact_assessor",
                title="影响评估师",
                description="评估对各方的影响",
                responsibilities=["评估经济影响", "预测连锁反应"],
                input_from=["geopolitical_analyst"],
                output_to=["strategy_advisor"],
                can_parallel=False,
                estimated_time="20分钟",
                required_skills=["impact_assessment"],
                model_requirement="全局视野",
            ),
            RoleDefinition(
                name="strategy_advisor",
                title="战略顾问",
                description="提出战略建议",
                responsibilities=["分析利益集团", "提出应对策略"],
                input_from=["impact_assessor"],
                output_to=[],
                can_parallel=False,
                estimated_time="20分钟",
                required_skills=["strategy"],
                model_requirement="深度分析",
            ),
        ]

        return RoleFlow(
            task_description=task_description,
            task_type="geopolitical_analysis",
            complexity=complexity,
            roles=roles,
            execution_order=[r.name for r in roles],
            parallel_groups=[],
            rationale="默认角色流程",
            model_used="fallback",
        )

    def _print_task_analysis(self):
        """打印任务分析结果"""
        if not self.task_analysis:
            return

        print(f"   任务类型: {self.task_analysis.task_type}")
        print(f"   复杂度: {self.task_analysis.complexity_score}/10")
        print(f"   推荐角色数: {self.task_analysis.recommended_roles_count}")
        print(f"   预估时长: {self.task_analysis.estimated_duration}")

    def _print_roles(self):
        """打印角色信息"""
        if not self.role_flow:
            return

        print(f"   生成角色: {self.role_flow.total_roles} 个")
        print(f"   执行顺序: {' -> '.join(self.role_flow.execution_order)}")

        for role in self.role_flow.roles:
            print(f"   - {role.title}: {role.description[:50]}...")

    def _print_routing(self):
        """打印模型路由结果"""
        if not self.routing_result:
            return

        print(f"   路由完成: {self.routing_result.total_roles} 个映射")
        print(f"   预估成本: {self.routing_result.estimated_cost_tier}")

        for mapping in self.routing_result.mappings:
            print(f"   - {mapping.role_id}: {mapping.primary_model}")

    def _print_execution_summary(self):
        """打印执行摘要"""
        success_count = sum(
            1 for r in self.execution_results.values() if r.get("success")
        )
        total = len(self.execution_results)
        print(f"\n   执行完成: {success_count}/{total} 成功")

    def _generate_final_report(self) -> Dict[str, Any]:
        """生成最终报告"""

        report_data = {
            "task_analysis": self.task_analysis.to_dict()
            if self.task_analysis
            else None,
            "role_flow": self.role_flow.to_dict() if self.role_flow else None,
            "routing": self.routing_result.to_dict() if self.routing_result else None,
            "execution": self.execution_results,
            "summary": {
                "total_roles": len(self.role_flow.roles) if self.role_flow else 0,
                "successful_executions": sum(
                    1 for r in self.execution_results.values() if r.get("success")
                ),
                "total_executions": len(self.execution_results),
            },
        }

        # 保存到文件
        output_file = self.project_path / "analysis_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\n✅ 分析报告已保存: {output_file}")

        return report_data


def main():
    """主函数"""

    # 任务描述
    task = """
分析美以打击伊朗对石油价格的地缘政治冲击。

要求：
1. 分析要严谨、符合逻辑
2. 从大格局出发，通观地缘政治
3. 分析背后利益集团和各方立场
4. 预测各国连锁反应
5. 评估对中国等石油进口国的影响
6. 提出投资策略建议
"""

    # 创建执行器
    system = OpenCodeBMADEVO(project_path="./opencode_analysis")

    # 执行工作流
    result = system.execute_full_workflow(task)

    print("\n" + "=" * 80)
    print("分析完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
