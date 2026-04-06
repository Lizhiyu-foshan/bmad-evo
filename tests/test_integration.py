#!/usr/bin/env python3
"""
BMAD-EVO v3.1 集成测试

测试完整的工作流，包括：
- 工作流编排器
- Agent 执行器
- 任务目录管理集成
"""

import sys
import json
import tempfile
import time
from pathlib import Path
from datetime import datetime

# 设置路径 - 使用绝对路径
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root / "lib"))
sys.path.insert(0, str(project_root / "lib" / "v3"))
sys.path.insert(0, str(project_root / "agents"))


def test_task_directory_integration():
    """测试任务目录管理集成"""
    print("\n" + "=" * 70)
    print("集成测试: 任务目录管理")
    print("=" * 70)

    from v3.task_directory_manager import TaskDirectoryManager, OutputType, TaskStatus

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建任务目录
        manager = TaskDirectoryManager(tmpdir, "测试任务")
        manager.create_task_structure(output_type=OutputType.MIXED, task_type="测试")

        print("\n1. 验证目录结构...")
        assert (Path(tmpdir) / "tasks").exists()
        assert (Path(tmpdir) / "tasks" / "requirement.md").exists()
        assert (Path(tmpdir) / "tasks" / "design.md").exists()
        assert (Path(tmpdir) / "tasks" / "assignment.md").exists()
        assert (Path(tmpdir) / "outputs").exists()
        assert (Path(tmpdir) / "outputs" / "reports").exists()
        assert (Path(tmpdir) / "outputs" / "code").exists()
        assert (Path(tmpdir) / "outputs" / "docs").exists()
        assert (Path(tmpdir) / ".bmad" / "versions").exists()
        print("   [OK] 目录结构验证通过")

        print("\n2. 测试版本创建和管理...")
        v1 = manager.create_new_version(
            output_type=OutputType.REPORT,
            changes=["初始版本"],
            status=TaskStatus.IN_PROGRESS,
        )

        # 保存报告
        report = "# 测试报告\n\n内容"
        manager.save_report(v1, report, meta={"test": True})

        # 更新状态
        manager.update_version_status(
            v1, status=TaskStatus.COMPLETED, audit_score=90, iterations=1
        )

        # 验证版本信息
        latest = manager.version_index.get_latest_version()
        assert latest.version == "v1.0"
        assert latest.status == TaskStatus.COMPLETED
        assert latest.audit_score == 90
        print("   [OK] 版本创建和管理测试通过")

        print("\n3. 测试文档更新...")
        manager.update_requirement_document("# 更新的需求", "测试")
        manager.update_design_document("# 更新的设计", "测试")

        req_content = (Path(tmpdir) / "tasks" / "requirement.md").read_text(
            encoding="utf-8"
        )
        assert "更新的需求" in req_content
        print("   [OK] 文档更新测试通过")

    print("\n[OK] 任务目录管理集成测试通过")


def test_model_routing_integration():
    """测试模型路由集成"""
    print("\n" + "=" * 70)
    print("集成测试: 模型路由")
    print("=" * 70)

    from v3.model_router import ModelRouter, AVAILABLE_MODELS

    print("\n1. 测试模型配置...")
    assert len(AVAILABLE_MODELS) >= 7  # 至少有 7 个 GLM 模型
    print(f"   [OK] 模型数量: {len(AVAILABLE_MODELS)}")

    print("\n2. 测试回退链...")
    router = ModelRouter()

    # 测试不同角色的回退链
    test_roles = ["analyst", "developer", "architect", "qa"]
    for role in test_roles:
        chain = router.get_fallback_chain(role, None)
        assert len(chain) >= 3
        assert chain[0] in AVAILABLE_MODELS or chain[0] == "glm-4.7"
        assert "kimi-coding/k2p5" in chain
        print(f"   [OK] {role}: {' → '.join(chain[:3])}...")

    print("\n3. 测试模型能力匹配...")
    glm51 = AVAILABLE_MODELS["glm-5.1"]
    assert "复杂代码" in glm51.strengths
    assert "深度推理" in glm51.strengths

    glm47_flash = AVAILABLE_MODELS["glm-4.7-flash"]
    assert "低延迟" in glm47_flash.strengths
    assert "快速实验" in glm47_flash.strengths

    print("   [OK] 模型能力匹配测试通过")

    print("\n[OK] 模型路由集成测试通过")


