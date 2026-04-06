#!/usr/bin/env python3
"""
BMAD-EVO v3.0 完整集成测试

测试完整的流程：
1. 项目生成
2. 定义全局约束
3. 任务类型检测
4. 复杂度评估
5. 角色流程生成（包含模型选择）
6. 阶段执行循环（网关+执行+审计+重试/决策）
"""

import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib" / "v3"))
sys.path.insert(0, str(Path(__file__).parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent / "agents"))

from workflow_orchestrator_v3_final import WorkflowOrchestratorV3Final


def test_full_workflow_mock():
    """测试完整流程（模拟模式）"""
    print("\n🧪 Test: 完整工作流集成测试（模拟）")
    print("="*70)
    
    # 创建临时项目目录
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        
        print(f"\n📁 项目路径: {project_path}")
        
        # 创建编排器
        orchestrator = WorkflowOrchestratorV3Final(
            project_path=str(project_path),
            interactive=False,  # 非交互模式
            config={'timeout': 30, 'max_retries': 2, 'pass_threshold': 85}
        )
        
        print("✅ 编排器创建成功")
        
        # 执行任务
        task = "创建一个Python脚本，实现斐波那契数列计算"
        print(f"\n📝 任务: {task}")
        
        result = orchestrator.execute_full_workflow(task)
        
        # 验证结果
        print("\n📊 验证结果:")
        
        # 1. 验证项目生成
        assert project_path.exists(), "项目目录未创建"
        assert (project_path / ".bmad").exists(), ".bmad目录未创建"
        print("   ✅ 项目生成成功")
        
        # 2. 验证全局约束
        constraint_file = project_path / ".bmad" / "constraints" / "global.json"
        assert constraint_file.exists(), "全局约束文件未创建"
        print("   ✅ 全局约束定义成功")
        
        # 3. 验证任务分析
        assert orchestrator.task_analysis is not None, "任务分析未执行"
        assert orchestrator.task_analysis.task_type, "任务类型未检测"
        print(f"   ✅ 任务类型检测: {orchestrator.task_analysis.task_type}")
        
        # 4. 验证复杂度评估
        assert orchestrator.task_analysis.complexity_score > 0, "复杂度未评估"
        print(f"   ✅ 复杂度评估: {orchestrator.task_analysis.complexity_score}/10")
        
        # 5. 验证角色生成
        assert orchestrator.role_flow is not None, "角色流程未生成"
        assert orchestrator.role_flow.total_roles > 0, "角色数量错误"
        print(f"   ✅ 角色生成: {orchestrator.role_flow.total_roles} 个角色")
        
        # 6. 验证模型选择
        assert orchestrator.model_routing is not None, "模型路由未执行"
        assert len(orchestrator.model_routing.mappings) > 0, "模型映射为空"
        print(f"   ✅ 模型选择: {len(orchestrator.model_routing.mappings)} 个映射")
        
        # 7. 验证阶段执行
        assert len(orchestrator.phase_results) > 0, "阶段未执行"
        print(f"   ✅ 阶段执行: {len(orchestrator.phase_results)} 个阶段")
        
        # 8. 验证最终结果
        assert 'success' in result, "结果缺少success字段"
        print(f"   ✅ 最终结果: {'成功' if result['success'] else '失败'}")
        
        print("\n🎉 完整集成测试通过！")
        return True


def test_entry_point():
    """测试入口文件可用性"""
    print("\n🧪 Test: 入口文件验证")
    print("="*70)
    
    # 检查关键文件存在
    skill_dir = Path(__file__).parent
    
    files_to_check = [
        ("bmad-evo", "CLI入口"),
        ("agents/workflow_orchestrator_v3_final.py", "v3编排器"),
        ("lib/v3/task_analyzer.py", "任务分析器"),
        ("lib/v3/role_generator.py", "角色生成器"),
        ("lib/v3/model_router.py", "模型路由器"),
        ("lib/v3/resilient_executor.py", "弹性执行器"),
    ]
    
    all_exist = True
    for file_path, desc in files_to_check:
        full_path = skill_dir / file_path
        if full_path.exists():
            print(f"   ✅ {desc}: {file_path}")
        else:
            print(f"   ❌ {desc}: {file_path} 不存在")
            all_exist = False
    
    return all_exist


def test_v3_module_imports():
    """测试v3模块导入"""
    print("\n🧪 Test: v3模块导入验证")
    print("="*70)
    
    try:
        from lib.v3 import BMADEVO3, TaskAnalyzer, DynamicRoleGenerator, ModelRouter
        print("   ✅ lib.v3 模块导入成功")
        
        from workflow_orchestrator_v3_final import WorkflowOrchestratorV3Final
        print("   ✅ WorkflowOrchestratorV3Final 导入成功")
        
        return True
    except Exception as e:
        print(f"   ❌ 导入失败: {e}")
        return False


def test_flow_order():
    """测试流程顺序"""
    print("\n🧪 Test: 流程顺序验证")
    print("="*70)
    
    import inspect
    from workflow_orchestrator_v3_final import WorkflowOrchestratorV3Final
    
    source = inspect.getsource(WorkflowOrchestratorV3Final.execute_full_workflow)
    
    # 验证正确的执行顺序
    steps = [
        ("_generate_project", "项目生成"),
        ("_define_global_constraints", "定义全局约束"),
        ("task_analyzer.analyze", "任务类型检测"),
        ("role_generator.generate", "角色流程生成"),
        ("model_router.route", "模型选择"),
    ]
    
    prev_idx = -1
    for keyword, desc in steps:
        idx = source.find(keyword)
        if idx > prev_idx:
            print(f"   ✅ 顺序正确: {desc}")
            prev_idx = idx
        else:
            print(f"   ❌ 顺序错误: {desc}")
            return False
    
    return True


def test_cli_help():
    """测试CLI帮助信息"""
    print("\n🧪 Test: CLI帮助信息")
    print("="*70)
    
    import subprocess
    result = subprocess.run(
        ["./bmad-evo", "help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent
    )
    
    if result.returncode == 0 and "BMAD-EVO" in result.stdout:
        print("   ✅ CLI帮助正常")
        return True
    else:
        print("   ❌ CLI帮助异常")
        print(f"   输出: {result.stdout[:200]}")
        return False


def run_all_tests():
    """运行所有测试"""
    print("="*70)
    print("🚀 BMAD-EVO v3.0 完整集成测试套件")
    print("="*70)
    
    tests = [
        ("入口文件验证", test_entry_point),
        ("v3模块导入", test_v3_module_imports),
        ("流程顺序验证", test_flow_order),
        ("CLI帮助信息", test_cli_help),
        ("完整工作流集成", test_full_workflow_mock),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
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
        print("\n🎉 所有集成测试通过！v3.0 系统可正常使用。")
    else:
        print(f"\n⚠️  {failed} 个测试失败，请检查错误信息。")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
