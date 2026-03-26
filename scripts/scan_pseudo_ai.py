#!/usr/bin/env python3
"""
BMAD-EVO 伪AI代码扫描器

检测代码中假装调用AI但实际上返回模拟结果的情况。

检测模式:
1. 函数声明包含AI相关关键词，但直接返回硬编码字典/字符串
2. 注释中包含"模拟"、"mock"、"简化版"、"示例"等关键词，且后面跟着return语句
3. 函数内部有AI相关注释，但实际返回的是模板字符串或固定结构
4. OpenClaw调用失败时自动回退到mock模式（隐藏问题）

运行方式:
    python3 scan_pseudo_ai.py your_code.py
    python3 scan_pseudo_ai.py --directory ./lib
    python3 scan_pseudo_ai.py --ci-mode  # CI模式，返回非零退出码
"""

import ast
import sys
import re
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PseudoAIHit:
    """伪AI代码命中记录"""
    file_path: str
    line_number: int
    function_name: str
    issue_type: str  # 'hardcoded_return', 'mock_fallback', 'template_response', 'comment_simulation'
    description: str
    evidence: str
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM'


class PseudoAIScanner(ast.NodeVisitor):
    """AST扫描器，检测伪AI代码模式"""
    
    # AI相关函数名模式
    AI_FUNCTION_PATTERNS = [
        r'(?i)ai[_-]?',           # ai_, ai-, ai
        r'(?i)gpt[_-]?',          # gpt_, gpt-, gpt
        r'(?i)llm[_-]?',          # llm_, llm-, llm
        r'(?i)generate',          # generate
        r'(?i)analyze[_-]?',      # analyze, analyse
        r'(?i)process[_-]?with[_-]?ai',
        r'(?i)call[_-]?ai',
        r'(?i)agent[_-]?executor',
        r'(?i)sessions[_-]?spawn',
        r'(?i)ask[_-]?ai',
    ]
    
    # 排除模式（这些不是伪AI）
    EXCLUDE_PATTERNS = [
        r'(?i)create[_-]?default',      # create_default_xxx 是配置生成
        r'(?i)load[_-]?default',
        r'(?i)default[_-]?config',
        r'(?i)_generate[_-]?summary',   # 内部摘要生成
        r'(?i)_generate[_-]?fallback',  # 错误回退输出
        r'(?i)format[_-]?',             # 格式化函数
        r'(?i)_generate[_-]?final[_-]?report',  # 最终报告生成（返回结构化数据是正常的）
        r'(?i)_generate[_-]?output',    # 输出生成
        r'(?i)build[_-]?',              # 构建函数
        r'(?i)create[_-]?',             # 创建函数
    ]
    
    # 模拟相关关键词
    MOCK_KEYWORDS = [
        r'(?i)模拟',
        r'(?i)mock',
        r'(?i)简化版',
        r'(?i)示例',
        r'(?i)placeholder',
        r'(?i)TODO.*AI',
        r'(?i)FIXME.*AI',
        r'(?i)实际应调用',
        r'(?i)这里返回模拟',
        r'(?i)硬编码',
    ]
    
    # 模板标记
    TEMPLATE_MARKERS = [
        r'XX', r'YY', r'XXX', r'YYY',
        r'\{placeholder\}',
        r'<placeholder>',
        r'\$\{[^}]+\}',  # ${variable}
    ]
    
    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.source_lines = source_code.split('\n')
        self.hits: List[PseudoAIHit] = []
        self.current_function: Optional[str] = None
        self.function_has_ai_comment = False
        self.comment_line_numbers = set()
    
    def _is_ai_related_function(self, func_name: str) -> bool:
        """检查函数名是否与AI相关"""
        # 先检查排除模式
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, func_name):
                return False
        
        for pattern in self.AI_FUNCTION_PATTERNS:
            if re.search(pattern, func_name):
                return True
        return False
    
    def _has_mock_keywords_in_comment(self, node) -> tuple[bool, str]:
        """检查节点附近的注释是否包含模拟关键词"""
        # 获取节点所在行的前后几行
        start_line = max(0, node.lineno - 5)
        end_line = min(len(self.source_lines), node.end_lineno + 2)
        
        for line_no in range(start_line, end_line):
            if line_no < len(self.source_lines):
                line = self.source_lines[line_no]
                # 检查是否是注释行
                if '#' in line:
                    comment_part = line[line.index('#'):]
                    for pattern in self.MOCK_KEYWORDS:
                        if re.search(pattern, comment_part):
                            return True, comment_part.strip()
        return False, ""
    
    def _is_hardcoded_dict(self, node) -> bool:
        """检查是否返回硬编码字典"""
        if isinstance(node, ast.Dict):
            return True
        if isinstance(node, ast.Call):
            # 检查是否是dict()调用
            if isinstance(node.func, ast.Name) and node.func.id == 'dict':
                return True
        return False
    
    def _is_template_response(self, node) -> bool:
        """检查是否返回模板字符串"""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for pattern in self.TEMPLATE_MARKERS:
                if re.search(pattern, node.value):
                    return True
        if isinstance(node, ast.JoinedStr):  # f-string
            # 检查是否主要是模板
            return True
        if isinstance(node, ast.List) or isinstance(node, ast.Tuple):
            # 检查列表/元组中的元素
            for elt in node.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    for pattern in self.TEMPLATE_MARKERS:
                        if re.search(pattern, elt.value):
                            return True
        return False
    
    def _check_return_statement(self, node):
        """检查return语句"""
        if not self.current_function:
            return
        
        # 检查是否返回硬编码值
        if node.value:
            # 情况1: 返回硬编码字典（最常见）
            if self._is_hardcoded_dict(node.value):
                has_mock_comment, comment = self._has_mock_keywords_in_comment(node)
                if has_mock_comment or self._is_ai_related_function(self.current_function):
                    self.hits.append(PseudoAIHit(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        function_name=self.current_function,
                        issue_type='hardcoded_return',
                        description='函数声明与AI相关，但直接返回硬编码字典（可能是模拟结果）',
                        evidence=f"return {ast.unparse(node.value)[:100]}..." if hasattr(ast, 'unparse') else f"return <hardcoded dict>",
                        severity='CRITICAL'
                    ))
            
            # 情况2: 返回模板字符串
            elif self._is_template_response(node.value):
                if self._is_ai_related_function(self.current_function):
                    self.hits.append(PseudoAIHit(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        function_name=self.current_function,
                        issue_type='template_response',
                        description='返回包含模板标记（XX/YY/placeholder）的响应，可能是假AI生成',
                        evidence=f"return {ast.unparse(node.value)[:100]}..." if hasattr(ast, 'unparse') else f"return <template>",
                        severity='HIGH'
                    ))
            
            # 情况3: 返回固定字符串，且附近有模拟注释
            elif isinstance(node.value, ast.Constant):
                has_mock_comment, comment = self._has_mock_keywords_in_comment(node)
                if has_mock_comment and self._is_ai_related_function(self.current_function):
                    self.hits.append(PseudoAIHit(
                        file_path=self.file_path,
                        line_number=node.lineno,
                        function_name=self.current_function,
                        issue_type='comment_simulation',
                        description=f'注释表明这是模拟实现: {comment}',
                        evidence=f"return {repr(node.value.value)[:100]}",
                        severity='CRITICAL'
                    ))
    
    def visit_FunctionDef(self, node):
        """访问函数定义"""
        old_function = self.current_function
        self.current_function = node.name
        
        # 检查函数是否是AI相关
        is_ai_func = self._is_ai_related_function(node.name)
        
        # 检查函数文档字符串和注释
        has_mock_doc = False
        if ast.get_docstring(node):
            for pattern in self.MOCK_KEYWORDS:
                if re.search(pattern, ast.get_docstring(node)):
                    has_mock_doc = True
                    break
        
        # 遍历函数体
        self.generic_visit(node)
        
        self.current_function = old_function
    
    def visit_Return(self, node):
        """访问return语句"""
        self._check_return_statement(node)
        self.generic_visit(node)
    
    def visit_ExceptHandler(self, node):
        """访问异常处理器 - 检测mock回退模式"""
        if node.type:
            # 检查是否是捕获OpenClaw/RuntimeError后回退到mock
            type_name = ast.unparse(node.type) if hasattr(ast, 'unparse') else str(node.type)
            if 'OpenClaw' in type_name or 'RuntimeError' in type_name or 'Exception' in type_name:
                # 检查异常处理块中是否有mock相关代码
                for stmt in node.body:
                    stmt_code = ast.unparse(stmt) if hasattr(ast, 'unparse') else ""
                    if 'mock' in stmt_code.lower() or '模拟' in stmt_code:
                        self.hits.append(PseudoAIHit(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            function_name=self.current_function or '<module>',
                            issue_type='mock_fallback',
                            description='OpenClaw/AI调用失败时自动回退到mock模式，可能隐藏真实问题',
                            evidence=f"except {type_name}: ... mock fallback",
                            severity='HIGH'
                        ))
                        break
        self.generic_visit(node)