def test_context_budget_integration():
    """测试上下文预算集成"""
    print("\n" + "=" * 70)
    print("集成测试: 上下文预算管理")
    print("=" * 70)

    from v3.context_budget import ContextBudgetManager, MODEL_CONTEXT_WINDOWS

    print("\n1. 测试模型上下文窗口配置...")
    assert "glm-5.1" in MODEL_CONTEXT_WINDOWS
    assert "glm-4.7" in MODEL_CONTEXT_WINDOWS
    assert "kimi-coding/k2p5" in MODEL_CONTEXT_WINDOWS
    print(f"   [OK] 模型配置: {len(MODEL_CONTEXT_WINDOWS)} 个")

    print("\n2. 测试预算检查...")
    manager = ContextBudgetManager()

    # 测试正常情况
    result = manager.check_budget(
        model_id="glm-4.7",
        system_prompt="System",
        context_from_previous="Context",
        task_description="Task",
        estimated_output_tokens=1000,
    )
    assert result.sufficient
    print("   [OK] 正常预算检查通过")

    # 测试超限情况 - 使用非常大的上下文使其真正超限
    large_context = "X" * 800000  # 超大上下文 (800K字符)
    result = manager.check_budget(
        model_id="glm-4.7",
        system_prompt="System",
        context_from_previous=large_context,
        task_description="Task",
        estimated_output_tokens=4000,
    )
    assert not result.sufficient
    assert len(result.suggestions) > 0
    print(f"   [OK] 超限预算检查通过: {len(result.suggestions)} 条建议")

    print("\n3. 测试工作流预算...")
    roles = [
        {"id": "role1", "name": "角色1", "description": "描述"},
        {"id": "role2", "name": "角色2", "description": "描述"},
    ]
    routing = {
        "role1": ["glm-4.7"],
        "role2": ["glm-4.7"],
    }

    results = manager.check_workflow_budget(
        roles=roles, model_routing=routing, task_description="测试任务"
    )
    assert len(results) == 2
    print(f"   [OK] 工作流预算检查通过: {len(results)} 个角色")

    print("\n[OK] 上下文预算集成测试通过")


def test_agent_executor_integration():
    """测试 Agent 执行器集成"""
    print("\n" + "=" * 70)
    print("集成测试: Agent 执行器")
    print("=" * 70)

    # 重新设置 sys.path 确保能找到模块
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    sys.path.insert(0, str(project_root / "lib"))
    sys.path.insert(0, str(project_root / "lib" / "v3"))
    sys.path.insert(0, str(project_root / "agents"))

    from agent_executor import AgentExecutor, DEFAULT_AGENTS

    print("\n1. 测试默认 Agent 配置...")
    assert len(DEFAULT_AGENTS) >= 7

    for role_name, config in DEFAULT_AGENTS.items():
        assert config.model.startswith("glm") or config.model == "kimi-coding/k2p5"
        print(f"   [OK] {role_name}: {config.model}")

    print(f"   [OK] 默认 Agent 配置: {len(DEFAULT_AGENTS)} 个")

    print("\n2. 测试模型分配...")
    expected_assignments = {
        "analyst": "glm-4.7",
        "pm": "glm-5.1",
        "architect": "glm-5.1",
        "ux": "glm-4.6v",
        "development": "glm-5.1",
        "qa": "glm-4.7-flash",
        "deployment": "glm-4.7",
    }

    for role_name, expected_model in expected_assignments.items():
        config = DEFAULT_AGENTS[role_name]
        assert config.model == expected_model, (
            f"{role_name} 预期 {expected_model}, 实际 {config.model}"
        )
        print(f"   [OK] {role_name}: {config.model}")

    print("\n3. 测试 Agent 配置加载...")
    with tempfile.TemporaryDirectory() as tmpdir:
        executor = AgentExecutor(tmpdir, mode="local")

        # 测试获取配置
        config = executor.get_agent_config("development")
        assert config.name == "development"
        assert config.model == "glm-5.1"
        print(f"   [OK] 配置加载: {config.model}")

    print("\n[OK] Agent 执行器集成测试通过")


def test_workflow_orchestrator_import():
    """测试工作流编排器导入"""
    print("\n" + "=" * 70)
    print("集成测试: WorkflowOrchestratorV3Final 导入")
    print("=" * 70)

    # 重新设置 sys.path 确保能找到模块
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    sys.path.insert(0, str(project_root / "lib"))
    sys.path.insert(0, str(project_root / "lib" / "v3"))
    sys.path.insert(0, str(project_root / "agents"))

    try:
        from agents.workflow_orchestrator_v3_final import WorkflowOrchestratorV3Final

        print("   [OK] WorkflowOrchestratorV3Final 导入成功")
        print("   [WARN] 跳过完整功能测试（需要 yaml 依赖）")
        return True
    except Exception as e:
        print(f"   [WARN] 导入失败: {e}")
        print("   [WARN] 这是预期的（缺少 yaml 依赖）")
        return False


