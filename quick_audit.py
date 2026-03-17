#!/usr/bin/env python3
"""
BMAD-EVO 快速审计工具

用于快速检查代码质量，无需完整 Phase Gateway 流程

使用场景:
- 开发时快速检查
- Git pre-commit hook
- CI/CD 集成

运行方式:
    python3 quick_audit.py your_code.py
    python3 quick_audit.py --mode strict your_code.py
    cat your_code.py | python3 quick_audit.py --stdin
"""

import sys
import argparse
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from constraint_checker import check_constraints
from ast_auditor import audit_code as ast_audit

def load_default_constraints():
    """加载默认约束模板"""
    import yaml
    template_path = Path(__file__).parent / "templates" / "constraints" / "ast-cron-job.yaml"
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}

def audit_file(file_path: str, mode: str = "fast"):
    """审计单个文件"""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ 文件不存在：{file_path}")
        return False
    
    print(f"🔍 审计文件：{file_path}")
    print(f"模式：{mode}")
    print("-" * 80)
    
    with open(path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    if mode == "fast":
        # AST only - 快速模式
        result = ast_audit(code, file_path=str(path))
        print(f"分析时间：{result.analysis_time_ms:.2f}ms")
        print(f"发现问题：{len(result.violations)}")
        print()
        
        if not result.passed:
            for i, v in enumerate(result.violations, 1):
                print(f"{i}. [{v.severity.value.upper()}] {v.description}")
                print(f"   行 {v.line_number}: {v.evidence}")
                print(f"   建议：{v.suggestion}")
                print()
    else:
        # Strict mode - AST + regex
        constraints = load_default_constraints()
        result = check_constraints(code, constraints, mode=mode)
        print(f"得分：{result.score}/100")
        print(f"通过：{result.passed}")
        print(f"发现问题：{len(result.violations)}")
        print(f"必须修复：{result.must_fix}")
        print()
        
        if result.violations:
            for i, v in enumerate(result.violations, 1):
                source_icon = "🎯" if v.source == "ast" else "📝"
                print(f"{i}. {source_icon} [{v.severity.value.upper()}] {v.description}")
                print(f"   行 {v.line_number}: {v.evidence[:80]}...")
                if v.fix_example:
                    print(f"   修复：{v.fix_example.split(chr(10))[0]}")
                print()
    
    # Summary
    print("=" * 80)
    if result.passed:
        print(f"✅ 审计通过！")
        return True
    else:
        print(f"❌ 审计失败！需要修复 {len(result.violations)} 个问题")
        return False

def audit_stdin(mode: str = "fast"):
    """从标准输入审计代码"""
    code = sys.stdin.read()
    
    print(f"🔍 审计标准输入代码")
    print(f"模式：{mode}")
    print("-" * 80)
    
    if mode == "fast":
        result = ast_audit(code, file_path="<stdin>")
        print(f"分析时间：{result.analysis_time_ms:.2f}ms")
        print(f"发现问题：{len(result.violations)}")
        print()
        
        if not result.passed:
            for i, v in enumerate(result.violations, 1):
                print(f"{i}. [{v.severity.value.upper()}] {v.description}")
                print(f"   行 {v.line_number}: {v.evidence}")
                print()
    else:
        constraints = load_default_constraints()
        result = check_constraints(code, constraints, mode=mode)
        print(f"得分：{result.score}/100")
        print(f"通过：{result.passed}")
        print(f"发现问题：{len(result.violations)}")
        print()
        
        if result.violations:
            for i, v in enumerate(result.violations, 1):
                print(f"{i}. [{v.severity.value.upper()}] {v.description}")
                print(f"   行 {v.line_number}: {v.evidence[:80]}...")
                print()
    
    print("=" * 80)
    if result.passed:
        print(f"✅ 审计通过！")
        return True
    else:
        print(f"❌ 审计失败！需要修复 {len(result.violations)} 个问题")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="BMAD-EVO 快速代码审计工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s your_code.py                    # 快速模式审计文件
  %(prog)s --mode strict your_code.py      # 严格模式审计文件
  cat code.py | %(prog)s --stdin           # 从管道读取代码
  %(prog)s --help                          # 显示帮助
  
模式说明:
  fast:        AST only，快速反馈（<50ms/文件）
  strict:      AST + regex，全面检查（<100ms/文件）
  regex_only:  仅正则，向后兼容
        """
    )
    
    parser.add_argument(
        "file",
        nargs="?",
        help="要审计的 Python 文件"
    )
    
    parser.add_argument(
        "--mode",
        choices=["fast", "strict", "regex_only"],
        default="fast",
        help="审计模式（默认：fast）"
    )
    
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="从标准输入读取代码"
    )
    
    parser.add_argument(
        "--exit-code",
        action="store_true",
        help="失败时返回非零退出码（用于 CI/CD）"
    )
    
    args = parser.parse_args()
    
    if args.stdin:
        success = audit_stdin(args.mode)
    elif args.file:
        success = audit_file(args.file, args.mode)
    else:
        parser.print_help()
        return 1
    
    if args.exit_code and not success:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
