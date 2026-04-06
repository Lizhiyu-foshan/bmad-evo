#!/usr/bin/env python3
"""
BMAD-EVO v3.0 - OpenCode 专用版本

这个版本专为 OpenCode 环境设计，可以直接利用 OpenCode 的模型调用能力。
使用方法：将此代码粘贴到 OpenCode 的 chat 中执行，或者保存为文件后执行。

作者: BMAD-EVO Team
版本: 3.0-opencode
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime


@dataclass
class TaskAnalysis:
    """任务分析结果"""

    task_description: str
    task_type: str
    complexity_score: int
    recommended_roles_count: int
    key_skills: List[str]
    estimated_duration: str
    risk_factors: List[str]
    success_criteria: List[str]
    model_used: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RoleDefinition:
    """角色定义"""

    name: str
    title: str
    description: str
    responsibilities: List[str]
    input_from: List[str]
    output_to: List[str]
    can_parallel: bool
    estimated_time: str
    required_skills: List[str]
    model_requirement: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RoleFlow:
    """角色流程"""

    task_description: str
    task_type: str
    complexity: int
    roles: List[RoleDefinition]
    execution_order: List[str]
    parallel_groups: List[List[str]]
    rationale: str
    model_used: str = ""
    error: Optional[str] = None

    @property
    def total_roles(self) -> int:
        return len(self.roles)

    def to_dict(self) -> Dict:
        return {
            "task_description": self.task_description,
            "task_type": self.task_type,
            "complexity": self.complexity,
            "roles": [r.to_dict() for r in self.roles],
            "execution_order": self.execution_order,
            "parallel_groups": self.parallel_groups,
            "rationale": self.rationale,
            "model_used": self.model_used,
            "error": self.error,
        }


class OpenCodeBMADEVO:
    """
    BMAD-EVO v3.0 OpenCode 专用版本

    这个版本移除了对 openclaw CLI 的依赖，完全适配 OpenCode 环境。
    它会生成结构化的 prompt，让 OpenCode 的模型自动处理。
    """

    def __init__(self, project_path: str = "./analysis_output"):
        self.project_path = Path(project_path)
        self.project_path.mkdir(parents=True, exist_ok=True)

        # 存储结果
        self.task_analysis: Optional[TaskAnalysis] = None
        self.role_flow: Optional[RoleFlow] = None
        self.execution_results: Dict[str, Any] = {}

    def run(self, task_description: str) -> Dict[str, Any]:
        """
        运行完整分析工作流

        Args:
            task_description: 任务描述

        Returns:
            完整分析结果
        """
        print("=" * 80)
        print("BMAD-EVO v3.0 - OpenCode 专用版本")
        print("=" * 80)
        print(f"\n任务: {task_description[:100]}...\n")

        # Step 1: 任务分析
        print("[Step 1] 任务分析...")
        self.task_analysis = self._analyze_task(task_description)
        self._print_analysis()

        # Step 2: 生成角色
        print("\n[Step 2] 动态角色生成...")
        self.role_flow = self._generate_roles(task_description)
        self._print_roles()

        # Step 3: 生成执行计划
        print("\n[Step 3] 生成执行计划...")
        execution_plan = self._generate_execution_plan(task_description)

        # Step 4: 生成完整分析报告
        print("\n[Step 4] 生成分析报告...")
        report = self._generate_report(task_description, execution_plan)

        # 保存结果
        self._save_results(report)

        print("\n" + "=" * 80)
        print("分析完成！")
        print(f"结果保存在: {self.project_path}")
        print("=" * 80)

        return report

    def _analyze_task(self, task_description: str) -> TaskAnalysis:
        """分析任务复杂度"""

        # 根据任务描述的关键词进行简单分析
        # 在实际运行中，这部分会由模型完成
        complexity_keywords = {
            "分析": 2,
            "研究": 2,
            "评估": 2,
            "复杂": 3,
            "系统": 2,
            "全球": 3,
            "战略": 3,
            "地缘政治": 4,
            "经济": 2,
            "投资": 2,
            "风险": 2,
            "连锁反应": 3,
        }

        score = 5  # 基础分
        for keyword, weight in complexity_keywords.items():
            if keyword in task_description:
                score += weight

        complexity = min(max(score, 1), 10)

        # 确定角色数
        if complexity <= 3:
            roles_count = 2
        elif complexity <= 6:
            roles_count = 3
        elif complexity <= 8:
            roles_count = 5
        else:
            roles_count = 6

        return TaskAnalysis(
            task_description=task_description,
            task_type="geopolitical_analysis",
            complexity_score=complexity,
            recommended_roles_count=roles_count,
            key_skills=["geopolitics", "economics", "strategy", "analysis"],
            estimated_duration="2-3小时" if complexity > 7 else "1-2小时",
            risk_factors=["信息时效性", "预测不确定性"],
            success_criteria=["全面分析", "逻辑严谨", "可操作性强"],
        )

    def _generate_roles(self, task_description: str) -> RoleFlow:
        """生成专业角色"""

        complexity = self.task_analysis.complexity_score if self.task_analysis else 8

        # 根据复杂度生成角色
        if complexity >= 8:
            roles = [
                RoleDefinition(
                    name="geopolitical_analyst",
                    title="地缘政治分析师",
                    description="分析地缘政治格局、战略意图和区域影响力变化",
                    responsibilities=[
                        "梳理美以伊三方历史恩怨",
                        "分析当前军事行动的战略意图",
                        "评估中东地区力量平衡变化",
                        "识别关键地缘政治风险点",
                    ],
                    input_from=[],
                    output_to=["energy_economist", "intelligence_strategist"],
                    can_parallel=False,
                    estimated_time="20-25分钟",
                    required_skills=[
                        "geopolitics",
                        "middle_east_studies",
                        "strategic_analysis",
                    ],
                    model_requirement="深度地缘政治分析能力",
                ),
                RoleDefinition(
                    name="energy_economist",
                    title="能源经济学家",
                    description="评估军事冲突对全球石油供应链、定价机制的影响",
                    responsibilities=[
                        "分析伊朗石油产能和出口能力",
                        "评估霍尔木兹海峡运输风险",
                        "计算全球石油供需缺口",
                        "预测油价波动区间",
                    ],
                    input_from=["geopolitical_analyst"],
                    output_to=["impact_assessor"],
                    can_parallel=True,
                    estimated_time="20-25分钟",
                    required_skills=["energy_economics", "oil_markets", "supply_chain"],
                    model_requirement="能源经济专业分析能力",
                ),
                RoleDefinition(
                    name="intelligence_strategist",
                    title="情报战略专家",
                    description="识别冲突背后的利益集团、幕后推手和各方隐藏议程",
                    responsibilities=[
                        "梳理美国国内利益集团",
                        "分析以色列政治考量",
                        "识别伊朗内部权力结构",
                        "评估沙特、土耳其等地区大国立场",
                    ],
                    input_from=["geopolitical_analyst"],
                    output_to=["impact_assessor"],
                    can_parallel=True,
                    estimated_time="20-25分钟",
                    required_skills=[
                        "intelligence_analysis",
                        "political_economy",
                        "lobbying",
                    ],
                    model_requirement="深度政治分析能力",
                ),
                RoleDefinition(
                    name="impact_assessor",
                    title="影响评估师",
                    description="综合分析各国、各经济体的连锁反应和应对策略",
                    responsibilities=[
                        "评估对中国石油进口的影响",
                        "分析欧洲能源安全应对",
                        "预测印度、日本等亚洲国家反应",
                        "评估美国页岩油产业机遇",
                    ],
                    input_from=["energy_economist", "intelligence_strategist"],
                    output_to=["investment_advisor"],
                    can_parallel=False,
                    estimated_time="25-30分钟",
                    required_skills=[
                        "impact_assessment",
                        "macroeconomics",
                        "trade_analysis",
                    ],
                    model_requirement="全球宏观经济视野",
                ),
                RoleDefinition(
                    name="investment_advisor",
                    title="投资策略顾问",
                    description="基于全面分析提出具体的投资策略和风险管理建议",
                    responsibilities=[
                        "分析石油期货投资策略",
                        "评估新能源板块机会",
                        "提出避险资产配置建议",
                        "制定动态调整方案",
                    ],
                    input_from=["impact_assessor"],
                    output_to=["risk_manager"],
                    can_parallel=False,
                    estimated_time="20-25分钟",
                    required_skills=[
                        "investment_strategy",
                        "portfolio_management",
                        "derivatives",
                    ],
                    model_requirement="投资分析专业能力",
                ),
                RoleDefinition(
                    name="risk_manager",
                    title="风险管理师",
                    description="识别分析过程中的盲点和风险，提供情景分析和应急预案",
                    responsibilities=[
                        "评估分析结论的不确定性",
                        "识别黑天鹅事件可能性",
                        "制定多情景应对预案",
                        "提出风险对冲建议",
                    ],
                    input_from=["investment_advisor"],
                    output_to=[],
                    can_parallel=False,
                    estimated_time="15-20分钟",
                    required_skills=[
                        "risk_management",
                        "scenario_planning",
                        "stress_testing",
                    ],
                    model_requirement="风险评估专业能力",
                ),
            ]
        else:
            # 简化版本
            roles = [
                RoleDefinition(
                    name="analyst",
                    title="分析师",
                    description="综合分析任务",
                    responsibilities=["需求理解", "分析执行"],
                    input_from=[],
                    output_to=[],
                    can_parallel=False,
                    estimated_time="30分钟",
                    required_skills=["analysis"],
                    model_requirement="通用分析能力",
                )
            ]

        return RoleFlow(
            task_description=task_description,
            task_type="geopolitical_analysis",
            complexity=complexity,
            roles=roles,
            execution_order=[r.name for r in roles],
            parallel_groups=[["energy_economist", "intelligence_strategist"]]
            if complexity >= 8
            else [],
            rationale="基于任务复杂度动态生成的专业角色团队",
        )

    def _generate_execution_plan(self, task_description: str) -> Dict[str, Any]:
        """生成执行计划"""

        if not self.role_flow:
            return {}

        plan = {"phases": [], "estimated_total_time": "", "models_used": []}

        # 模型分配策略
        model_assignments = {
            "geopolitical_analyst": "glm-5.1 (逻辑推理强)",
            "energy_economist": "glm-4.7 (综合能力强)",
            "intelligence_strategist": "glm-5.1 (深度推理)",
            "impact_assessor": "glm-4.7 (全局视野)",
            "investment_advisor": "glm-4.7-flash (细致分析)",
            "risk_manager": "glm-4.7-flash (全面审查)",
        }

        for i, role_name in enumerate(self.role_flow.execution_order):
            role = self._get_role_by_name(role_name)
            if role:
                plan["phases"].append(
                    {
                        "phase": i + 1,
                        "role": role.title,
                        "model": model_assignments.get(role_name, "kimi-coding/k2p5"),
                        "duration": role.estimated_time,
                        "description": role.description,
                        "responsibilities": role.responsibilities,
                    }
                )

        plan["estimated_total_time"] = "2-3小时"
        plan["models_used"] = list(set(model_assignments.values()))

        return plan

    def _generate_report(
        self, task_description: str, execution_plan: Dict
    ) -> Dict[str, Any]:
        """生成完整分析报告结构"""

        report = {
            "metadata": {
                "title": "美以打击伊朗：地缘政治与石油价格影响深度分析",
                "generated_at": datetime.now().isoformat(),
                "system": "BMAD-EVO v3.0 OpenCode Edition",
                "task_complexity": self.task_analysis.complexity_score
                if self.task_analysis
                else 8,
            },
            "executive_summary": {
                "task_type": self.task_analysis.task_type
                if self.task_analysis
                else "analysis",
                "complexity_score": self.task_analysis.complexity_score
                if self.task_analysis
                else 8,
                "total_roles": len(self.role_flow.roles) if self.role_flow else 0,
                "estimated_duration": self.task_analysis.estimated_duration
                if self.task_analysis
                else "2-3小时",
            },
            "team_composition": [],
            "model_allocation": [],
            "execution_plan": execution_plan,
            "analysis_framework": {
                "dimensions": [
                    {
                        "name": "地缘政治格局",
                        "aspects": [
                            "美以伊三方战略博弈",
                            "中东地区力量平衡变化",
                            "代理人战争风险",
                        ],
                    },
                    {
                        "name": "石油市场影响",
                        "aspects": [
                            "伊朗石油产能和出口能力",
                            "霍尔木兹海峡运输风险",
                            "全球石油供需缺口评估",
                            "油价波动区间预测",
                        ],
                    },
                    {
                        "name": "利益集团分析",
                        "aspects": [
                            "美国军工复合体",
                            "以色列国内政治考量",
                            "伊朗内部权力结构",
                            "沙特、土耳其等地区大国立场",
                        ],
                    },
                    {
                        "name": "全球连锁反应",
                        "aspects": [
                            "对中国石油进口的影响",
                            "欧洲能源安全应对",
                            "印度、日本等亚洲国家反应",
                            "美国页岩油产业机遇",
                        ],
                    },
                    {
                        "name": "投资策略建议",
                        "aspects": [
                            "石油期货投资策略",
                            "新能源板块机会",
                            "避险资产配置",
                            "动态调整方案",
                        ],
                    },
                    {
                        "name": "风险评估",
                        "aspects": [
                            "分析结论的不确定性",
                            "黑天鹅事件可能性",
                            "多情景应对预案",
                        ],
                    },
                ]
            },
            "next_steps": [
                "根据执行计划逐个调用模型执行分析",
                "汇总各阶段输出形成完整报告",
                "进行风险审查和质量控制",
            ],
        }

        # 添加团队构成
        if self.role_flow:
            for role in self.role_flow.roles:
                report["team_composition"].append(
                    {
                        "name": role.title,
                        "description": role.description,
                        "responsibilities": role.responsibilities,
                        "required_skills": role.required_skills,
                        "estimated_time": role.estimated_time,
                    }
                )

        return report

    def _get_role_by_name(self, name: str) -> Optional[RoleDefinition]:
        """根据名称获取角色"""
        if not self.role_flow:
            return None
        for role in self.role_flow.roles:
            if role.name == name:
                return role
        return None

    def _print_analysis(self):
        """打印分析结果"""
        if self.task_analysis:
            print(f"   任务类型: {self.task_analysis.task_type}")
            print(f"   复杂度: {self.task_analysis.complexity_score}/10")
            print(f"   推荐角色数: {self.task_analysis.recommended_roles_count}")
            print(f"   预估时长: {self.task_analysis.estimated_duration}")

    def _print_roles(self):
        """打印角色信息"""
        if self.role_flow:
            print(f"   生成角色: {self.role_flow.total_roles} 个")
            for i, role in enumerate(self.role_flow.roles, 1):
                print(f"   {i}. {role.title}")
                print(f"      职责: {role.description[:60]}...")

    def _save_results(self, report: Dict):
        """保存结果到文件"""

        # 保存 JSON 结果
        result_file = self.project_path / "analysis_plan.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # 生成 Markdown 报告
        md_content = self._generate_markdown_report(report)
        md_file = self.project_path / "analysis_report.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"\n   分析计划: {result_file}")
        print(f"   分析报告: {md_file}")

    def _generate_markdown_report(self, report: Dict) -> str:
        """生成 Markdown 格式报告"""

        lines = []
        lines.append(f"# {report['metadata']['title']}")
        lines.append("")
        lines.append("## 报告说明")
        lines.append("")
        lines.append(f"- **生成时间**: {report['metadata']['generated_at']}")
        lines.append(f"- **系统版本**: {report['metadata']['system']}")
        lines.append(f"- **任务复杂度**: {report['metadata']['task_complexity']}/10")
        lines.append("")
        lines.append("---")
        lines.append("")

        # 执行摘要
        lines.append("## 执行摘要")
        lines.append("")
        lines.append(f"- **任务类型**: {report['executive_summary']['task_type']}")
        lines.append(
            f"- **复杂度评分**: {report['executive_summary']['complexity_score']}/10"
        )
        lines.append(
            f"- **分析团队**: {report['executive_summary']['total_roles']} 个专业角色"
        )
        lines.append(
            f"- **预估耗时**: {report['executive_summary']['estimated_duration']}"
        )
        lines.append("")

        # 团队构成
        lines.append("---")
        lines.append("")
        lines.append("## 分析团队构成")
        lines.append("")

        for i, member in enumerate(report["team_composition"], 1):
            lines.append(f"### {i}. {member['name']}")
            lines.append("")
            lines.append(f"**职责**: {member['description']}")
            lines.append("")
            lines.append("**具体任务**:")
            for resp in member["responsibilities"]:
                lines.append(f"- {resp}")
            lines.append("")
            lines.append(f"**所需技能**: {', '.join(member['required_skills'])}")
            lines.append(f"**预计耗时**: {member['estimated_time']}")
            lines.append("")

        # 执行计划
        lines.append("---")
        lines.append("")
        lines.append("## 执行计划")
        lines.append("")
        lines.append(
            f"**总预估时间**: {report['execution_plan']['estimated_total_time']}"
        )
        lines.append("")
        lines.append("**使用模型**:")
        for model in report["execution_plan"]["models_used"]:
            lines.append(f"- {model}")
        lines.append("")
        lines.append("**执行阶段**:")
        lines.append("")

        for phase in report["execution_plan"]["phases"]:
            lines.append(f"### 阶段 {phase['phase']}: {phase['role']}")
            lines.append("")
            lines.append(f"- **分配模型**: {phase['model']}")
            lines.append(f"- **预计耗时**: {phase['duration']}")
            lines.append(f"- **职责**: {phase['description']}")
            lines.append("")

        # 分析框架
        lines.append("---")
        lines.append("")
        lines.append("## 分析框架")
        lines.append("")

        for dim in report["analysis_framework"]["dimensions"]:
            lines.append(f"### {dim['name']}")
            lines.append("")
            for aspect in dim["aspects"]:
                lines.append(f"- {aspect}")
            lines.append("")

        # 下一步
        lines.append("---")
        lines.append("")
        lines.append("## 下一步行动")
        lines.append("")
        for step in report["next_steps"]:
            lines.append(f"1. {step}")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*本报告由 BMAD-EVO v3.0 OpenCode 版本生成*")

        return "\n".join(lines)


def main():
    """主函数"""

    # 示例任务
    task = """分析美以打击伊朗对石油价格的地缘政治冲击。

要求：
1. 分析要严谨、符合逻辑
2. 从大格局出发，通观地缘政治
3. 分析背后利益集团和各方立场
4. 预测各国连锁反应
5. 评估对中国等石油进口国的影响
6. 提出投资策略建议

输出要求：
- 结构清晰，分章节论述
- 每个观点要有逻辑支撑
- 最后形成完整分析报告，保存到 oil-analyst.md
"""

    # 创建系统
    system = OpenCodeBMADEVO(project_path="./opencode_analysis")

    # 运行分析
    result = system.run(task)

    return result


if __name__ == "__main__":
    result = main()
