# BMAD-EVO v3.1 代码审计报告

**审计时间**: 2026-04-06 22:15:32
**项目路径**: .
**审计文件数**: 46
**发现问题数**: 112

---

## 问题统计

| 严重级别 | 数量 |
|---------|------|
| 🔴 CRITICAL | 0 |
| 🟠 HIGH | 25 |
| 🟡 MEDIUM | 66 |
| 🟢 LOW | 13 |
| ℹ️ INFO | 8 |

---

## 详细问题


### agents\constraint_auditor.py

- 🟡 **MEDIUM** (行 182): 函数 'main' 较长 (87 行)
  💡 考虑是否可以简化逻辑

### agents\decision_interface.py

- 🟡 **MEDIUM** (行 173): 函数 '_get_user_choice' 较长 (65 行)
  💡 考虑是否可以简化逻辑

### agents\phase_gateway.py

- 🟡 **MEDIUM** (行 181): 函数 'complete_phase' 较长 (94 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 276): 函数 'user_decision' 较长 (73 行)
  💡 考虑是否可以简化逻辑

### agents\test_repairs.py

- 🟢 **LOW** (行 0): 重复的导入: phase_gateway.PhaseGateway
- 🟢 **LOW** (行 0): 重复的导入: phase_gateway.PhaseGateway
- 🟢 **LOW** (行 0): 重复的导入: decision_interface.DecisionInterface
- 🟢 **LOW** (行 0): 重复的导入: shutil
- 🟢 **LOW** (行 0): 重复的导入: traceback
- 🟡 **MEDIUM** (行 107): 函数 'test_decision_interface_non_interactive' 较长 (59 行)
  💡 考虑是否可以简化逻辑

### agents\workflow_orchestrator.py

- 🟡 **MEDIUM** (行 146): 函数 '_audit_with_retry' 较长 (55 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 344): 函数 'main' 较长 (69 行)
  💡 考虑是否可以简化逻辑

### agents\workflow_orchestrator_v3_final.py

- 🟠 **HIGH** (行 456): 函数 '_execute_phase_with_iteration' 过长 (138 行)
  💡 考虑将函数拆分为更小的子函数
- 🟠 **HIGH** (行 815): 函数 '_generate_final_report' 过长 (157 行)
  💡 考虑将函数拆分为更小的子函数
- 🟠 **HIGH** (行 973): 函数 '_generate_markdown_report' 过长 (135 行)
  💡 考虑将函数拆分为更小的子函数
- 🟡 **MEDIUM** (行 287): 函数 '_interactive_plan_confirmation' 较长 (62 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 373): 函数 '_plan_constraint_audit' 较长 (82 行)
  💡 考虑是否可以简化逻辑

### examples\demo_dynamic_system.py

- 🟠 **HIGH** (行 198): 函数 'demonstrate_dynamic_system' 过长 (121 行)
  💡 考虑将函数拆分为更小的子函数
- 🟠 **HIGH** (行 321): 函数 'generate_demonstration_report' 过长 (128 行)
  💡 考虑将函数拆分为更小的子函数

### examples\opencode_simple.py

- 🟠 **HIGH** (行 197): 函数 '_generate_roles' 过长 (159 行)
  💡 考虑将函数拆分为更小的子函数
- 🟠 **HIGH** (行 394): 函数 '_generate_report' 过长 (106 行)
  💡 考虑将函数拆分为更小的子函数
- 🟡 **MEDIUM** (行 543): 函数 '_generate_markdown_report' 较长 (100 行)
  💡 考虑是否可以简化逻辑

### lib\agent_executor.py

- 🟠 **HIGH** (行 285): 函数 '_execute_openclaw' 过长 (118 行)
  💡 考虑将函数拆分为更小的子函数
- 🟢 **LOW** (行 0): 重复的导入: time
- 🟢 **LOW** (行 0): 重复的导入: os
- 🟡 **MEDIUM** (行 404): 函数 '_execute_local' 较长 (80 行)
  💡 考虑是否可以简化逻辑

### lib\ast_auditor.py

- 🟡 **MEDIUM** (行 187): 函数名 'visit_FunctionDef' 不符合 snake_case 命名规范
  💡 使用小写字母和下划线，如: my_function
- 🟡 **MEDIUM** (行 235): 函数名 'visit_Try' 不符合 snake_case 命名规范
  💡 使用小写字母和下划线，如: my_function
