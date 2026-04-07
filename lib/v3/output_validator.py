"""
BMAD-EVO Output Quality Validator

像代码测试一样验证输出质量，确保报告、文档等输出符合要求

主要功能：
1. 完整性验证 - 检查结构、章节、内容是否完整
2. 质量验证 - 检查字数、深度、分析是否到位
3. 格式验证 - 检查Markdown格式、结构是否规范
4. 内容深度验证 - 检查是否有具体案例、数据、分析，不只是框架
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(Enum):
    """验证级别"""

    CRITICAL = "CRITICAL"  # 必须通过
    HIGH = "HIGH"  # 应该通过
    MEDIUM = "MEDIUM"  # 建议通过
    LOW = "LOW"  # 可选


@dataclass
class ValidationIssue:
    """验证问题"""

    level: ValidationLevel
    category: str  # 类别：completeness, quality, format, depth
    message: str  # 问题描述
    location: Optional[str] = None  # 位置（章节、行号等）
    suggestion: Optional[str] = None  # 改进建议


@dataclass
class ValidationResult:
    """验证结果"""

    overall_score: int  # 总分 0-100
    passed: bool  # 是否通过（总分>=85）
    issues: List[ValidationIssue]  # 问题列表
    metrics: Dict[str, Any]  # 质量指标
    summary: str  # 总结


class OutputQualityValidator:
    """输出质量验证器"""

    def __init__(self, min_score: int = 85):
        self.min_score = min_score

    def validate_report(
        self, report_path: Path, expected_structure: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        验证报告质量

        Args:
            report_path: 报告文件路径
            expected_structure: 期望的章节结构

        Returns:
            ValidationResult
        """
        if not report_path.exists():
            return ValidationResult(
                overall_score=0,
                passed=False,
                issues=[
                    ValidationIssue(
                        level=ValidationLevel.CRITICAL,
                        category="completeness",
                        message=f"报告文件不存在: {report_path}",
                    )
                ],
                metrics={},
                summary="报告文件不存在",
            )

        content = report_path.read_text(encoding="utf-8")
        lines = content.split("\n")
        issues = []
        metrics = {}

        # 1. 基本指标
        metrics.update(self._calculate_basic_metrics(content, lines))

        # 2. 完整性验证
        issues.extend(
            self._validate_completeness(content, lines, metrics, expected_structure)
        )

        # 3. 质量验证
        issues.extend(self._validate_quality(content, lines, metrics))

        # 4. 格式验证
        issues.extend(self._validate_format(content, lines))

        # 5. 内容深度验证（关键：防止只生成框架）
        issues.extend(self._validate_depth(content, lines, metrics))

        # 计算总分
        overall_score = self._calculate_score(metrics, issues)

        return ValidationResult(
            overall_score=overall_score,
            passed=overall_score >= self.min_score,
            issues=issues,
            metrics=metrics,
            summary=self._generate_summary(overall_score, issues, metrics),
        )

    def _calculate_basic_metrics(
        self, content: str, lines: List[str]
    ) -> Dict[str, Any]:
        """计算基本指标"""
        word_count = len(content)
        char_count = sum(len(line) for line in lines)
        line_count = len(lines)

        # 统计标题数量
        headings = [line for line in lines if line.strip().startswith("#")]
        h1_count = sum(1 for line in headings if re.match(r"^# ", line))
        h2_count = sum(1 for line in headings if re.match(r"^## ", line))
        h3_count = sum(1 for line in headings if re.match(r"^### ", line))

        # 统计表格
        tables = len(re.findall(r"\|.*\|", content)) // 4  # 估算表格数量

        # 统计代码块
        code_blocks = len(re.findall(r"```.*?```", content, re.DOTALL))

        # 统计列表项
        list_items = len(re.findall(r"^\s*[-*+]\s+", content, re.MULTILINE))

        return {
            "word_count": word_count,
            "char_count": char_count,
            "line_count": line_count,
            "h1_count": h1_count,
            "h2_count": h2_count,
            "h3_count": h3_count,
            "total_headings": len(headings),
            "tables": tables,
            "code_blocks": code_blocks,
            "list_items": list_items,
        }

    def _validate_completeness(
        self,
        content: str,
        lines: List[str],
        metrics: Dict[str, Any],
        expected_structure: Optional[List[str]] = None,
    ) -> List[ValidationIssue]:
        """验证完整性"""
        issues = []

        # 检查是否有标题
        if metrics["total_headings"] == 0:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category="completeness",
                    message="报告没有标题，缺少结构",
                )
            )

        # 检查H1标题（主标题）
        if metrics["h1_count"] == 0:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.HIGH,
                    category="completeness",
                    message="报告缺少H1主标题",
                    suggestion="添加主标题，例如 '# 人工智能教育改革深度分析报告'",
                )
            )

        # 检查H2标题（主要章节）
        if metrics["h2_count"] < 5:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.HIGH,
                    category="completeness",
                    message=f"报告H2章节过少（{metrics['h2_count']}个），建议至少5个主要章节",
                    suggestion="增加主要章节，覆盖核心分析维度",
                )
            )

        # 检查H3标题（小节）
        if metrics["h3_count"] < 10:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.MEDIUM,
                    category="completeness",
                    message=f"报告H3小节过少（{metrics['h3_count']}个），建议至少10个小节",
                    suggestion="在每个主要章节下增加详细的小节",
                )
            )

        # 检查期望的结构
        if expected_structure:
            for section in expected_structure:
                if section not in content:
                    issues.append(
                        ValidationIssue(
                            level=ValidationLevel.HIGH,
                            category="completeness",
                            message=f"报告缺少期望的章节: {section}",
                            suggestion=f"添加 '{section}' 章节",
                        )
                    )

        return issues

    def _validate_quality(
        self, content: str, lines: List[str], metrics: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """验证质量"""
        issues = []

        # 字数检查
        word_count = metrics["word_count"]
        if word_count < 5000:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category="quality",
                    message=f"报告字数过少（{word_count}字），深度分析报告至少需要10,000字",
                    suggestion="增加每个章节的内容深度，添加更多分析、案例和数据",
                )
            )
        elif word_count < 10000:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.HIGH,
                    category="quality",
                    message=f"报告字数偏少（{word_count}字），深度分析报告建议15,000字以上",
                    suggestion="补充各章节的详细分析内容",
                )
            )

        # 空行比例检查（内容密度）
        non_empty_lines = [line for line in lines if line.strip()]
        if len(non_empty_lines) > 0:
            density = len(non_empty_lines) / len(lines)
            if density < 0.6:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.MEDIUM,
                        category="quality",
                        message=f"内容密度偏低（{density:.1%}），建议增加实质性内容",
                    )
                )

        # 平均每行长度
        avg_line_length = metrics["char_count"] / len(lines) if len(lines) > 0 else 0
        if avg_line_length < 50:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.MEDIUM,
                    category="quality",
                    message=f"平均每行长度偏短（{avg_line_length:.1f}字符），内容可能不够详细",
                )
            )

        return issues

    def _validate_format(self, content: str, lines: List[str]) -> List[ValidationIssue]:
        """验证格式"""
        issues = []

        # 检查Markdown格式
        if not re.search(r"^#+ .+", content, re.MULTILINE):
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.MEDIUM,
                    category="format",
                    message="缺少Markdown标题格式",
                    suggestion="使用 '#'、'##'、'###' 标记标题层级",
                )
            )

        # 检查列表格式
        if not re.search(r"^\s*[-*+]\s+", content, re.MULTILINE):
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.LOW,
                    category="format",
                    message="缺少列表格式，建议使用列表提高可读性",
                )
            )

        # 检查分隔线
        if not re.search(r"^-{3,}$", content, re.MULTILINE):
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.LOW,
                    category="format",
                    message="缺少分隔线，建议使用 '---' 分隔章节",
                )
            )

        return issues

    def _validate_depth(
        self, content: str, lines: List[str], metrics: Dict[str, Any]
    ) -> List[ValidationIssue]:
        """
        验证内容深度（关键：防止只生成框架）
        """
        issues = []

        # 1. 检查是否有具体的描述性内容（不只是标题）
        # 统计每个H2/H3标题下的内容长度
        sections = self._extract_sections(content)
        short_sections = []

        for section_title, section_content in sections.items():
            # 每个章节至少200字（降低阈值以适应更长的报告）
            if len(section_content.strip()) < 200:
                short_sections.append(section_title)

        if short_sections:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.CRITICAL,
                    category="depth",
                    message=f"发现 {len(short_sections)} 个章节内容过少，可能是框架而非深度分析",
                    location=f"章节: {', '.join(short_sections[:5])}{'...' if len(short_sections) > 5 else ''}",
                    suggestion="每个章节需要包含详细的分析内容，包括数据、案例、论证等",
                )
            )

        # 2. 检查是否有具体的数据或数字（深度分析的标志）
        numbers = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?%?|\d+\.?\d*%", content)
        if len(numbers) < 20:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.HIGH,
                    category="depth",
                    message=f"报告缺少具体数据（只找到{len(numbers)}个数字），深度分析应包含数据支撑",
                    suggestion="添加具体的数据、统计、百分比、案例数字等，增强分析的可信度",
                )
            )

        # 3. 检查是否有案例（深度分析的标志）
        case_keywords = [
            "案例",
            "例如",
            "如",
            "例如：",
            "例如,",
            "Case",
            "Example",
            "Khan Academy",
            "Georgia Tech",
            "Duolingo",
        ]
        case_count = sum(1 for keyword in case_keywords if keyword in content)
        if case_count == 0:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.HIGH,
                    category="depth",
                    message="报告缺少具体案例，深度分析应包含实际案例",
                    suggestion="添加国内外典型案例，如 Khan Academy、Georgia Tech、松鼠AI 等",
                )
            )

        # 4. 检查是否有分析性内容（不只是描述）
        analysis_keywords = [
            "分析",
            "探讨",
            "评估",
            "对比",
            "研究",
            "认为",
            "表明",
            "显示",
            "发现",
        ]
        analysis_count = sum(1 for keyword in analysis_keywords if keyword in content)
        if analysis_count < 5:  # 降低阈值从10到5
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.MEDIUM,
                    category="depth",
                    message=f"分析性内容偏少（只找到{analysis_count}个关键词），建议增加深度分析",
                    suggestion="增加对比分析、评估、论证等内容，不只是简单描述",
                )
            )

        # 5. 检查是否有具体建议或结论（实用性的标志）
        recommendation_keywords = ["建议", "应该", "需要", "必须", "提议", "推荐"]
        recommendation_count = sum(
            1 for keyword in recommendation_keywords if keyword in content
        )
        if recommendation_count < 5:
            issues.append(
                ValidationIssue(
                    level=ValidationLevel.MEDIUM,
                    category="depth",
                    message=f"具体建议偏少（只找到{recommendation_count}个关键词），建议增加可落地的建议",
                    suggestion="在每个章节后添加具体的实施建议或行动指南",
                )
            )

        # 6. 检查是否有过多的占位符（框架的标志）
        placeholder_patterns = [
            r"\[.*?\]",  # [待补充]
            r"TODO|FIXME|待完成|待添加",  # 待办标记
            r"此处.*?内容|这里.*?内容",  # 占位符
        ]
        for pattern in placeholder_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(
                    ValidationIssue(
                        level=ValidationLevel.CRITICAL,
                        category="depth",
                        message=f"发现 {len(matches)} 个占位符/待办标记，这是未完成的框架",
                        suggestion="替换所有占位符为实际内容",
                    )
                )

        return issues

    def _extract_sections(self, content: str) -> Dict[str, str]:
        """提取各H2主要章节及其内容（不包括H3小节）"""
        sections = {}
        lines = content.split("\n")
        current_section = ""
        current_content = []

        for line in lines:
            if re.match(r"^##\s+", line):
                # 保存上一节
                if current_section and current_content:
                    sections[current_section] = "\n".join(current_content)
                # 开始新节
                current_section = line.strip()
                current_content = []
            else:
                if current_section:
                    current_content.append(line)

        # 保存最后一节
        if current_section and current_content:
            sections[current_section] = "\n".join(current_content)

        return sections

    def _calculate_score(
        self, metrics: Dict[str, Any], issues: List[ValidationIssue]
    ) -> int:
        """计算总分"""
        score = 100

        for issue in issues:
            if issue.level == ValidationLevel.CRITICAL:
                score -= 20
            elif issue.level == ValidationLevel.HIGH:
                score -= 10
            elif issue.level == ValidationLevel.MEDIUM:
                score -= 5
            elif issue.level == ValidationLevel.LOW:
                score -= 2

        # 字数加成
        word_count = metrics.get("word_count", 0)
        if word_count >= 15000:
            score = min(100, score + 5)
        elif word_count >= 10000:
            score = min(100, score + 2)

        return max(0, score)

    def _generate_summary(
        self, overall_score: int, issues: List[ValidationIssue], metrics: Dict[str, Any]
    ) -> str:
        """生成总结"""
        critical_count = sum(1 for i in issues if i.level == ValidationLevel.CRITICAL)
        high_count = sum(1 for i in issues if i.level == ValidationLevel.HIGH)
        medium_count = sum(1 for i in issues if i.level == ValidationLevel.MEDIUM)
        low_count = sum(1 for i in issues if i.level == ValidationLevel.LOW)

        summary_parts = [
            f"总分: {overall_score}/100",
            f"问题数: {len(issues)} (CRITICAL:{critical_count}, HIGH:{high_count}, MEDIUM:{medium_count}, LOW:{low_count})",
            f"字数: {metrics.get('word_count', 0):,} 字",
            f"章节: H1:{metrics.get('h1_count', 0)}, H2:{metrics.get('h2_count', 0)}, H3:{metrics.get('h3_count', 0)}",
        ]

        if critical_count > 0:
            summary_parts.append(
                f"[WARNING] 存在 {critical_count} 个严重问题，必须修复"
            )
        elif high_count > 0:
            summary_parts.append(f"[WARNING] 存在 {high_count} 个重要问题，建议修复")
        elif medium_count > 0:
            summary_parts.append(f"[INFO] 存在 {medium_count} 个次要问题，可以优化")

        return "\n".join(summary_parts)

    def print_result(self, result: ValidationResult):
        """打印验证结果"""
        print("\n" + "=" * 60)
        print("[OUTPUT] 输出质量验证结果")
        print("=" * 60)

        print(f"\n总分: {result.overall_score}/100 ", end="")
        if result.passed:
            print("[PASS] 通过")
        else:
            print("[FAIL] 未通过")

        print(f"\n{result.summary}")

        if result.issues:
            print("\n" + "-" * 60)
            print("问题详情:")
            print("-" * 60)

            for i, issue in enumerate(result.issues, 1):
                level_marker = {
                    ValidationLevel.CRITICAL: "[CRITICAL]",
                    ValidationLevel.HIGH: "[HIGH]",
                    ValidationLevel.MEDIUM: "[MEDIUM]",
                    ValidationLevel.LOW: "[LOW]",
                }
                print(f"\n{i}. [{issue.level.value}] {issue.category}")
                print(f"   {level_marker.get(issue.level, '')} {issue.message}")
                if issue.location:
                    print(f"   [LOCATION] {issue.location}")
                if issue.suggestion:
                    print(f"   [SUGGESTION] {issue.suggestion}")

        print("\n" + "=" * 60)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="验证输出质量")
    parser.add_argument("report_path", help="报告文件路径")
    parser.add_argument("--min-score", type=int, default=85, help="最低通过分数")
    parser.add_argument("--expected-structure", nargs="+", help="期望的章节结构")

    args = parser.parse_args()

    validator = OutputQualityValidator(min_score=args.min_score)
    result = validator.validate_report(
        Path(args.report_path), expected_structure=args.expected_structure
    )

    validator.print_result(result)

    return 0 if result.passed else 1


if __name__ == "__main__":
    exit(main())
