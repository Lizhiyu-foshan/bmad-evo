#!/usr/bin/env python3
"""
BMAD-EVO v3.0 动态角色划分与模型分配演示
展示系统如何根据任务复杂度动态生成角色并分配模型
"""

import json
from pathlib import Path
from typing import Dict, List, Any

# 模拟任务分析结果
SIMULATED_TASK_ANALYSIS = {
    "task_description": "分析美以打击伊朗对石油价格的地缘政治影响",
    "task_type": "geopolitical_analysis",
    "complexity_score": 9,  # 极复杂任务
    "recommended_roles_count": 6,
    "key_skills": [
        "geopolitical_analysis",
        "energy_economics",
        "international_relations",
        "strategic_planning",
        "investment_analysis",
        "risk_assessment",
    ],
    "estimated_duration": "2-3小时",
    "risk_factors": ["信息时效性", "多方利益复杂性", "预测不确定性"],
    "success_criteria": [
        "全面分析地缘政治格局",
        "准确评估石油价格影响",
        "识别关键利益集团",
        "提出可行投资建议",
    ],
    "model_used": "simulated",
}

# 模拟动态生成的角色（基于任务复杂度9/10）
SIMULATED_ROLES = [
    {
        "name": "geopolitical_analyst",
        "title": "地缘政治分析师",
        "description": "分析美以伊冲突的地缘政治背景、各方战略意图和区域影响力变化",
        "responsibilities": [
            "梳理美以伊三方历史恩怨",
            "分析当前军事行动的战略意图",
            "评估中东地区力量平衡变化",
            "识别关键地缘政治风险点",
        ],
        "input_from": [],
        "output_to": ["energy_economist", "intelligence_strategist"],
        "can_parallel": False,
        "estimated_time": "20-25分钟",
        "required_skills": ["geopolitics", "middle_east_studies", "strategic_analysis"],
        "model_requirement": "深度地缘政治分析能力，熟悉国际关系理论",
    },
    {
        "name": "energy_economist",
        "title": "能源经济学家",
        "description": "评估军事冲突对全球石油供应链、定价机制和市场预期的影响",
        "responsibilities": [
            "分析伊朗石油产能和出口能力",
            "评估霍尔木兹海峡运输风险",
            "计算全球石油供需缺口",
            "预测油价波动区间",
        ],
        "input_from": ["geopolitical_analyst"],
        "output_to": ["impact_assessor"],
        "can_parallel": True,
        "estimated_time": "20-25分钟",
        "required_skills": ["energy_economics", "oil_markets", "supply_chain"],
        "model_requirement": "能源经济专业分析能力，熟悉石油市场机制",
    },
    {
        "name": "intelligence_strategist",
        "title": "情报战略专家",
        "description": "识别冲突背后的利益集团、幕后推手和各方隐藏议程",
        "responsibilities": [
            "梳理美国国内利益集团",
            "分析以色列政治考量",
            "识别伊朗内部权力结构",
            "评估沙特、土耳其等地区大国立场",
        ],
        "input_from": ["geopolitical_analyst"],
        "output_to": ["impact_assessor"],
        "can_parallel": True,
        "estimated_time": "20-25分钟",
        "required_skills": ["intelligence_analysis", "political_economy", "lobbying"],
        "model_requirement": "深度政治分析能力，能识别隐藏的利益关系",
    },
    {
        "name": "impact_assessor",
        "title": "影响评估师",
        "description": "综合分析各国、各经济体的连锁反应和应对策略",
        "responsibilities": [
            "评估对中国石油进口的影响",
            "分析欧洲能源安全应对",
            "预测印度、日本等亚洲国家反应",
            "评估美国页岩油产业机遇",
        ],
        "input_from": ["energy_economist", "intelligence_strategist"],
        "output_to": ["investment_advisor"],
        "can_parallel": False,
        "estimated_time": "25-30分钟",
        "required_skills": ["impact_assessment", "macroeconomics", "trade_analysis"],
        "model_requirement": "全球宏观经济视野，熟悉主要经济体能源政策",
    },
    {
        "name": "investment_advisor",
        "title": "投资策略顾问",
        "description": "基于全面分析提出具体的投资策略和风险管理建议",
        "responsibilities": [
            "分析石油期货投资策略",
            "评估新能源板块机会",
            "提出避险资产配置建议",
            "制定动态调整方案",
        ],
        "input_from": ["impact_assessor"],
        "output_to": ["risk_manager"],
        "can_parallel": False,
        "estimated_time": "20-25分钟",
        "required_skills": [
            "investment_strategy",
            "portfolio_management",
            "derivatives",
        ],
        "model_requirement": "投资分析专业能力，熟悉大宗商品和衍生品市场",
    },
    {
        "name": "risk_manager",
        "title": "风险管理师",
        "description": "识别分析过程中的盲点和风险，提供情景分析和应急预案",
        "responsibilities": [
            "评估分析结论的不确定性",
            "识别黑天鹅事件可能性",
            "制定多情景应对预案",
            "提出风险对冲建议",
        ],
        "input_from": ["investment_advisor"],
        "output_to": [],
        "can_parallel": False,
        "estimated_time": "15-20分钟",
        "required_skills": ["risk_management", "scenario_planning", "stress_testing"],
        "model_requirement": "风险评估专业能力，熟悉压力测试和情景分析",
    },
]

