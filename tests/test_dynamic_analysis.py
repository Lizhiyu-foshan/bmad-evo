#!/usr/bin/env python3
"""
BMAD-EVO v3.0 动态分析测试
任务：美以打击伊朗对石油价格的地缘政治影响分析
"""

import sys
import json
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "lib" / "v3"))
sys.path.insert(0, str(Path(__file__).parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent / "agents"))

from lib.v3 import BMADEVO3

# 任务描述
TASK_DESCRIPTION = """
分析一下美以对伊朗的打击，对石油价格的冲击。

要求：
1. 分析要严谨、符合逻辑
2. 从大格局出发，不要只看石油价格
3. 要通观地缘政治格局
4. 分析背后利益集团
5. 预测各国的连锁反应
6. 评估对中国等石油进口国的影响
7. 提出投资策略建议

输出要求：
- 结构清晰，分章节论述
- 每个观点要有逻辑支撑
- 最后形成完整分析报告
"""


def main():
    print("=" * 80)
    print("BMAD-EVO v3.0 动态地缘政治分析测试")
    print("=" * 80)
    print("\n任务：美以打击伊朗的地缘政治与石油价格影响分析\n")
    print("=" * 80)

    # 初始化系统
    system = BMADEVO3(project_path="./test_oil_analysis", timeout=600, max_retries=2)

    # 执行任务
    result = system.execute(TASK_DESCRIPTION)

    # 保存完整结果
    output_dir = Path("./test_oil_analysis/.bmad/v3_results")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "execution_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    # 生成最终分析报告
    generate_final_report(result)

    print("\n" + "=" * 80)
    print("分析完成！")
    print(f"详细结果保存在: {output_dir}")
    print("=" * 80)


def generate_final_report(result):
    """生成最终分析报告"""

    # 提取各阶段输出
    execution_results = result.get("execution", {})

    report = []
    report.append("# 美以打击伊朗：地缘政治与石油价格影响深度分析报告")
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 执行摘要")
    report.append("")
    report.append(f"**任务类型**: {result['task_analysis']['task_type']}")
    report.append(f"**复杂度评分**: {result['task_analysis']['complexity_score']}/10")
    report.append(f"**参与角色数**: {result['summary']['total_roles']}")
    report.append(
        f"**成功执行**: {result['summary']['successful_executions']}/{result['summary']['total_roles']}"
    )
    report.append("")

    # 添加角色信息
    report.append("## 分析团队构成")
    report.append("")

    role_flow = result.get("role_flow", {})
    for role in role_flow.get("roles", []):
        report.append(f"### {role['title']}")
        report.append(f"- **职责**: {role['description']}")
        report.append(f"- **技能要求**: {', '.join(role['required_skills'])}")
        report.append("")

    report.append("## 模型分配")
    report.append("")

    routing = result.get("routing", {})
    for mapping in routing.get("mappings", []):
        report.append(f"- **{mapping['role_id']}**: {mapping['primary_model']}")

    report.append("")
    report.append("---")
    report.append("")

    # 添加各阶段分析结果
    report.append("## 详细分析内容")
    report.append("")

    for role_id, exec_result in execution_results.items():
        if exec_result.get("success"):
            report.append(f"### {role_id}")
            report.append("")
            report.append(exec_result.get("output", "无输出"))
            report.append("")
            report.append("---")
            report.append("")

    # 写入文件
    with open("oil-analyst.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))

    print(f"\n分析报告已保存到: oil-analyst.md")


if __name__ == "__main__":
    main()