- 🟡 **MEDIUM** (行 266): 函数名 'visit_Call' 不符合 snake_case 命名规范
  💡 使用小写字母和下划线，如: my_function
- 🟡 **MEDIUM** (行 310): 函数名 'visit_Assign' 不符合 snake_case 命名规范
  💡 使用小写字母和下划线，如: my_function
- 🟡 **MEDIUM** (行 344): 函数名 'visit_FunctionDef' 不符合 snake_case 命名规范
  💡 使用小写字母和下划线，如: my_function

### lib\audit_report.py

- 🟠 **HIGH** (行 29): 函数 'generate_markdown_report' 过长 (152 行)
  💡 考虑将函数拆分为更小的子函数

### lib\constraint_checker.py

- 🟡 **MEDIUM** (行 231): 函数 'audit' 较长 (61 行)
  💡 考虑是否可以简化逻辑

### lib\v3\bmad_evo3.py

- 🟠 **HIGH** (行 60): 函数 'execute' 过长 (113 行)
  💡 考虑将函数拆分为更小的子函数

### lib\v3\context_budget.py

- 🟡 **MEDIUM** (行 161): 函数 'check_budget' 较长 (85 行)
  💡 考虑是否可以简化逻辑

### lib\v3\model_router.py

- 🟠 **HIGH** (行 489): 函数 '_heuristic_route' 过长 (102 行)
  💡 考虑将函数拆分为更小的子函数
- 🟡 **MEDIUM** (行 239): 函数 'route' 较长 (65 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 305): 函数 '_build_routing_prompt' 较长 (96 行)
  💡 考虑是否可以简化逻辑

### lib\v3\resilient_executor.py

- 🟠 **HIGH** (行 95): 函数 'execute' 过长 (174 行)
  💡 考虑将函数拆分为更小的子函数
- 🟡 **MEDIUM** (行 95): 函数 'execute' 参数过多 (8 个)
  💡 考虑使用参数对象或配置字典

### lib\v3\role_generator.py

- 🟡 **MEDIUM** (行 92): 函数 'generate' 较长 (57 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 150): 函数 '_build_generation_prompt' 较长 (80 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 314): 函数 '_create_fallback_flow' 较长 (91 行)
  💡 考虑是否可以简化逻辑

### lib\v3\task_analyzer.py

- 🟡 **MEDIUM** (行 60): 函数 'analyze' 较长 (71 行)
  💡 考虑是否可以简化逻辑

### lib\v3\task_directory_manager.py

- 🟠 **HIGH** (行 196): 函数 '_create_initial_task_files' 过长 (131 行)
  💡 考虑将函数拆分为更小的子函数
- 🟡 **MEDIUM** (行 133): 函数 'create_task_structure' 较长 (62 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 379): 函数 'create_new_version' 较长 (54 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 588): 函数 'update_assignment_document' 较长 (88 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 747): 函数 'get_structure_summary' 较长 (55 行)
  💡 考虑是否可以简化逻辑

### quick_audit.py

- 🟡 **MEDIUM** (行 37): 函数 'audit_file' 较长 (54 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 133): 函数 'main' 较长 (56 行)
  💡 考虑是否可以简化逻辑

### real_multi_agent_analysis\tasks\bmad_evo_executor.py

- 🟠 **HIGH** (行 251): 函数 'generate_report' 过长 (101 行)
  💡 考虑将函数拆分为更小的子函数
- 🟡 **MEDIUM** (行 141): 函数 'call_model_with_retry_and_fallback' 较长 (68 行)
  💡 考虑是否可以简化逻辑

### real_multi_agent_analysis\tasks\run_investment_analysis_v3.py

- 🟠 **HIGH** (行 539): 函数 '_generate_investment_report' 过长 (261 行)
  💡 考虑将函数拆分为更小的子函数
- 🟡 **MEDIUM** (行 124): 函数 '_load_comprehensive_intelligence' 较长 (57 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 477): 函数 '_analyst_risk' 较长 (61 行)
  💡 考虑是否可以简化逻辑

### real_multi_agent_analysis\tasks\run_linked_7_experts.py

- 🟠 **HIGH** (行 348): 函数 'generate_final_report' 过长 (182 行)
  💡 考虑将函数拆分为更小的子函数
- 🟡 **MEDIUM** (行 122): 函数 'execute_analyst' 较长 (68 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 191): 函数 'get_prompts_for_analyst' 较长 (73 行)
  💡 考虑是否可以简化逻辑