def scan_file(file_path: Path) -> List[PseudoAIHit]:
    """扫描单个文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        scanner = PseudoAIScanner(str(file_path), source)
        scanner.visit(tree)
        return scanner.hits
    except SyntaxError as e:
        print(f"⚠️ 语法错误跳过 {file_path}: {e}")
        return []
    except Exception as e:
        print(f"⚠️ 扫描失败 {file_path}: {e}")
        return []


def scan_directory(directory: Path, pattern: str = "*.py") -> List[PseudoAIHit]:
    """扫描目录"""
    all_hits = []
    for file_path in directory.rglob(pattern):
        if '.git' in str(file_path) or '__pycache__' in str(file_path):
            continue
        hits = scan_file(file_path)
        all_hits.extend(hits)
    return all_hits


def print_report(hits: List[PseudoAIHit], verbose: bool = False):
    """打印扫描报告"""
    if not hits:
        print("✅ 未发现伪AI代码！")
        return
    
    print(f"\n🔍 发现 {len(hits)} 处伪AI代码:\n")
    
    # 按严重程度排序
    severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2}
    hits.sort(key=lambda h: severity_order.get(h.severity, 3))
    
    for i, hit in enumerate(hits, 1):
        severity_icon = {
            'CRITICAL': '🔴',
            'HIGH': '🟠',
            'MEDIUM': '🟡'
        }.get(hit.severity, '⚪')
        
        print(f"{i}. {severity_icon} [{hit.severity}] {hit.issue_type}")
        print(f"   文件: {hit.file_path}:{hit.line_number}")
        print(f"   函数: {hit.function_name}")
        print(f"   问题: {hit.description}")
        if verbose:
            print(f"   证据: {hit.evidence}")
        print()
    
    # 统计
    critical = sum(1 for h in hits if h.severity == 'CRITICAL')
    high = sum(1 for h in hits if h.severity == 'HIGH')
    medium = sum(1 for h in hits if h.severity == 'MEDIUM')
    
    print("=" * 80)
    print(f"统计: CRITICAL={critical}, HIGH={high}, MEDIUM={medium}")


def main():
    parser = argparse.ArgumentParser(
        description="BMAD-EVO 伪AI代码扫描器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s your_code.py              # 扫描单个文件
  %(prog)s --directory ./lib         # 扫描目录
  %(prog)s --ci-mode                 # CI模式（有伪AI代码时返回非零）
  %(prog)s --verbose                 # 显示详细信息
        """
    )
    
    parser.add_argument(
        "files",
        nargs="*",
        help="要扫描的Python文件"
    )
    
    parser.add_argument(
        "--directory", "-d",
        type=Path,
        help="扫描整个目录"
    )
    
    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="CI模式：发现伪AI代码时返回非零退出码"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细信息"
    )
    
    parser.add_argument(
        "--pattern",
        default="*.py",
        help="文件匹配模式（默认: *.py）"
    )
    
    args = parser.parse_args()
    
    all_hits = []
    
    # 扫描指定文件
    if args.files:
        for file_path in args.files:
            path = Path(file_path)
            if path.exists():
                hits = scan_file(path)
                all_hits.extend(hits)
    
    # 扫描目录
    if args.directory:
        if args.directory.exists():
            hits = scan_directory(args.directory, args.pattern)
            all_hits.extend(hits)
        else:
            print(f"❌ 目录不存在: {args.directory}")
            return 1
    
    # 如果没有指定文件或目录，显示帮助
    if not args.files and not args.directory:
        parser.print_help()
        return 0
    
    # 打印报告
    print_report(all_hits, args.verbose)
    
    # CI模式：有CRITICAL或HIGH问题时返回非零
    if args.ci_mode:
        critical_high = [h for h in all_hits if h.severity in ('CRITICAL', 'HIGH')]
        if critical_high:
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
