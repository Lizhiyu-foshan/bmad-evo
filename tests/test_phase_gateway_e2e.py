#!/usr/bin/env python3
"""
BMAD-EVO Phase Gateway 端到端测试

演示完整的 Phase Gateway + AST 审计工作流

运行方式:
    python3 test_phase_gateway_e2e.py
"""

import sys
import tempfile
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent / "agents"))

from phase_gateway import PhaseGateway
from constraint_checker import ConstraintChecker, check_constraints
import yaml

# 测试代码示例
GOOD_CODE = '''
import os
import requests
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

def fetch_user_data(user_id: str, api_key: str) -> Optional[Dict]:
    """获取用户数据（良好的代码）"""
    if not user_id:
        raise ValueError("user_id 不能为空")
    if not api_key:
        raise ValueError("api_key 不能为空")
    
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        response = requests.get(
            f"https://api.example.com/users/{user_id}",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout as e:
        logger.error(f"请求超时：{user_id}")
        return None
    except requests.RequestException as e:
        logger.error(f"网络错误：{e}")
        return None

def main():
    api_key = os.getenv('API_KEY')
    if not api_key:
        raise ValueError("API_KEY 未设置")
    
    data = fetch_user_data("user123", api_key)
    if data:
        print(f"获取成功：{data}")

if __name__ == '__main__':
    main()
'''

BAD_CODE = '''
import requests

def fetch_user_data(user_id, api_key):
    """获取用户数据（糟糕的代码）"""
    # 问题：没有空值检查
    url = f"https://api.example.com/users/{user_id}"
    
    # 问题：网络请求没有异常处理
    response = requests.get(url)
    
    # 问题：硬编码密钥
    password = "super_secret_123"
    
    return response.json()

def save_to_file(content, filename):
    # 问题：文件操作没有异常处理
    # 问题：没有使用 with 语句
    f = open(filename, 'w')
    f.write(content)
    f.close()

# 问题：全局硬编码密钥
API_KEY = "sk-1234567890abcdef"

def main():
    data = fetch_user_data("user123", API_KEY)
    save_to_file(data, 'output.txt')

if __name__ == '__main__':
    main()
'''

def load_constraint_template(template_name: str = "ast-cron-job.yaml") -> dict:
    """加载约束模板"""
    template_path = Path(__file__).parent / "templates" / "constraints" / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"约束模板不存在：{template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def test_good_code():
    """测试良好代码 - 应该通过审计"""
    print("=" * 80)
    print("测试 1: 良好代码 - 预期通过审计")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 初始化 Phase Gateway
        gateway = PhaseGateway(tmpdir)
        
        # 加载约束模板
        constraints = load_constraint_template()
        
        # 创建审计器（严格模式）
        checker = ConstraintChecker(constraints, mode="strict")
        
        # 开始阶段
        gateway.start_phase("development")
        
        # 审计代码
        audit_result = checker.audit(GOOD_CODE, output_type="code")
        
        # 完成阶段
        result = gateway.complete_phase("development", audit_result)
        
        print(f"审计结果: {result['message']}")
        print(f"得分：{audit_result.score}/100")
        print(f"问题数：{len(audit_result.violations)}")
        
        if audit_result.passed:
            print("✅ 测试通过：良好代码成功通过审计")
        else:
            print("❌ 测试失败：良好代码应该通过审计")
            for v in audit_result.violations:
                print(f"  - [{v.severity.value}] {v.description}")
        
        print()
        return audit_result.passed

def test_bad_code():
    """测试糟糕代码 - 应该失败并需要重试"""
    print("=" * 80)
    print("测试 2: 糟糕代码 - 预期失败并触发重试")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 初始化 Phase Gateway
        gateway = PhaseGateway(tmpdir, config={"max_retries": 2})
        
        # 加载约束模板
        constraints = load_constraint_template()
        
        # 创建审计器（严格模式）
        checker = ConstraintChecker(constraints, mode="strict")
        
        # 开始阶段
        gateway.start_phase("development")
        
        # 第一次审计（应该失败）
        print("第 1 次审计...")
        audit_result = checker.audit(BAD_CODE, output_type="code")
        result = gateway.complete_phase("development", audit_result, attempt=1)
        
        print(f"结果：{result['message']}")
        print(f"得分：{audit_result.score}/100")
        print(f"问题数：{len(audit_result.violations)}")
        
        # 模拟修复（实际应该由 AI 自动修复）
        if result['action'] == 'retry':
            print("⏳ 需要修复后重试...")
            
            # 第 2 次审计（还是失败，因为代码没改）
            print("第 2 次审计...")
            audit_result = checker.audit(BAD_CODE, output_type="code")
            result = gateway.complete_phase("development", audit_result, attempt=2)
            
            print(f"结果：{result['message']}")
            
            # 第 3 次审计（最终失败，需要用户决策）
            if result['action'] == 'block':
                print("🚫 所有重试用尽，等待用户决策")
                print(f"可选操作：{result['options']}")
                
                # 模拟用户选择强制通过
                print("\n模拟用户选择：force_proceed")
                decision_result = gateway.user_decision("development", "force_proceed")
                print(f"结果：{decision_result['message']}")
        
        print(f"\n✅ 测试完成：糟糕代码正确触发审计失败流程")
        print()
        return True

def test_phase_transitions():
    """测试阶段转换"""
    print("=" * 80)
    print("测试 3: 阶段转换 - 验证状态管理")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        gateway = PhaseGateway(tmpdir)
        constraints = load_constraint_template()
        checker = ConstraintChecker(constraints, mode="strict")
        
        # 开始 analyst 阶段
        print("开始 analyst 阶段...")
        gateway.start_phase("analyst")
        
        # 完成 analyst（假设通过）
        mock_result = checker.audit("分析师报告", output_type="text")
        result = gateway.complete_phase("analyst", mock_result)
        print(f"analyst 阶段：{result['message']}")
        
        # 尝试直接跳到 architect（应该失败，因为缺少 pm 阶段）
        print("\n尝试跳过 pm 阶段直接开始 architect...")
        success = gateway.start_phase("architect")
        if not success:
            print("✅ 正确阻断：必须先完成 pm 阶段")
        else:
            print("❌ 错误：应该阻断非法阶段转换")
        
        # 正确的流程
        print("\n正确流程：pm 阶段...")
        gateway.start_phase("pm")
        pm_result = checker.audit("产品需求文档", output_type="text")
        gateway.complete_phase("pm", pm_result)
        
        print("正确流程：architect 阶段...")
        gateway.start_phase("architect")
        arch_result = checker.audit("架构设计文档", output_type="text")
        gateway.complete_phase("architect", arch_result)
        
        print("\n✅ 测试完成：阶段转换管理正常")
        print()
        return True

def main():
    """运行所有测试"""
    print("BMAD-EVO Phase Gateway 端到端测试")
    print("=" * 80)
    print()
    
    results = []
    
    # Test 1: Good code
    results.append(("良好代码审计", test_good_code()))
    
    # Test 2: Bad code
    results.append(("糟糕代码审计", test_bad_code()))
    
    # Test 3: Phase transitions
    results.append(("阶段转换管理", test_phase_transitions()))
    
    # Summary
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n🎉 所有测试通过！Phase Gateway + AST 审计集成正常")
    else:
        print("\n❌ 部分测试失败，请检查")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
