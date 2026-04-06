#!/usr/bin/env python3
"""
BMAD-EVO v3.1 单元测试

测试各个核心模块的功能
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent.parent / "lib" / "v3"))


# 测试任务目录管理器
def test_task_directory_manager():
    """测试任务目录管理器"""
    print("\n" + "=" * 70)
    print("测试: TaskDirectoryManager")
    print("=" * 70)

    from v3.task_directory_manager import (
        TaskDirectoryManager,
        OutputType,
        TaskStatus,
        VersionInfo,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        task_desc = "开发用户认证系统"
        manager = TaskDirectoryManager(tmpdir, task_desc)

        # 测试创建目录结构
        print("\n1. 创建目录结构...")
        structure = manager.create_task_structure(
            output_type=OutputType.CODE, task_type="软件开发"
        )
        assert "project_path" in structure
        assert "tasks_dir" in structure
        assert "outputs_dir" in structure
        print("   [OK] 目录结构创建成功")

        # 测试创建版本
        print("\n2. 创建版本 v1.0...")
        v1 = manager.create_new_version(
            output_type=OutputType.CODE,
            changes=["初始版本"],
            status=TaskStatus.IN_PROGRESS,
        )
        assert v1 == "v1.0"
        print(f"   [OK] 版本 {v1} 创建成功")

        # 测试保存代码
        print("\n3. 保存代码...")
        code = {
            "auth.py": "def login():\n    pass",
            "utils.py": "def hash():\n    pass",
        }
        manager.save_code(v1, code, meta={"author": "test"})
        assert (Path(tmpdir) / "outputs" / "code" / "v1.0" / "src" / "auth.py").exists()
        print("   [OK] 代码保存成功")

        # 测试保存报告
        print("\n4. 保存报告...")
        report = "# Test Report\n\nContent"
        manager.save_report(v1, report, meta={"total": 1})
        assert (Path(tmpdir) / "outputs" / "reports" / "v1.0" / "report.md").exists()
        print("   [OK] 报告保存成功")

        # 测试版本状态更新
        print("\n5. 更新版本状态...")
        manager.update_version_status(
            v1,
            status=TaskStatus.COMPLETED,
            audit_score=95,
            iterations=2,
            user_feedback=["需要改进"],
        )
        latest = manager.version_index.get_latest_version()
        assert latest.status == TaskStatus.COMPLETED
        assert latest.audit_score == 95
        assert latest.iterations == 2
        print("   [OK] 版本状态更新成功")

        # 测试版本索引
        print("\n6. 获取版本列表...")
        versions = manager.get_version_list()
        assert len(versions) == 1
        assert versions[0]["version"] == "v1.0"
        print(f"   [OK] 版本列表获取成功: {len(versions)} 个版本")

        # 测试更新文档
        print("\n7. 更新任务文档...")
        manager.update_requirement_document("# New Requirement\n\nContent", "Test")
        assert (Path(tmpdir) / "tasks" / "requirement.md").exists()
        print("   [OK] 任务文档更新成功")

    print("\n[OK] TaskDirectoryManager 所有测试通过")


# 测试上下文预算管理器
def test_context_budget_manager():
    """测试上下文预算管理器"""
    print("\n" + "=" * 70)
    print("测试: ContextBudgetManager")
    print("=" * 70)

    from v3.context_budget import (
        ContextBudgetManager,
        MODEL_CONTEXT_WINDOWS,
        estimate_tokens,
    )

    # 测试 token 估算
    print("\n1. Token 估算...")
    tokens = estimate_tokens("这是一个测试字符串")
    assert tokens > 0
    print(f"   [OK] Token 估算: '这是一个测试字符串' -> {tokens} tokens")

    # 测试预算检查
    print("\n2. 预算检查...")
    manager = ContextBudgetManager()

    # 足够的预算
    result = manager.check_budget(
        model_id="glm-4.7",
        system_prompt="System prompt",
        context_from_previous="",
        task_description="Simple task",
        estimated_output_tokens=4000,
    )
    assert result.sufficient
    print("   [OK] 预算充足检查通过")

    # 不足的预算 - 使用非常大的上下文使其真正超限
    # GLM-4.7: 输入200K, 预留20% -> 可用160K (约480K字符)
    # 800K个字符 ≈ 267K tokens，这会明显超限
    result = manager.check_budget(
        model_id="glm-4.7",
        system_prompt="System prompt with some additional text to increase token count significantly and make it exceed the available budget",
        context_from_previous="X" * 800000,  # 超大上下文 (800K字符)
        task_description="Complex task with additional requirements and detailed specifications that will add more tokens to the total",
        estimated_output_tokens=4000,
    )
    assert not result.sufficient
    assert len(result.suggestions) > 0
    print(f"   [OK] 预算不足检查通过: {len(result.suggestions)} 条建议")

    # 测试工作流预算检查
    print("\n3. 工作流预算检查...")
    roles = [
        {"id": "analyst", "name": "分析师", "description": "需求分析"},
        {"id": "developer", "name": "开发者", "description": "代码开发"},
    ]
    model_routing = {
        "analyst": ["glm-4.7"],
        "developer": ["glm-4.7"],
    }

    results = manager.check_workflow_budget(
        roles=roles, model_routing=model_routing, task_description="Test task"
    )
    assert len(results) == 2
    print(f"   [OK] 工作流预算检查通过: {len(results)} 个角色")

    # 测试预算报告
    print("\n4. 生成预算报告...")
    report = manager.format_budget_report(results)
    assert "Context Budget Report" in report
    assert "analyst" in report.lower() or "分析师" in report
    print("   [OK] 预算报告生成成功")

    print("\n[OK] ContextBudgetManager 所有测试通过")


# 测试模型路由
def test_model_router():
    """测试模型路由"""
    print("\n" + "=" * 70)
    print("测试: ModelRouter")
    print("=" * 70)

    from v3.model_router import (
        ModelRouter,
        AVAILABLE_MODELS,
        ModelCapability,
    )

    # 测试模型配置
    print("\n1. 模型配置...")
    assert "glm-5.1" in AVAILABLE_MODELS
    assert "glm-4.7" in AVAILABLE_MODELS
    assert "glm-4.7-flash" in AVAILABLE_MODELS
    print(f"   [OK] 可用模型: {len(AVAILABLE_MODELS)} 个")

    # 测试模型能力
    print("\n2. 模型能力...")
    glm47 = AVAILABLE_MODELS["glm-4.7"]
    assert ModelCapability.CODE_GENERATION in glm47.capabilities
    assert ModelCapability.CODE_REVIEW in glm47.capabilities
    print(f"   [OK] GLM-4.7 能力: {len(glm47.capabilities)} 个")

    # 测试回退链
    print("\n3. 回退链...")
    router = ModelRouter()
    chain = router.get_fallback_chain("test_role", None)
    assert "glm-4.7" in chain
    assert "glm-5.1" in chain
    assert "kimi-coding/k2p5" in chain
    print(f"   [OK] 回退链: {' -> '.join(chain)}")

    print("\n[OK] ModelRouter 所有测试通过")


# 测试角色生成器
def test_role_generator():
    """测试角色生成器（仅测试导入和基本结构）"""
    print("\n" + "=" * 70)
    print("测试: DynamicRoleGenerator (导入测试)")
    print("=" * 70)

    try:
        from v3.role_generator import (
            DynamicRoleGenerator,
            RoleDefinition,
            RoleFlow,
        )

        print("\n   [OK] DynamicRoleGenerator 导入成功")
        print("   [WARN]  跳过完整功能测试（需要模型调用）")

    except Exception as e:
        print(f"   [FAIL] 导入失败: {e}")
        raise

    print("\n[OK] DynamicRoleGenerator 导入测试通过")


# 测试任务分析器
def test_task_analyzer():
    """测试任务分析器（仅测试导入和基本结构）"""
    print("\n" + "=" * 70)
    print("测试: TaskAnalyzer (导入测试)")
    print("=" * 70)

    try:
        from v3.task_analyzer import (
            TaskAnalyzer,
            TaskAnalysis,
            analyze_task,
        )

        print("\n   [OK] TaskAnalyzer 导入成功")
        print("   [WARN]  跳过完整功能测试（需要模型调用）")

    except Exception as e:
        print(f"   [FAIL] 导入失败: {e}")
        raise

    print("\n[OK] TaskAnalyzer 导入测试通过")


# 运行所有测试
def run_all_tests():
    """运行所有单元测试"""
    print("=" * 70)
    print("BMAD-EVO v3.1 单元测试")
    print("=" * 70)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        ("任务目录管理器", test_task_directory_manager),
        ("上下文预算管理器", test_context_budget_manager),
        ("模型路由", test_model_router),
        ("角色生成器", test_role_generator),
        ("任务分析器", test_task_analyzer),
    ]

    passed = 0
    failed = 0

    results = []

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
            results.append((name, "[OK] 通过", None))
        except Exception as e:
            failed += 1
            results.append((name, "[FAIL] 失败", str(e)))
            print(f"\n[FAIL] 测试 '{name}' 失败: {e}")
            import traceback

            traceback.print_exc()

    # 输出测试摘要
    print("\n" + "=" * 70)
    print("测试摘要")
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
    success = run_all_tests()
    sys.exit(0 if success else 1)