### real_multi_agent_analysis\tasks\run_multi_model_v2.py

- 🟠 **HIGH** (行 298): 函数 'run_full_analysis' 过长 (174 行)
  💡 考虑将函数拆分为更小的子函数
- 🟠 **HIGH** (行 858): 函数 '_compile_final_report' 过长 (158 行)
  💡 考虑将函数拆分为更小的子函数
- 🟡 **MEDIUM** (行 226): 函数 'search_latest_intelligence' 较长 (56 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 473): 函数 '_run_latest_intelligence_analyst' 较长 (98 行)
  💡 考虑是否可以简化逻辑

### real_multi_agent_analysis\tasks\run_real_7_experts_v4.py

- 🟡 **MEDIUM** (行 57): 函数 'call_model' 较长 (54 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 268): 函数 '_compile_results' 较长 (59 行)
  💡 考虑是否可以简化逻辑

### real_multi_agent_analysis\tasks\run_serial_7_experts.py

- 🟠 **HIGH** (行 171): 函数 'get_prompt' 过长 (195 行)
  💡 考虑将函数拆分为更小的子函数
- 🟠 **HIGH** (行 394): 函数 'main' 过长 (107 行)
  💡 考虑将函数拆分为更小的子函数
- ℹ️ **INFO** (行 9): 发现 TODO 注释
  💡 记得完成 TODO 事项

### real_multi_agent_analysis\tasks\test_model_availability.py

- 🟡 **MEDIUM** (行 54): 函数 'test_model' 较长 (62 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 149): 函数 'generate_report' 较长 (57 行)
  💡 考虑是否可以简化逻辑

### scripts\code_auditor.py

- 🟠 **HIGH** (行 372): 函数 'generate_report' 过长 (137 行)
  💡 考虑将函数拆分为更小的子函数
- ℹ️ **INFO** (行 324): 发现 TODO 注释
  💡 记得完成 TODO 事项
- ℹ️ **INFO** (行 333): 发现 TODO 注释
  💡 记得完成 TODO 事项
- ℹ️ **INFO** (行 334): 发现 TODO 注释
  💡 记得完成 TODO 事项
- 🟡 **MEDIUM** (行 58): 函数 'audit_file' 较长 (74 行)
  💡 考虑是否可以简化逻辑

### scripts\fix_all_issues.py

- 🟠 **HIGH** (行 19): 函数 'fix_all_issues' 过长 (192 行)
  💡 考虑将函数拆分为更小的子函数
- 🟠 **HIGH** (行 213): 函数 'generate_final_report' 过长 (169 行)
  💡 考虑将函数拆分为更小的子函数

### scripts\run_opencode_analysis.py

- 🟡 **MEDIUM** (行 77): 函数 '_analyze_task' 较长 (76 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 154): 函数 '_generate_roles' 较长 (87 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 392): 函数 '_create_default_roles' 较长 (52 行)
  💡 考虑是否可以简化逻辑

### scripts\scan_pseudo_ai.py

- ℹ️ **INFO** (行 78): 发现 TODO 注释
  💡 记得完成 TODO 事项
- 🟡 **MEDIUM** (行 207): 函数名 'visit_FunctionDef' 不符合 snake_case 命名规范
  💡 使用小写字母和下划线，如: my_function
- 🟡 **MEDIUM** (行 228): 函数名 'visit_Return' 不符合 snake_case 命名规范
  💡 使用小写字母和下划线，如: my_function
- 🟡 **MEDIUM** (行 233): 函数名 'visit_ExceptHandler' 不符合 snake_case 命名规范
  💡 使用小写字母和下划线，如: my_function
- 🟡 **MEDIUM** (行 321): 函数 'main' 较长 (79 行)
  💡 考虑是否可以简化逻辑

### test_alibab_models.py

- 🟡 **MEDIUM** (行 29): 函数 'test_model' 较长 (55 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 86): 函数 'main' 较长 (72 行)
  💡 考虑是否可以简化逻辑

### test_task_directory.py

- 🟠 **HIGH** (行 17): 函数 'test_task_directory_manager' 过长 (170 行)
  💡 考虑将函数拆分为更小的子函数
- ℹ️ **INFO** (行 60): 发现 TODO 注释
  💡 记得完成 TODO 事项
