#!/usr/bin/env python3
"""
BMAD-EVO v3.1 代码审计工具

对核心模块进行全面审计，包括：
- 代码质量
- 一致性检查
- 潜在问题检测
- 文档完整性
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class AuditIssue:
    """审计问题"""

    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str
    file: str
    line: int
    message: str
    suggestion: Optional[str] = None


@dataclass
class FileAuditResult:
    """文件审计结果"""

    file: str
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    functions: List[str]
    classes: List[str]
    issues: List[AuditIssue]
    cyclomatic_complexity: Dict[str, int]
    documentation_score: float


class CodeAuditor:
    """代码审计器"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.issues: List[AuditIssue] = []
        self.results: Dict[str, FileAuditResult] = {}

    def audit_file(self, file_path: Path) -> FileAuditResult:
        """审计单个文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            issue = AuditIssue(
                severity="HIGH",
                category="READ_ERROR",
                file=str(file_path),
                line=0,
                message=f"无法读取文件: {e}",
            )
            self.issues.append(issue)
            return None

        lines = content.split("\n")
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = self._count_comment_lines(content)
        code_lines = total_lines - blank_lines - comment_lines

        # AST 解析
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            issue = AuditIssue(
                severity="CRITICAL",
                category="SYNTAX_ERROR",
                file=str(file_path),
                line=e.lineno,
                message=f"语法错误: {e.msg}",
            )
            self.issues.append(issue)
            return None

        # 提取函数和类
        functions = []
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

        # 计算圈复杂度
        complexity = self._calculate_complexity(tree)

        # 检查文档完整性
        doc_score = self._check_documentation(tree, content)

        # 运行各种检查
        self._check_naming_conventions(tree, str(file_path))
        self._check_function_length(tree, str(file_path), lines)
        self._check_code_smells(tree, str(file_path), content)
        self._check_imports(tree, str(file_path))
        self._check_todo_comments(content, str(file_path), lines)
        self._check_exception_handling(tree, str(file_path))

        result = FileAuditResult(
            file=str(file_path),
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            functions=functions,
            classes=classes,
            issues=[i for i in self.issues if i.file == str(file_path)],
            cyclomatic_complexity=complexity,
            documentation_score=doc_score,
        )

        self.results[str(file_path)] = result
        return result

    def _count_comment_lines(self, content: str) -> int:
        """计算注释行数"""
        lines = content.split("\n")
        count = 0
        in_docstring = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = not in_docstring
                count += 1
            elif in_docstring or stripped.startswith("#"):
                count += 1
        return count

    def _calculate_complexity(self, tree: ast.AST) -> Dict[str, int]:
        """计算圈复杂度"""
        complexity = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                cyclomatic = 1  # 基础复杂度
                for child in ast.walk(node):
                    if isinstance(
                        child, (ast.If, ast.While, ast.For, ast.ExceptHandler)
                    ):
                        cyclomatic += 1
                    elif isinstance(child, ast.BoolOp):
                        cyclomatic += len(child.values) - 1
                complexity[node.name] = cyclomatic

        return complexity

    def _check_documentation(self, tree: ast.AST, content: str) -> float:
        """检查文档完整性"""
        doc_functions = 0
        doc_classes = 0

        # 检查文件级文档
        module_doc = ast.get_docstring(tree)
        has_module_doc = module_doc is not None

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                doc = ast.get_docstring(node)
                if doc and len(doc) > 10:
                    doc_functions += 1
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                if doc and len(doc) > 10:
                    doc_classes += 1

        total_functions = sum(
            1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
        )
        total_classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))

        # 计算文档分数
        score = 0.0
        if has_module_doc:
            score += 0.2
        if total_functions > 0:
            score += 0.4 * (doc_functions / total_functions)
        if total_classes > 0:
            score += 0.4 * (doc_classes / total_classes)

        return round(score * 100, 1)

    def _check_naming_conventions(self, tree: ast.AST, file: str):
        """检查命名规范"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 函数名应该是 snake_case
                if not re.match(r"^[a-z_][a-z0-9_]*$", node.name):
                    self.issues.append(
                        AuditIssue(
                            severity="MEDIUM",
                            category="NAMING",
                            file=file,
                            line=node.lineno,
                            message=f"函数名 '{node.name}' 不符合 snake_case 命名规范",
                            suggestion="使用小写字母和下划线，如: my_function",
                        )
                    )

                # 参数名应该是 snake_case
                for arg in node.args.args:
                    if not re.match(r"^[a-z_][a-z0-9_]*$", arg.arg):
                        self.issues.append(
                            AuditIssue(
                                severity="LOW",
                                category="NAMING",
                                file=file,
                                line=node.lineno,
                                message=f"参数名 '{arg.arg}' 不符合 snake_case 命名规范",
                            )
                        )

            elif isinstance(node, ast.ClassDef):
                # 类名应该是 PascalCase
                if not re.match(r"^[A-Z][a-zA-Z0-9]*$", node.name):
                    self.issues.append(
                        AuditIssue(
                            severity="MEDIUM",
                            category="NAMING",
                            file=file,
                            line=node.lineno,
                            message=f"类名 '{node.name}' 不符合 PascalCase 命名规范",
                            suggestion="使用大驼峰命名，如: MyClass",
                        )
                    )

    def _check_function_length(self, tree: ast.AST, file: str, lines: List[str]):
        """检查函数长度"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 计算函数行数
                start_line = node.lineno
                end_line = (
                    node.end_lineno if hasattr(node, "end_lineno") else start_line
                )
                length = end_line - start_line + 1

                if length > 100:
                    self.issues.append(
                        AuditIssue(
                            severity="HIGH",
                            category="FUNCTION_LENGTH",
                            file=file,
                            line=start_line,
                            message=f"函数 '{node.name}' 过长 ({length} 行)",
                            suggestion="考虑将函数拆分为更小的子函数",
                        )
                    )
                elif length > 50:
                    self.issues.append(
                        AuditIssue(
                            severity="MEDIUM",
                            category="FUNCTION_LENGTH",
                            file=file,
                            line=start_line,
                            message=f"函数 '{node.name}' 较长 ({length} 行)",
                            suggestion="考虑是否可以简化逻辑",
                        )
                    )

    def _check_code_smells(self, tree: ast.AST, file: str, content: str):
        """检查代码异味"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检查参数数量
                args_count = len(node.args.args)
                if args_count > 7:
                    self.issues.append(
                        AuditIssue(
                            severity="MEDIUM",
                            category="CODE_SMELL",
                            file=file,
                            line=node.lineno,
                            message=f"函数 '{node.name}' 参数过多 ({args_count} 个)",
                            suggestion="考虑使用参数对象或配置字典",
                        )
                    )

    def _check_imports(self, tree: ast.AST, file: str):
        """检查导入"""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}")

        # 检查重复导入
        seen = {}
        for imp in imports:
            if imp in seen:
                self.issues.append(
                    AuditIssue(
                        severity="LOW",
                        category="DUPLICATE_IMPORT",
                        file=file,
                        line=seen[imp],
                        message=f"重复的导入: {imp}",
                    )
                )
            seen[imp] = 0  # 简化处理

    def _check_todo_comments(self, content: str, file: str, lines: List[str]):
        """检查 TODO 注释"""
        for i, line in enumerate(lines, 1):
            if re.search(r"\bTODO\b", line, re.IGNORECASE):
                self.issues.append(
                    AuditIssue(
                        severity="INFO",
                        category="TODO_COMMENT",
                        file=file,
                        line=i,
                        message=f"发现 TODO 注释",
                        suggestion="记得完成 TODO 事项",
                    )
                )

    def _check_exception_handling(self, tree: ast.AST, file: str):
        """检查异常处理"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if handler.type is None:
                        # 裸 except
                        self.issues.append(
                            AuditIssue(
                                severity="HIGH",
                                category="EXCEPTION_HANDLING",
                                file=file,
                                line=handler.lineno,
                                message="使用裸 except 语句",
                                suggestion="指定具体的异常类型",
                            )
                        )

    def audit_directory(
        self, directory: Path, pattern: str = "*.py"
    ) -> List[FileAuditResult]:
        """审计整个目录"""
        results = []
        for file_path in directory.rglob(pattern):
            if "__pycache__" in str(file_path):
                continue

            print(f"审计中: {file_path.relative_to(self.project_path)}")
            result = self.audit_file(file_path)
            if result:
                results.append(result)

        return results

    def generate_report(self) -> str:
        """生成审计报告"""
        lines = [
            "# BMAD-EVO v3.1 代码审计报告",
            "",
            f"**审计时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**项目路径**: {self.project_path}",
            f"**审计文件数**: {len(self.results)}",
            f"**发现问题数**: {len(self.issues)}",
            "",
            "---",
            "",
        ]

        # 问题统计
        severity_count = {}
        for issue in self.issues:
            severity_count[issue.severity] = severity_count.get(issue.severity, 0) + 1

        lines.extend(
            [
                "## 问题统计",
                "",
                "| 严重级别 | 数量 |",
                "|---------|------|",
            ]
        )

        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
            count = severity_count.get(severity, 0)
            emoji = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢",
                "INFO": "ℹ️",
            }.get(severity, "")
            lines.append(f"| {emoji} {severity} | {count} |")

        lines.extend(["", "---", "", "## 详细问题", ""])

        # 按文件分组
        file_issues = {}
        for issue in self.issues:
            if issue.file not in file_issues:
                file_issues[issue.file] = []
            file_issues[issue.file].append(issue)

        for file, issues in sorted(file_issues.items()):
            rel_file = Path(file).relative_to(self.project_path)
            lines.append(f"\n### {rel_file}")
            lines.append("")

            for issue in sorted(issues, key=lambda x: (x.severity, x.line)):
                emoji = {
                    "CRITICAL": "🔴",
                    "HIGH": "🟠",
                    "MEDIUM": "🟡",
                    "LOW": "🟢",
                    "INFO": "ℹ️",
                }.get(issue.severity, "")
                lines.append(
                    f"- {emoji} **{issue.severity}** (行 {issue.line}): {issue.message}"
                )
                if issue.suggestion:
                    lines.append(f"  💡 {issue.suggestion}")

        # 文件统计
        lines.extend(
            [
                "",
                "---",
                "",
                "## 文件统计",
                "",
                "| 文件 | 总行数 | 代码行 | 注释行 | 文档分 | 平均复杂度 |",
            ]
        )
        lines.append("|------|--------|--------|--------|--------|------------|")

        for file_path, result in sorted(self.results.items()):
            rel_file = Path(file_path).relative_to(self.project_path)
            avg_complexity = (
                sum(result.cyclomatic_complexity.values())
                / len(result.cyclomatic_complexity)
                if result.cyclomatic_complexity
                else 0
            )
            doc_status = (
                "✅"
                if result.documentation_score >= 80
                else "⚠️"
                if result.documentation_score >= 50
                else "❌"
            )

            lines.append(
                f"| {rel_file} | {result.total_lines} | {result.code_lines} | "
                f"{result.comment_lines} | {doc_status} {result.documentation_score}% | "
                f"{avg_complexity:.1f} |"
            )

        # 建议
        lines.extend(["", "---", "", "## 改进建议", ""])

        if severity_count.get("CRITICAL", 0) > 0:
            lines.append(
                "1. 🔴 **优先修复所有 CRITICAL 级别问题**，这些是语法错误或严重缺陷"
            )

        if severity_count.get("HIGH", 0) > 0:
            lines.append(
                "2. 🟠 **修复所有 HIGH 级别问题**，包括函数过长、异常处理不当等"
            )

        low_doc_files = sum(
            1 for r in self.results.values() if r.documentation_score < 80
        )
        if low_doc_files > 0:
            lines.append(
                f"3. 📝 **提高文档覆盖率**，{low_doc_files} 个文件文档完整性不足 80%"
            )

        high_complexity_files = sum(
            1
            for r in self.results.values()
            if r.cyclomatic_complexity
            and any(c > 10 for c in r.cyclomatic_complexity.values())
        )
        if high_complexity_files > 0:
            lines.append(
                f"4. 🔄 **降低复杂度**，{high_complexity_files} 个文件存在高复杂度函数"
            )

        lines.extend(["", "---", "", "*本报告由 BMAD-EVO 代码审计工具自动生成*"])

        return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="BMAD-EVO 代码审计工具")
    parser.add_argument("--project", default=".", help="项目路径")
    parser.add_argument("--output", default="audit_report.md", help="输出报告文件")
    args = parser.parse_args()

    auditor = CodeAuditor(args.project)
    auditor.audit_directory(Path(args.project))

    report = auditor.generate_report()

    # 保存报告
    report_path = Path(args.project) / args.output
    report_path.write_text(report, encoding="utf-8")

    print(f"\n审计完成！")
    print(f"报告已保存到: {report_path}")
    print(f"\n问题统计:")
    severity_count = {}
    for issue in auditor.issues:
        severity_count[issue.severity] = severity_count.get(issue.severity, 0) + 1
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
        count = severity_count.get(severity, 0)
        if count > 0:
            print(f"  {severity}: {count}")


if __name__ == "__main__":
    main()