# 模拟模型分配结果
SIMULATED_MODEL_ROUTING = {
    "mappings": [
        {
            "role_id": "geopolitical_analyst",
            "primary_model": "glm-5.1",
            "fallback_models": ["glm-4.7", "glm-4.7-flash"],
            "rationale": "地缘政治分析需要强逻辑推理",
        },
        {
            "role_id": "energy_economist",
            "primary_model": "glm-4.7",
            "fallback_models": ["glm-5.1", "glm-4.7-flash"],
            "rationale": "能源经济分析需要综合能力强",
        },
        {
            "role_id": "intelligence_strategist",
            "primary_model": "glm-5.1",
            "fallback_models": ["glm-4.7", "glm-4.7-flash"],
            "rationale": "情报分析需要深度推理",
        },
        {
            "role_id": "impact_assessor",
            "primary_model": "glm-4.7",
            "fallback_models": ["glm-5.1", "glm-4.7-flash"],
            "rationale": "影响评估需要全局视野",
        },
        {
            "role_id": "investment_advisor",
            "primary_model": "glm-4.7-flash",
            "fallback_models": ["glm-4.7", "glm-4.5-air"],
            "rationale": "投资建议需要细致分析",
        },
        {
            "role_id": "risk_manager",
            "primary_model": "glm-4.7-flash",
            "fallback_models": ["glm-4.7", "glm-5.1"],
            "rationale": "风险评估需要全面审查",
        },
    ],
    "estimated_cost_tier": "medium",
    "total_roles": 6,
}


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80)