- ℹ️ **INFO** (行 65): 发现 TODO 注释
  💡 记得完成 TODO 事项
- ℹ️ **INFO** (行 71): 发现 TODO 注释
  💡 记得完成 TODO 事项

### tests\run_all_tests.py

- 🟠 **HIGH** (行 151): 函数 'generate_comprehensive_report' 过长 (204 行)
  💡 考虑将函数拆分为更小的子函数
- 🟡 **MEDIUM** (行 357): 函数 'main' 较长 (56 行)
  💡 考虑是否可以简化逻辑

### tests\test_dynamic_analysis.py

- 🟡 **MEDIUM** (行 67): 函数 'generate_final_report' 较长 (61 行)
  💡 考虑是否可以简化逻辑

### tests\test_dynamic_system.py

- 🟢 **LOW** (行 0): 重复的导入: task_analyzer.TaskAnalyzer
- 🟡 **MEDIUM** (行 180): 函数 'test_resilient_executor' 较长 (60 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 242): 函数 'test_workflow_executor' 较长 (55 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 330): 函数 'test_integration_flow' 较长 (58 行)
  💡 考虑是否可以简化逻辑

### tests\test_integration.py

- 🟢 **LOW** (行 0): 重复的导入: v3.model_router.AVAILABLE_MODELS
- 🟢 **LOW** (行 0): 重复的导入: v3.context_budget.MODEL_CONTEXT_WINDOWS
- 🟢 **LOW** (行 0): 重复的导入: agent_executor.DEFAULT_AGENTS
- 🟡 **MEDIUM** (行 26): 函数 'test_task_directory_integration' 较长 (59 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 125): 函数 'test_context_budget_integration' 较长 (58 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 185): 函数 'test_agent_executor_integration' 较长 (53 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 341): 函数 'run_all_integration_tests' 较长 (55 行)
  💡 考虑是否可以简化逻辑

### tests\test_phase_gateway_e2e.py

- 🟡 **MEDIUM** (行 150): 函数 'test_bad_code' 较长 (52 行)
  💡 考虑是否可以简化逻辑

### tests\test_unit.py

- 🟡 **MEDIUM** (行 19): 函数 'test_task_directory_manager' 较长 (83 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 105): 函数 'test_context_budget_manager' 较长 (72 行)
  💡 考虑是否可以简化逻辑
- 🟡 **MEDIUM** (行 267): 函数 'run_all_tests' 较长 (51 行)
  💡 考虑是否可以简化逻辑

### tests\test_v3_full_integration.py

- 🟢 **LOW** (行 0): 重复的导入: workflow_orchestrator_v3_final.WorkflowOrchestratorV3Final
- 🟢 **LOW** (行 0): 重复的导入: workflow_orchestrator_v3_final.WorkflowOrchestratorV3Final
- 🟡 **MEDIUM** (行 26): 函数 'test_full_workflow_mock' 较长 (68 行)
  💡 考虑是否可以简化逻辑

---

## 文件统计

