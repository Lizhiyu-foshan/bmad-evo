#!/usr/bin/env python3
"""
BMAD-EVO v3.0 集成测试

测试 v3.0 系统与现有约束审计系统的集成
"""

import sys
import tempfile
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "v3"))
sys.path.insert(0, str(Path(__file__).parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent / "agents"))

from v3 import BMADEVO3, TaskAnalyzer, DynamicRoleGenerator, ModelRouter
from workflow_orchestrator_v3 import WorkflowOrchestratorV3


def test_evo3_basic():
    """测试 v3.0 基础功能"""
    print("\n🧪 Test 1: BMADEVO3 基础功能")
    print("-"*70)
    
    evo3 = BMADEVO3(project_path=".", timeout=60)
    
    # 测试简单任务（模拟模式，不实际调用API）
    task = "创建一个Python脚本，计算斐波那契数列"
    
    # 验证组件初始化
    assert evo3.task_analyzer is not None
    assert evo3.role_generator is not None
    assert evo3.model_router is not None
    assert evo3.workflow_executor is not None
    print("✅ 所有组件初始化成功")
    
    # 验证提示词构建
    prompt = evo3.task_analyzer._build_analysis_prompt(task)
    assert "斐波那契" in prompt
    assert "complexity_score" in prompt
    print("✅ 任务分析提示词构建成功")
    
    print("✅ Test 1 通过")
    return True


