# BMAD-EVO v3.0 流程实现对比 - 修正版

## 正确的流程顺序（用户最终确认）

```
用户输入
↓
项目生成
↓
定义全局约束
↓
任务类型检测
↓
复杂度评估
↓
角色流程生成（包含选择合适的模型）
↓
【阶段网关】启动阶段 N
↓
【Agent 执行】调用对应模型角色按流程执行
↓
【强制审计】自动触发
↓
通过（≥85分）→ 【网关】进入阶段 N+1
↓
未通过，三次重试，仍失败就提交用户决策
```

## 实现对比

### 1. workflow_orchestrator_v3.py (基础版 - 错误顺序)

**流程顺序**:
```
任务分析 → 角色生成 → 项目初始化 → 批量执行所有角色 → 统一审计
```

**问题**:
- ❌ 项目生成太晚（在任务分析之后）
- ❌ 没有先定义全局约束
- ❌ 任务分析和复杂度评估顺序正确，但位置不对
- ❌ 批量执行，没有阶段 N→N+1 流转
- ❌ 没有 ≥85分检查
- ❌ 没有 3次重试机制

### 2. workflow_orchestrator_v3_complete.py (完整版 - 错误顺序)

**流程顺序**:
```
任务分析 → 角色生成 → 项目初始化 → 阶段执行（有重试和审计）
```

**问题**:
- ❌ 仍然是任务分析在前，项目生成在后
- ❌ 没有先定义全局约束
- 其他流程（阶段执行、审计、重试、决策）是正确的

### 3. workflow_orchestrator_v3_final.py (最终版 - 正确顺序) ⭐

**流程顺序**:
```
用户输入 (execute_full_workflow参数)
↓
Step 1: _generate_project() - 项目生成
↓
Step 2: _define_global_constraints() - 定义全局约束
↓
Step 3: task_analyzer.analyze() - 任务类型检测
↓
Step 4: (complexity from analysis) - 复杂度评估
↓
Step 5: role_generator.generate() + model_router.route() - 角色流程生成（包含模型选择）
↓
Step 6: 阶段执行循环
  ├─ 【阶段网关】启动阶段 N
  ├─ 【Agent 执行】_execute_agent()
  ├─ 【强制审计】_perform_audit()
  ├─ 检查 ≥85分
  │   ├─ 通过 → 进入阶段 N+1
  │   └─ 未通过
  │       ├─ 重试（最多3次）
  │       └─ 重试用尽 → _user_decision()
  │           ├─ force_proceed → 强制继续
  │           ├─ relax_constraint → 放宽约束
  │           ├─ manual_fix → 等待手动修复
  │           └─ abort → 中止
```

**正确性验证**:

| 步骤 | 方法 | 状态 |
|------|------|------|
| 1. 用户输入 | `execute_full_workflow(task_description)` | ✅ |
| 2. 项目生成 | `_generate_project()` | ✅ |
| 3. 定义全局约束 | `_define_global_constraints()` | ✅ |
| 4. 任务类型检测 | `task_analyzer.analyze()` | ✅ |
| 5. 复杂度评估 | `task_analysis.complexity_score` | ✅ |
| 6. 角色流程生成 | `role_generator.generate()` | ✅ |
| 6a. 模型选择 | `model_router.route()` | ✅ |
| 7. 阶段网关启动 | `_execute_phase() 循环` | ✅ |
| 8. Agent执行 | `_execute_agent()` | ✅ |
| 9. 强制审计 | `_perform_audit()` | ✅ |
| 10. ≥85分检查 | `audit_score >= pass_threshold` | ✅ |
| 11. 3次重试 | `for attempt in range(1, max_retries+1)` | ✅ |
| 12. 用户决策 | `_user_decision()` | ✅ |

## 关键修正点

### 1. 项目生成和全局约束的位置

**错误** (v3.py, v3_complete.py):
```python
# 先分析任务
task_analysis = analyzer.analyze(task)
# 再生成角色
role_flow = generator.generate(task, task_analysis)
# 最后才创建项目
_initialize_project()  # 太晚了！
```