| 文件 | 总行数 | 代码行 | 注释行 | 文档分 | 平均复杂度 |
|------|--------|--------|--------|--------|------------|
| agents\constraint_auditor.py | 273 | 118 | 91 | ✅ 90.0% | 3.0 |
| agents\decision_interface.py | 395 | 83 | 235 | ✅ 96.4% | 4.0 |
| agents\phase_gateway.py | 432 | 229 | 128 | ⚠️ 77.1% | 3.0 |
| agents\test_repairs.py | 236 | 74 | 116 | ❌ 42.9% | 2.3 |
| agents\workflow_orchestrator.py | 417 | 132 | 196 | ✅ 96.7% | 4.2 |
| agents\workflow_orchestrator_v3_final.py | 1131 | 275 | 696 | ⚠️ 77.9% | 4.6 |
| examples\ast_quick_start.py | 95 | 9 | 66 | ❌ 20.0% | 0.0 |
| examples\demo_dynamic_system.py | 453 | 368 | 41 | ❌ 33.3% | 4.0 |
| examples\opencode_simple.py | 676 | 160 | 434 | ❌ 35.0% | 2.7 |
| lib\agent_executor.py | 550 | 284 | 180 | ⚠️ 65.3% | 2.3 |
| lib\ast_auditor.py | 599 | 193 | 307 | ✅ 94.8% | 3.4 |
| lib\audit_report.py | 355 | 22 | 271 | ✅ 95.6% | 3.3 |
| lib\constraint_checker.py | 556 | 134 | 333 | ⚠️ 65.9% | 3.6 |
| lib\opencode_adapter.py | 211 | 49 | 119 | ⚠️ 73.3% | 2.0 |
| lib\v3\__init__.py | 92 | 75 | 12 | ❌ 20.0% | 0.0 |
| lib\v3\bmad_evo3.py | 241 | 144 | 56 | ⚠️ 76.0% | 2.0 |
| lib\v3\context_budget.py | 345 | 267 | 25 | ❌ 36.4% | 2.6 |
| lib\v3\model_router.py | 664 | 294 | 289 | ❌ 28.0% | 4.9 |
| lib\v3\resilient_executor.py | 629 | 304 | 218 | ❌ 46.7% | 2.9 |
| lib\v3\role_generator.py | 470 | 176 | 226 | ❌ 47.9% | 2.4 |
| lib\v3\task_analyzer.py | 337 | 54 | 228 | ⚠️ 64.0% | 2.6 |
| lib\v3\task_directory_manager.py | 860 | 126 | 567 | ❌ 44.7% | 2.9 |
| quick_audit.py | 192 | 75 | 86 | ❌ 20.0% | 5.8 |
| real_multi_agent_analysis\tasks\bmad_evo_executor.py | 428 | 168 | 181 | ❌ 48.3% | 3.4 |
| real_multi_agent_analysis\tasks\run_investment_analysis_v3.py | 816 | 224 | 422 | ❌ 32.6% | 2.0 |
| real_multi_agent_analysis\tasks\run_linked_7_experts.py | 535 | 129 | 309 | ❌ 33.3% | 3.1 |
| real_multi_agent_analysis\tasks\run_multi_model_v2.py | 1052 | 72 | 757 | ⚠️ 52.4% | 2.9 |
| real_multi_agent_analysis\tasks\run_real_7_experts_v4.py | 332 | 78 | 198 | ❌ 37.1% | 2.9 |
| real_multi_agent_analysis\tasks\run_serial_7_experts.py | 505 | 52 | 358 | ❌ 26.7% | 4.5 |
| real_multi_agent_analysis\tasks\test_model_availability.py | 266 | 109 | 106 | ❌ 46.7% | 2.7 |
| scripts\code_auditor.py | 542 | 125 | 346 | ❌ 20.0% | 6.1 |
| scripts\fix_all_issues.py | 401 | 91 | 225 | ❌ 20.0% | 8.0 |
| scripts\run_opencode_analysis.py | 543 | 128 | 319 | ⚠️ 68.9% | 2.6 |
| scripts\scan_pseudo_ai.py | 404 | 152 | 191 | ⚠️ 55.4% | 5.8 |
| test_alibab_models.py | 162 | -6 | 140 | ❌ 20.0% | 4.5 |
| test_task_directory.py | 191 | 67 | 85 | ❌ 20.0% | 1.0 |
| tests\run_all_tests.py | 417 | 210 | 123 | ❌ 20.0% | 9.0 |
| tests\test_agent_executor.py | 244 | 24 | 160 | ❌ 42.9% | 1.6 |
| tests\test_ast_integration.py | 139 | 0 | 113 | ❌ 20.0% | 0.0 |
| tests\test_dynamic_analysis.py | 132 | 57 | 45 | ❌ 20.0% | 3.0 |
| tests\test_dynamic_system.py | 482 | 152 | 235 | ❌ 20.0% | 1.5 |
| tests\test_integration.py | 401 | 103 | 215 | ❌ 25.0% | 3.0 |
| tests\test_phase_gateway_e2e.py | 284 | 32 | 186 | ❌ 36.0% | 2.6 |
| tests\test_unit.py | 323 | 93 | 170 | ❌ 33.3% | 2.0 |
| tests\test_v3_full_integration.py | 244 | 62 | 127 | ❌ 26.7% | 2.8 |
| tests\test_v3_integration.py | 295 | 61 | 166 | ⚠️ 50.0% | 1.9 |

---

## 改进建议

2. 🟠 **修复所有 HIGH 级别问题**，包括函数过长、异常处理不当等
3. 📝 **提高文档覆盖率**，41 个文件文档完整性不足 80%
4. 🔄 **降低复杂度**，8 个文件存在高复杂度函数

---

*本报告由 BMAD-EVO 代码审计工具自动生成*