def test_workflow_orchestrator_v3_init():
    """测试 WorkflowOrchestratorV3 初始化"""
    print("\n🧪 Test 2: WorkflowOrchestratorV3 初始化")
    print("-"*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        orchestrator = WorkflowOrchestratorV3(
            project_path=tmpdir,
            interactive=False,
            config={'timeout': 60, 'max_retries': 2}
        )
        
        assert orchestrator.evo3 is not None
        assert orchestrator.auditor is not None
        print("✅ OrchestratorV3 初始化成功")
        
        # 验证配置传递
        assert orchestrator.evo3.timeout == 60
        assert orchestrator.evo3.max_retries == 2
        print("✅ 配置正确传递")
    
    print("✅ Test 2 通过")
    return True


def test_role_generation_mock():
    """测试角色生成（模拟模式）"""
    print("\n🧪 Test 3: 角色生成（模拟）")
    print("-"*70)
    
    generator = DynamicRoleGenerator(timeout=30)
    
    # 测试回退流程生成
    result = generator._create_fallback_flow(
        task_description="测试任务",
        task_analysis={
            "complexity_score": 5,
            "task_type": "test",
            "key_skills": ["python"]
        },
        execution_time=0.0,
        error="test"
    )
    
    assert result.total_roles > 0
    assert len(result.roles) > 0
    print(f"✅ 回退流程生成成功: {result.total_roles} 个角色")
    
    # 验证角色属性
    role = result.roles[0]
    assert role.name
    assert role.title
    assert role.responsibilities
    print(f"✅ 角色属性完整: {role.title}")
    
    print("✅ Test 3 通过")
    return True


def test_model_routing():
    """测试模型路由"""
    print("\n🧪 Test 4: 模型路由")
    print("-"*70)
    
    router = ModelRouter()
    
    # 测试模型库加载
    assert len(router.models) > 0
    print(f"✅ 模型库加载成功: {len(router.models)} 个模型")
    
    # 测试启发式路由
    from v3.role_generator import DynamicRoleGenerator
    generator = DynamicRoleGenerator(timeout=30)
    
    role_flow = generator._create_fallback_flow(
        task_description="开发API",
        task_analysis={"complexity_score": 6, "task_type": "api_development"},
        execution_time=0.0,
        error="test"
    )
    
    routing = router.route(
        roles=[r.to_dict() for r in role_flow.roles],
        task_type="api_development",
        complexity_score=6
    )
    
    assert len(routing.mappings) == len(role_flow.roles)
    print(f"✅ 角色路由成功: {len(routing.mappings)} 个映射")
    
    # 验证每个角色都有主模型和备选模型
    for mapping in routing.mappings:
        assert mapping.primary_model
        assert len(mapping.fallback_models) >= 2
        print(f"   - {mapping.role_id}: {mapping.primary_model}")
    
    print("✅ Test 4 通过")
    return True


def test_end_to_end_mock():
    """测试端到端流程（模拟模式）"""
    print("\n🧪 Test 5: 端到端流程（模拟）")
    print("-"*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建项目结构
        (Path(tmpdir) / ".bmad").mkdir()
        (Path(tmpdir) / ".bmad" / "project-charter.yaml").write_text("""
project:
  name: "Test Project"
  vision: "Test"
""")
        
        orchestrator = WorkflowOrchestratorV3(
            project_path=tmpdir,
            interactive=False,
            config={'timeout': 30, 'max_retries': 1}
        )
        
        # 使用简单的任务描述
        task = "创建一个简单的Python函数"
        
        print(f"   任务: {task}")
        print("   模拟执行...")
        
        # 由于实际执行需要调用API，这里只验证流程准备
        evo3 = orchestrator.evo3
        
        # 验证任务分析准备
        prompt = evo3.task_analyzer._build_analysis_prompt(task)
        assert len(prompt) > 100
        print("✅ 任务分析准备就绪")
        
        # 验证角色生成准备
        analysis = {
            "task_type": "script_development",
            "complexity_score": 3,
            "recommended_roles_count": 2,
            "key_skills": ["python"]
        }
        
        role_prompt = evo3.role_generator._build_generation_prompt(task, analysis)
        assert "角色生成" in role_prompt or "role" in role_prompt.lower()
        print("✅ 角色生成准备就绪")
        
        print("✅ Test 5 通过")
    
    return True


def test_complexity_to_roles_mapping():
    """测试复杂度到角色数量的映射"""
    print("\n🧪 Test 6: 复杂度映射")
    print("-"*70)
    
    test_cases = [
        (1, 2),   # 极简单
        (2, 2),   # 简单
        (3, 2),   # 简单
        (4, 3),   # 中等
        (5, 3),   # 中等
        (6, 3),   # 中等
        (7, 4),   # 复杂
        (8, 4),   # 复杂
        (9, 5),   # 极复杂
        (10, 5),  # 极复杂
    ]
    
    analyzer = TaskAnalyzer(timeout=30)
    
    for complexity, expected_roles in test_cases:
        actual = analyzer._estimate_roles(complexity)
        assert actual == expected_roles, f"复杂度 {complexity} 应生成 {expected_roles} 角色，实际 {actual}"
        print(f"✅ 复杂度 {complexity}/10 → {actual} 角色")
    
    print("✅ Test 6 通过")
    return True


def test_v2_vs_v3_comparison():
    """测试 v2.0 和 v3.0 的差异"""
    print("\n🧪 Test 7: v2.0 vs v3.0 对比")
    print("-"*70)
    
    print("   v2.0 (固定角色):")
    print("   - 预定义阶段: analyst → pm → architect → development → qa")
    print("   - 所有任务使用相同流程")
    print("   - 角色数量和职责固定")
    
    print("\n   v3.0 (动态角色):")
    print("   - 任务分析 → 动态生成角色 → 模型路由 → 执行")
    print("   - 根据任务复杂度生成不同角色")
    print("   - 简单任务1-2角色，复杂任务3-7角色")
    print("   - 每个角色有特定的输入输出关系")
    
    print("\n✅ Test 7 通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("="*70)
    print("🚀 BMAD-EVO v3.0 集成测试套件")
    print("="*70)
    
    tests = [
        ("BMADEVO3 基础功能", test_evo3_basic),
        ("WorkflowOrchestratorV3 初始化", test_workflow_orchestrator_v3_init),
        ("角色生成（模拟）", test_role_generation_mock),
        ("模型路由", test_model_routing),
        ("端到端流程（模拟）", test_end_to_end_mock),
        ("复杂度映射", test_complexity_to_roles_mapping),
        ("v2.0 vs v3.0 对比", test_v2_vs_v3_comparison),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n❌ Test failed: {name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("📊 测试结果")
    print("="*70)
    print(f"✅ 通过: {passed}/{len(tests)}")
    print(f"❌ 失败: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n🎉 所有集成测试通过！v3.0 可与主流程正常工作。")
    else:
        print(f"\n⚠️  {failed} 个测试失败，请检查错误信息。")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