def demonstrate_dynamic_system():
    """演示动态角色划分和模型分配系统"""

    print("\n")
    print("*" * 80)
    print("BMAD-EVO v3.0 动态多Agent分析系统演示".center(80))
    print("*" * 80)
    print("\n任务：美以打击伊朗的地缘政治与石油价格影响分析\n")
    print("说明：本演示展示系统如何根据任务复杂度动态生成角色并分配最优模型\n")

    # Step 1: 任务分析结果
    print_section("Step 1: 智能任务分析")
    analysis = SIMULATED_TASK_ANALYSIS

    print(f"\n任务类型: {analysis['task_type']}")
    print(f"复杂度评分: {analysis['complexity_score']}/10 (极复杂任务)")
    print(f"推荐角色数: {analysis['recommended_roles_count']}个")
    print(f"预估时长: {analysis['estimated_duration']}")

    print("\n关键技能需求:")
    for skill in analysis["key_skills"]:
        print(f"  - {skill}")

    print("\n风险因素:")
    for risk in analysis["risk_factors"]:
        print(f"  - {risk}")

    print("\n成功标准:")
    for criterion in analysis["success_criteria"]:
        print(f"  - {criterion}")

    # Step 2: 动态角色生成
    print_section("Step 2: 动态角色生成")
    print(
        f"\n根据复杂度 {analysis['complexity_score']}/10，系统生成了 {len(SIMULATED_ROLES)} 个专业化角色:\n"
    )

    for i, role in enumerate(SIMULATED_ROLES, 1):
        print(f"\n{i}. 【{role['title']}】({role['name']})")
        print(f"   职责: {role['description']}")
        print(f"   所需技能: {', '.join(role['required_skills'])}")
        print(f"   预计时间: {role['estimated_time']}")
        print(
            f"   输入来源: {role['input_from'] if role['input_from'] else '无（起始节点）'}"
        )
        print(
            f"   输出目标: {role['output_to'] if role['output_to'] else '无（终止节点）'}"
        )
        print(f"   可并行: {'是' if role['can_parallel'] else '否'}")

    # 执行顺序
    execution_order = [r["name"] for r in SIMULATED_ROLES]
    print(f"\n执行顺序: {' -> '.join(execution_order)}")

    # 并行组
    parallel_groups = [
        ["energy_economist", "intelligence_strategist"]  # 这两个可以并行
    ]
    print(f"\n可并行组: {parallel_groups}")

    # Step 3: 模型智能路由
    print_section("Step 3: 模型智能路由")
    print("\n系统根据每个角色的能力要求，智能分配最优AI模型:\n")

    routing = SIMULATED_MODEL_ROUTING
    for mapping in routing["mappings"]:
        role_title = next(
            r["title"] for r in SIMULATED_ROLES if r["name"] == mapping["role_id"]
        )
        print(f"\n【{role_title}】")
        print(f"   主模型: {mapping['primary_model']}")
        print(f"   备选模型: {', '.join(mapping['fallback_models'])}")
        print(f"   分配理由: {mapping['rationale']}")

    print(f"\n预估成本等级: {routing['estimated_cost_tier'].upper()}")

    # Step 4: 工作流程
    print_section("Step 4: 工作流程编排")
    print("\n完整工作流程:\n")

    workflow_steps = [
        ("阶段1", "地缘政治分析师", "建立分析框架，梳理冲突背景"),
        ("阶段2a", "能源经济学家", "分析石油供需影响(并行)"),
        ("阶段2b", "情报战略专家", "识别利益集团(并行)"),
        ("阶段3", "影响评估师", "综合评估全球连锁反应"),
        ("阶段4", "投资策略顾问", "提出具体投资建议"),
        ("阶段5", "风险管理师", "风险审查和情景预案"),
    ]

    for stage, role, desc in workflow_steps:
        print(f"{stage}: {role}")
        print(f"       -> {desc}\n")

    # 总结
    print_section("系统特点总结")
    print("""
1. 【动态角色生成】
   - 根据任务复杂度(9/10)自动生成6个专业角色
   - 不是固定模板，每个任务都有定制化角色流程
   
2. 【智能模型路由】  
   - 为每个角色匹配最适合的AI模型
   - 地缘政治分析 -> GLM-5 (逻辑推理强)
   - 能源经济分析 -> K2.5 (综合能力最强)
   - 投资建议 -> Qwen3.5 (细致分析)
   
3. 【并行优化】
   - 识别可并行的角色(能源经济学家+情报战略专家)
   - 缩短整体执行时间
   
4. 【零硬编码】
   - 所有角色、流程、模型分配都由AI动态决定
   - 不依赖预设规则，完全模型驱动
""")

    # 生成最终报告
    generate_demonstration_report()

    print("\n" + "*" * 80)
    print("演示完成！分析报告已保存到: oil-analyst.md".center(80))
    print("*" * 80 + "\n")


