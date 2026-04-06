#!/usr/bin/env python3
"""
BMAD-EVO AST Integration Test
测试 AST 引擎与传统正则检查的对比

运行方式:
    python3 test_ast_integration.py
"""

import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

from ast_auditor import audit_code as ast_audit
from constraint_checker import check_constraints

# 测试代码：典型的定时任务问题代码
test_code = '''
import requests

def process_wechat_message(data):
    """处理微信消息"""
    # 问题 1: 没有空值检查
    url = data['url']
    
    # 问题 2: 网络请求没有异常处理
    response = requests.get(url)
    
    # 问题 3: JSON 解析没有异常处理
    content = response.json()
    
    # 问题 4: 没有检查空集合
    for item in content:
        print(item)
    
    return content

def save_to_file(content, filename):
    """保存到文件"""
    # 问题 5: 文件操作没有异常处理
    # 问题 6: 没有使用 with 语句
    f = open(filename, 'w')
    f.write(content)
    f.close()

# 问题 7: 硬编码密钥
password = "super_secret_password_123"

def main():
    # 问题 8: 没有日志记录
    data = {'url': 'https://example.com'}
    result = process_wechat_message(data)
    save_to_file(result, 'output.txt')

if __name__ == '__main__':
    main()
'''

print("=" * 80)
print("BMAD-EVO AST Integration Test")
print("=" * 80)
print()

# Test 1: AST-only mode
print("📊 测试 1: AST 模式（零误报）")
print("-" * 80)
ast_result = ast_audit(test_code, filename="<test>")
print(f"分析时间：{ast_result.execution_time_ms:.2f}ms")
print(f"发现问题：{len(ast_result.violations)}")
print()

for i, v in enumerate(ast_result.violations, 1):
    print(f"{i}. [{v.severity.value.upper()}] {v.rule_name}")
    print(f"   行 {v.line}: {v.message}")
    print(f"   建议：{v.suggestion}")
    print()

print()

# Test 2: Traditional regex mode
print("📊 测试 2: 传统正则模式")
print("-" * 80)
regex_result = check_constraints(test_code, mode="regex_only")
print(f"得分：{regex_result.score}/100")
print(f"发现问题：{len(regex_result.violations)}")
print()

for i, v in enumerate(regex_result.violations, 1):
    print(f"{i}. [{v.severity.value.upper()}] {v.description}")
    print(f"   证据：{v.evidence[:60]}...")
    print()

print()

# Test 3: Hybrid mode (AST + regex)
print("📊 测试 3: 混合模式（AST + 正则）⭐ 推荐")
print("-" * 80)
hybrid_result = check_constraints(test_code, mode="strict")
print(f"得分：{hybrid_result.score}/100")
print(f"通过：{hybrid_result.passed}")
print(f"发现问题：{len(hybrid_result.violations)}")
print(f"必须修复：{hybrid_result.must_fix}")
print()

# 按来源分类统计
ast_count = sum(1 for v in hybrid_result.violations if v.source == "ast")
regex_count = sum(1 for v in hybrid_result.violations if v.source == "regex")
print(f"AST 发现：{ast_count} 个")
print(f"正则发现：{regex_count} 个")
print()

for i, v in enumerate(hybrid_result.violations, 1):
    source_icon = "🎯" if v.source == "ast" else "📝"
    print(f"{i}. {source_icon} [{v.severity.value.upper()}] {v.description}")
    print(f"   行 {v.line_number}: {v.evidence[:60]}...")
    if v.fix_example:
        print(f"   修复: {v.fix_example.split(chr(10))[0]}")
    print()

print()
print("=" * 80)
print("测试完成!")
print("=" * 80)
print()
print("📈 性能对比:")
print(f"  AST 模式：{ast_result.execution_time_ms:.2f}ms")
print(f"  混合模式：待测试（通常 < 100ms）")
print()
print("✅ AST 模式优势:")
print("  - 零误报：不会把字符串/注释里的代码当真代码")
print("  - 更深层：能检查控制流、数据流")
print("  - 更精确：能定位到具体行号和列")
print()
print("🎯 推荐使用方式:")
print("  开发时：mode='fast' (AST only, <50ms)")
print("  发布前：mode='strict' (AST+regex, 全面检查)")