**正确** (v3_final.py):
```python
# 第一步：创建项目
_generate_project(task)
# 第二步：定义约束
_define_global_constraints()
# 第三步：分析任务
task_analysis = analyzer.analyze(task)
# 第四步：生成角色
role_flow = generator.generate(task, task_analysis)
```

### 2. 为什么这个顺序很重要？

1. **项目生成优先**: 任务分析和角色生成可能需要写入文件，需要先有项目目录
2. **全局约束影响审计**: 约束配置在审计之前定义，确保审计规则正确
3. **约束可定制**: 用户可以根据项目类型（API/脚本/系统）定义不同的约束
4. **符合工程实践**: 先搭好舞台（项目），再开始表演（任务执行）

### 3. 角色流程包含的内容

**RoleDefinition**:
- name, title, description
- responsibilities
- **input_from**: 前置角色（数据依赖）
- **output_to**: 后续角色
- **can_parallel**: 是否可以并行
- required_skills
- estimated_time

**RoleFlow**:
- roles: 所有角色
- **execution_order**: 阶段执行顺序（阶段 N→N+1）
- **parallel_groups**: 可并行组
- rationale: 设计理由

**ModelRouting**:
- 为每个角色选择 primary_model + fallback_models
- 根据角色职责和复杂度匹配模型能力

## 使用方式

### 正确流程版本 (v3_final.py)

```python
from agents.workflow_orchestrator_v3_final import WorkflowOrchestratorV3Final

# 创建编排器
orchestrator = WorkflowOrchestratorV3Final(
    project_path="./my_project",
    interactive=True
)

# 执行完整流程
result = orchestrator.execute_full_workflow("开发用户认证系统")
```

或命令行：

```bash
python3 agents/workflow_orchestrator_v3_final.py \
    --project ./my_project \
    "开发用户认证系统"
```

## 流程输出示例

```
======================================================================
🚀 BMAD-EVO v3.0 - 修正流程
======================================================================
任务: 开发用户认证系统...
======================================================================

📋 Step 1: 项目生成
----------------------------------------------------------------------
✅ 项目生成完成: ./my_project

📋 Step 2: 定义全局约束
----------------------------------------------------------------------
✅ 全局约束定义完成

📋 Step 3: 任务类型检测
----------------------------------------------------------------------
✅ 任务类型检测完成: api_development

📋 Step 4: 复杂度评估
----------------------------------------------------------------------
✅ 复杂度评估完成: 7/10
   预估时间: 2-3天
   推荐角色数: 4

📋 Step 5: 角色流程生成（包含模型选择）
----------------------------------------------------------------------
✅ 角色生成完成: 4 个角色
   执行顺序: requirement_analyst → architect → developer → qa

✅ 模型选择完成:
   requirement_analyst: zhipu/glm-5
   architect: kimi-coding/k2p5
   developer: kimi-coding/k2p5
   qa: alibaba/qwen3.5-plus
   预估成本: medium

======================================================================
📋 Step 6: 阶段执行（网关 → 执行 → 审计 → 重试/决策）
======================================================================

======================================================================
🚀 【阶段网关】启动阶段 1/4: 需求分析师
======================================================================

📍 尝试 1/3
   角色: 需求分析师
   模型: zhipu/glm-5

   🤖 【Agent 执行】调用模型...
   ⏱️  执行时间: 15.32s

   🔍 【强制审计】检查中...
   📊 审计分数: 92/100 (需要≥85)
   ✅ 审计通过！

======================================================================
🚀 【阶段网关】启动阶段 2/4: 架构师
======================================================================
...
```

## 总结

| 文件 | 顺序 | 阶段流转 | 审计+重试+决策 | 推荐使用 |
|------|------|----------|----------------|----------|
| v3.py | ❌ 错误 | ❌ 批量 | ❌ 无 | 不推荐 |
| v3_complete.py | ❌ 错误 | ✅ 有 | ✅ 有 | 不推荐 |
| **v3_final.py** | ✅ **正确** | ✅ **有** | ✅ **有** | **✅ 推荐** |

**最终结论**: `workflow_orchestrator_v3_final.py` 完全符合用户要求的流程顺序。
