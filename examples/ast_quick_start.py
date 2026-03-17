#!/usr/bin/env python3
"""
BMAD-EVO AST Audit Engine - Quick Start Examples

运行方式:
    python3 examples/ast_quick_start.py
"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from ast_auditor import audit_code, audit_file
from constraint_checker import check_constraints

print("=" * 80)
print("BMAD-EVO AST Audit Engine - Quick Start")
print("=" * 80)
print()

# Example 1: Audit code string
print("📝 示例 1: 审计代码字符串")
print("-" * 80)

problematic_code = '''
import requests

def fetch_data(url):
    # 问题：没有异常处理
    response = requests.get(url)
    return response.json()

def process_data(data):
    # 问题：没有空值检查
    value = data['key']
    return value * 2

# 问题：硬编码密钥
api_key = "sk-1234567890abcdef"
'''

result = audit_code(problematic_code, filename="example.py")
print(f"得分：{result.score}/100")
print(f"分析时间：{result.execution_time_ms:.2f}ms")
print(f"发现问题：{len(result.violations)}")
print()

for i, v in enumerate(result.violations[:3], 1):  # Show first 3
    print(f"{i}. [{v.severity.value.upper()}] {v.rule_name}")
    print(f"   行 {v.line}: {v.message}")
    print(f"   建议：{v.suggestion}")
    print()

print()

# Example 2: Check with constraints
print("📝 示例 2: 使用约束检查（严格模式）")
print("-" * 80)

result2 = check_constraints(problematic_code, mode="strict")
print(f"通过：{result2.passed}")
print(f"得分：{result2.score}/100")
print(f"必须修复：{result2.must_fix}")
print()

# Example 3: Audit self
print("📝 示例 3: 审计 AST 引擎自己")
print("-" * 80)

result3 = audit_file("lib/ast_auditor.py")
print(f"文件：lib/ast_auditor.py")
print(f"得分：{result3.score:.2f}/100")
print(f"分析时间：{result3.execution_time_ms:.2f}ms")
print(f"发现问题：{len(result3.violations)}")
print()

# Check if passing
if result3.score >= 85:
    print("✅ 审计通过！")
else:
    print("❌ 审计未通过")

print()
print("=" * 80)
print("Quick Start 完成!")
print("=" * 80)
print()
print("💡 提示:")
print("  - 开发时使用 mode='fast' (AST only)")
print("  - 发布前使用 mode='strict' (AST + regex)")
print("  - 审计得分 >= 85 且无 HIGH/CRITICAL 问题即为通过")
print()