def test_file_imports():
    """测试所有核心文件导入"""
    print("\n" + "=" * 70)
    print("集成测试: 核心文件导入")
    print("=" * 70)

    imports = {
        "任务目录管理器": "v3.task_directory_manager",
        "上下文预算管理器": "v3.context_budget",
        "模型路由": "v3.model_router",
        "弹性执行器": "v3.resilient_executor",
        "Agent 执行器": "lib.agent_executor",
        "工作流编排器 v3.1": "agents.workflow_orchestrator_v3_final",
    }

    all_passed = True

    for name, module_path in imports.items():
        try:
            __import__(module_path)
            print(f"   [OK] {name} ({module_path})")
        except Exception as e:
            print(f"   [FAIL] {name} ({module_path}): {e}")
            all_passed = False

    return all_passed


def test_consistency():
    """测试配置一致性"""
    print("\n" + "=" * 70)
    print("集成测试: 配置一致性")
    print("=" * 70)

    # 重新设置 sys.path 确保能找到模块
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    sys.path.insert(0, str(project_root / "lib"))
    sys.path.insert(0, str(project_root / "lib" / "v3"))
    sys.path.insert(0, str(project_root / "agents"))

    from v3.model_router import AVAILABLE_MODELS
    from v3.context_budget import MODEL_CONTEXT_WINDOWS
    from agent_executor import DEFAULT_AGENTS

    print("\n1. 检查模型配置一致性...")

    # 检查 AVAILABLE_MODELS 和 MODEL_CONTEXT_WINDOWS 中的模型一致
    router_models = set(AVAILABLE_MODELS.keys())
    budget_models = set(MODEL_CONTEXT_WINDOWS.keys())

    # Budget 应该包含所有 router 模型 + kimi
    for model in router_models:
        assert model in budget_models, f"模型 {model} 在 MODEL_CONTEXT_WINDOWS 中不存在"
        print(f"   [OK] {model}: 一致")

    assert "kimi-coding/k2p5" in budget_models
    print(f"   [OK] kimi-coding/k2p5: 在预算配置中")

    print("\n2. 检查 Agent 模型分配...")

    # 检查所有 Agent 使用的模型都是有效的
    for role_name, config in DEFAULT_AGENTS.items():
        model = config.model
        if model.startswith("glm-"):
            assert model in router_models, (
                f"Agent {role_name} 使用的模型 {model} 不在 AVAILABLE_MODELS 中"
            )
            print(f"   [OK] {role_name}: {model} (有效)")
        elif model == "kimi-coding/k2p5":
            assert model in budget_models
            print(f"   [OK] {role_name}: {model} (回退模型)")

    print("\n[OK] 配置一致性测试通过")


def run_all_integration_tests():
    """运行所有集成测试"""
    print("=" * 70)
    print("BMAD-EVO v3.1 集成测试")
    print("=" * 70)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        ("任务目录管理集成", test_task_directory_integration),
        ("模型路由集成", test_model_routing_integration),
        ("上下文预算集成", test_context_budget_integration),
        # ("Agent 执行器集成", test_agent_executor_integration),
        # ("工作流编排器导入", test_workflow_orchestrator_import),
        ("核心文件导入", test_file_imports),
        # ("配置一致性", test_consistency),
    ]

    passed = 0
    failed = 0
    results = []

    for name, test_func in tests:
        try:
            if test_func() is not False:
                passed += 1
                results.append((name, "[OK] 通过", None))
            else:
                failed += 1
                results.append((name, "[FAIL] 失败", "测试返回 False"))
        except Exception as e:
            failed += 1
            results.append((name, "[FAIL] 失败", str(e)))
            print(f"\n[FAIL] 测试 '{name}' 失败: {e}")
            import traceback

            traceback.print_exc()

    # 输出测试摘要
    print("\n" + "=" * 70)
    print("集成测试摘要")
    print("=" * 70)

    print("\n| 测试名称 | 状态 | 说明 |")
    print("|---------|------|------|")

    for name, status, error in results:
        error_msg = error[:50] if error else ""
        print(f"| {name} | {status} | {error_msg} |")

    print(f"\n总计: {passed + failed} 个测试")
    print(f"通过: {passed} [OK]")
    print(f"失败: {failed} [FAIL]")
    print(f"通过率: {passed / (passed + failed) * 100:.1f}%")

    return failed == 0


if __name__ == "__main__":
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)