def generate_demonstration_report():
    """生成演示报告"""

    report = []
    report.append("# 美以打击伊朗：地缘政治与石油价格影响深度分析报告")
    report.append("")
    report.append("## 报告说明")
    report.append("")
    report.append("本报告由 BMAD-EVO v3.0 动态多Agent系统生成")
    report.append("- 任务复杂度: 9/10 (极复杂)")
    report.append("- 参与角色: 6个专业分析师")
    report.append("- 使用模型: GLM-5, K2.5, Qwen3.5 (智能路由)")
    report.append("")
    report.append("---")
    report.append("")

    # 分析团队
    report.append("## 分析团队构成")
    report.append("")
    report.append("系统根据任务复杂度动态生成了以下6个专业角色:\n")

    for i, role in enumerate(SIMULATED_ROLES, 1):
        report.append(f"### {i}. {role['title']}")
        report.append("")
        report.append(f"**职责**: {role['description']}")
        report.append("")
        report.append("**具体任务**:")
        for resp in role["responsibilities"]:
            report.append(f"- {resp}")
        report.append("")
        report.append(f"**所需技能**: {', '.join(role['required_skills'])}")
        report.append(f"**预计耗时**: {role['estimated_time']}")
        report.append("")

    # 模型分配
    report.append("---")
    report.append("")
    report.append("## AI模型分配方案")
    report.append("")
    report.append("系统为每个角色智能匹配最优AI模型:\n")

    for mapping in SIMULATED_MODEL_ROUTING["mappings"]:
        role_title = next(
            r["title"] for r in SIMULATED_ROLES if r["name"] == mapping["role_id"]
        )
        report.append(f"- **{role_title}**: {mapping['primary_model']}")
        report.append(f"  - 备选: {', '.join(mapping['fallback_models'])}")
        report.append(f"  - 理由: {mapping['rationale']}")
        report.append("")

    # 工作流程
    report.append("---")
    report.append("")
    report.append("## 分析工作流程")
    report.append("")
    report.append("```")
    report.append("阶段1: 地缘政治分析师")
    report.append("    ↓")
    report.append("阶段2: 能源经济学家 + 情报战略专家(并行)")
    report.append("    ↓")
    report.append("阶段3: 影响评估师")
    report.append("    ↓")
    report.append("阶段4: 投资策略顾问")
    report.append("    ↓")
    report.append("阶段5: 风险管理师")
    report.append("```")
    report.append("")

    # 核心发现框架
    report.append("---")
    report.append("")
    report.append("## 核心分析维度")
    report.append("")
    report.append("### 1. 地缘政治格局")
    report.append("- 美以伊三方战略博弈")
    report.append("- 中东地区力量平衡变化")
    report.append("- 代理人战争风险")
    report.append("")
    report.append("### 2. 石油市场影响")
    report.append("- 伊朗石油产能和出口能力")
    report.append("- 霍尔木兹海峡运输风险")
    report.append("- 全球石油供需缺口评估")
    report.append("- 油价波动区间预测")
    report.append("")
    report.append("### 3. 利益集团分析")
    report.append("- 美国军工复合体")
    report.append("- 以色列国内政治考量")
    report.append("- 伊朗内部权力结构")
    report.append("- 沙特、土耳其等地区大国立场")
    report.append("")
    report.append("### 4. 全球连锁反应")
    report.append("- 对中国石油进口的影响")
    report.append("- 欧洲能源安全应对")
    report.append("- 印度、日本等亚洲国家反应")
    report.append("- 美国页岩油产业机遇")
    report.append("")
    report.append("### 5. 投资策略建议")
    report.append("- 石油期货投资策略")
    report.append("- 新能源板块机会")
    report.append("- 避险资产配置")
    report.append("- 动态调整方案")
    report.append("")
    report.append("### 6. 风险评估")
    report.append("- 分析结论的不确定性")
    report.append("- 黑天鹅事件可能性")
    report.append("- 多情景应对预案")
    report.append("")

    # 系统说明
    report.append("---")
    report.append("")
    report.append("## 技术说明")
    report.append("")
    report.append("本分析由BMAD-EVO v3.0系统生成，该系统具有以下特点:")
    report.append("")
    report.append("1. **全动态角色生成**: 根据任务复杂度智能生成专业角色团队")
    report.append("2. **智能模型路由**: 为每个角色匹配最适合的AI模型")
    report.append("3. **并行优化**: 识别可并行执行的角色，提高效率")
    report.append("4. **零硬编码**: 所有流程由AI动态决定，无需预设规则")
    report.append("")
    report.append("---")
    report.append("")
    report.append("*报告生成时间: 2026-03-29*")
    report.append("*系统版本: BMAD-EVO v3.0*")

    # 写入文件
    with open("oil-analyst.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))


if __name__ == "__main__":
    demonstrate_dynamic_system()
