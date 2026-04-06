#!/usr/bin/env python3
"""
BMAD-EVO v3.1 全面测试脚本

运行代码审计、单元测试、集成测试，生成综合报告
"""

import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime


def run_code_auditor(project_path: str) -> dict:
    """运行代码审计"""
    print("\n" + "=" * 70)
    print("步骤 1: 代码审计")
    print("=" * 70)

    auditor_script = Path(__file__).parent.parent / "scripts" / "code_auditor.py"
    output_file = Path(project_path) / "audit_report.md"

    cmd = [
        sys.executable,
        str(auditor_script),
        "--project",
        project_path,
        "--output",
        "audit_report.md",
    ]

    print(f"运行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    # 解析审计报告
    if output_file.exists():
        with open(output_file, "r", encoding="utf-8") as f:
            content = f.read()

        # 提取统计信息
        issues = {}
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            if f"{severity} |" in content:
                line = [l for l in content.split("\n") if f"{severity} |" in l]
                if line:
                    parts = line[0].split("|")
                    if len(parts) >= 3:
                        try:
                            issues[severity] = int(parts[2].strip())
                        except Exception:
                            issues[severity] = 0

        return {
            "success": result.returncode == 0,
            "issues": issues,
            "output_file": str(output_file),
        }
    else:
        return {"success": False, "issues": {}, "error": "审计报告未生成"}


def run_unit_tests(project_path: str) -> dict:
    """运行单元测试"""
    print("\n" + "=" * 70)
    print("步骤 2: 单元测试")
    print("=" * 70)

    test_script = Path(__file__).parent / "test_unit.py"

    cmd = [sys.executable, str(test_script)]

    print(f"运行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    # 解析测试结果
    passed = 0
    failed = 0
    lines = result.stdout.split("\n")

    for line in lines:
        if "通过: " in line and "✅" in line:
            try:
                passed = int(line.split("通过:")[1].split()[0])
            except Exception:
                pass
        elif "失败: " in line and "❌" in line:
            try:
                failed = int(line.split("失败:")[1].split()[0])
            except Exception:
                pass

    return {
        "success": result.returncode == 0,
        "passed": passed,
        "failed": failed,
        "total": passed + failed,
    }


def run_integration_tests(project_path: str) -> dict:
    """运行集成测试"""
    print("\n" + "=" * 70)
    print("步骤 3: 集成测试")
    print("=" * 70)

    test_script = Path(__file__).parent / "test_integration.py"

    cmd = [sys.executable, str(test_script)]

    print(f"运行: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_path)

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    # 解析测试结果
    passed = 0
    failed = 0
    lines = result.stdout.split("\n")

    for line in lines:
        if "通过: " in line and "✅" in line:
            try:
                passed = int(line.split("通过:")[1].split()[0])
            except Exception:
                pass
        elif "失败: " in line and "❌" in line:
            try:
                failed = int(line.split("失败:")[1].split()[0])
            except Exception:
                pass

    return {
        "success": result.returncode == 0,
        "passed": passed,
        "failed": failed,
        "total": passed + failed,
    }


def generate_comprehensive_report(
    project_path: str,
    audit_result: dict,
    unit_test_result: dict,
    integration_test_result: dict,
) -> str:
    """生成综合测试报告"""
    lines = [
        "# BMAD-EVO v3.1 综合测试报告",
        "",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**项目路径**: {project_path}",
        f"**版本**: v3.1.0",
        "",
        "---",
        "",
        "## 执行摘要",
        "",
    ]

    # 代码审计摘要
    audit_issues = audit_result.get("issues", {})
    total_issues = sum(audit_issues.values())
    critical_issues = audit_issues.get("CRITICAL", 0)
    high_issues = audit_issues.get("HIGH", 0)

    audit_status = (
        "✅ 通过" if critical_issues == 0 and high_issues == 0 else "⚠️ 需要修复"
    )

    lines.extend(
        [
            f"| 测试类型 | 状态 | 详情 |",
            f"|---------|------|------|",
            f"| 代码审计 | {audit_status} | {total_issues} 个问题 ({critical_issues} CRITICAL, {high_issues} HIGH) |",
        ]
    )

    # 单元测试摘要
    unit_status = "✅ 通过" if unit_test_result.get("success") else "❌ 失败"
    unit_total = unit_test_result.get("total", 0)
    unit_passed = unit_test_result.get("passed", 0)
    unit_rate = (unit_passed / unit_total * 100) if unit_total > 0 else 0

    lines.append(
        f"| 单元测试 | {unit_status} | {unit_passed}/{unit_total} 通过 ({unit_rate:.1f}%) |"
    )

    # 集成测试摘要
    integration_status = (
        "✅ 通过" if integration_test_result.get("success") else "❌ 失败"
    )
    integration_total = integration_test_result.get("total", 0)
    integration_passed = integration_test_result.get("passed", 0)
    integration_rate = (
        (integration_passed / integration_total * 100) if integration_total > 0 else 0
    )

    lines.append(
        f"| 集成测试 | {integration_status} | {integration_passed}/{integration_total} 通过 ({integration_rate:.1f}%) |"
    )

    # 综合评分
    lines.extend(["", "---", "", "## 综合评分", ""])

    score = 100

    # 代码审计扣分
    score -= critical_issues * 20
    score -= high_issues * 10
    score -= audit_issues.get("MEDIUM", 0) * 5
    score -= audit_issues.get("LOW", 0) * 2

    # 单元测试扣分
    if unit_total > 0:
        score -= (unit_total - unit_passed) * 10

    # 集成测试扣分
    if integration_total > 0:
        score -= (integration_total - integration_passed) * 10

    score = max(0, min(100, score))

    if score >= 90:
        grade = "A"
        grade_desc = "优秀"
    elif score >= 80:
        grade = "B"
        grade_desc = "良好"
    elif score >= 70:
        grade = "C"
        grade_desc = "及格"
    else:
        grade = "D"
        grade_desc = "不合格"

    lines.extend(
        [
            f"**综合评分**: {score}/100",
            f"**等级**: {grade} - {grade_desc}",
            "",
        ]
    )

    # 详细结果
    lines.extend(["", "---", "", "## 代码审计详情", ""])

    if audit_result.get("output_file"):
        lines.append(f"详细审计报告: `{audit_result['output_file']}`")

    if audit_issues:
        lines.extend(
            [
                "",
                "### 问题统计",
                "",
                "| 严重级别 | 数量 |",
                "|---------|------|",
            ]
        )

        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            count = audit_issues.get(severity, 0)
            if count > 0:
                emoji = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟠",
                    "MEDIUM": "🟡",
                    "LOW": "🟢",
                    "INFO": "ℹ️",
                }.get(severity, "")
                lines.append(f"| {emoji} {severity} | {count} |")

    # 单元测试详情
    lines.extend(["", "---", "", "## 单元测试详情", ""])

    unit_failed = unit_total - unit_passed
    lines.extend(
        [
            "",
            f"- **测试总数**: {unit_total}",
            f"- **通过**: {unit_passed}",
            f"- **失败**: {unit_failed}",
            f"- **通过率**: {unit_rate:.1f}%",
        ]
    )

    if unit_failed > 0:
        lines.extend(
            [
                "",
                "[WARN] **需要修复失败的单元测试**",
            ]
        )

    # 集成测试详情
    lines.extend(["", "---", "", "## 集成测试详情", ""])

    integration_failed = integration_total - integration_passed
    lines.extend(
        [
            "",
            f"- **测试总数**: {integration_total}",
            f"- **通过**: {integration_passed}",
            f"- **失败**: {integration_failed}",
            f"- **通过率**: {integration_rate:.1f}%",
        ]
    )

    if integration_failed > 0:
        lines.extend(
            [
                "",
                "⚠️  **需要修复失败的集成测试**",
            ]
        )

    # 建议
    lines.extend(["", "---", "", "## 改进建议", ""])

    suggestions = []

    if critical_issues > 0:
        suggestions.append(
            f"1. 🔴 **立即修复所有 {critical_issues} 个 CRITICAL 级别问题**"
        )

    if high_issues > 0:
        suggestions.append(f"2. 🟠 **优先修复所有 {high_issues} 个 HIGH 级别问题**")

    if unit_failed > 0:
        suggestions.append(f"3. 🧪 **修复 {unit_failed} 个失败的单元测试**")

    if integration_failed > 0:
        suggestions.append(f"4. 🔗 **修复 {integration_failed} 个失败的集成测试**")

    if not suggestions:
        suggestions.append("✅ **所有测试通过，代码质量良好！**")

    lines.extend(suggestions)

    lines.extend(["", "---", "", "*本报告由 BMAD-EVO 测试框架自动生成*"])

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="BMAD-EVO v3.1 全面测试")
    parser.add_argument("--project", default=".", help="项目路径")
    parser.add_argument(
        "--output", default="comprehensive_test_report.md", help="输出报告文件"
    )
    args = parser.parse_args()

    project_path = Path(args.project).absolute()

    print("=" * 70)
    print("BMAD-EVO v3.1 全面测试")
    print("=" * 70)
    print(f"项目路径: {project_path}")
    print(f"报告文件: {args.output}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 运行所有测试
    audit_result = run_code_auditor(str(project_path))
    unit_test_result = run_unit_tests(str(project_path))
    integration_test_result = run_integration_tests(str(project_path))

    # 生成综合报告
    print("\n" + "=" * 70)
    print("生成综合报告")
    print("=" * 70)

    report = generate_comprehensive_report(
        str(project_path), audit_result, unit_test_result, integration_test_result
    )

    # 保存报告
    report_path = project_path / args.output
    report_path.write_text(report, encoding="utf-8")

    print(f"\n报告已保存到: {report_path}")

    # 显示摘要
    print("\n" + "=" * 70)
    print("测试完成摘要")
    print("=" * 70)

    audit_issues = audit_result.get("issues", {})
    print(f"\n代码审计: {sum(audit_issues.values())} 个问题")

    unit_total = unit_test_result.get("total", 0)
    unit_passed = unit_test_result.get("passed", 0)
    print(f"单元测试: {unit_passed}/{unit_total} 通过")

    integration_total = integration_test_result.get("total", 0)
    integration_passed = integration_test_result.get("passed", 0)
    print(f"集成测试: {integration_passed}/{integration_total} 通过")

    print(f"\n综合报告: {report_path}")


if __name__ == "__main__":
    main()
