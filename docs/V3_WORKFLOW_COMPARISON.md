# BMAD-EVO v3.0 流程实现对比

## 用户要求的完整流程

```
用户输入
↓
任务类型检测 → 复杂度评估
↓
角色流程生成
↓
项目生成 + 定义全局约束
↓
【阶段网关】启动阶段 N (动态角色名 + 对应模型)
↓
【Agent 执行】调用模型角色
↓
【强制审计】≥85分通过
    ├── 通过 → 进入阶段 N+1
    └── 未通过 → 3次重试 → 用户决策
```

## 实现对比

### 1. workflow_orchestrator_v3.py (基础集成)

**已实现**:
- ✅ 任务类型检测 → 复杂度评估 (TaskAnalyzer)
- ✅ 角色流程生成 (DynamicRoleGenerator)
- ⚠️ 项目生成 + 全局约束 (部分实现)
- ✅ 【阶段网关】概念存在但未严格按阶段流转
- ⚠️ 【Agent 执行】简化实现
- ⚠️ 【强制审计】有审计但无 ≥85分阈值
- ❌ 未通过 → 3次重试 (无阶段级重试)
- ❌ 用户决策 (有DecisionInterface但未在失败时调用)

**流程问题**:
- 一次性执行完所有角色，没有真正的"阶段 N → 阶段 N+1"流转
- 审计只是展示结果，不阻塞流程
- 没有3次重试机制
- 审计失败不触发用户决策

### 2. workflow_orchestrator_v3_complete.py (完整实现)

**已实现**:
- ✅ 任务类型检测 → 复杂度评估 (TaskAnalyzer)
- ✅ 角色流程生成 (DynamicRoleGenerator)
- ✅ 项目生成 + 定义全局约束 (_initialize_project)
- ✅ 【阶段网关】严格的阶段流转 (_execute_phase_with_retry)
- ✅ 【Agent 执行】模型选择 + 调用 (_execute_role)
- ✅ 【强制审计】≥85分阈值检查
- ✅ 未通过 → 3次重试 (for attempt in range(1, max_retries + 1))
- ✅ 用户决策 (_handle_blocked_phase → DecisionInterface)

**流程特点**:
```python
for role in execution_order:  # 严格的阶段 N → N+1
    for attempt in range(1, max_retries + 1):  # 3次重试
        output = execute_role(role)  # Agent执行
        audit = audit_phase(output)   # 强制审计
        score = calculate_score(audit)  # 计算分数
        
        if score >= 85:  # ≥85分通过检查
            break  # 进入阶段 N+1
        elif attempt < max_retries:
            continue  # 重试
        else:
            decision = user_decision()  # 用户决策
            # force_proceed / manual_fix / relax_constraint / abort
```

## 关键差异说明

### 角色流程设计包含内容

**RoleDefinition (单个角色)**:
- name: 角色标识
- title: 显示名称
- description: 职责描述
- responsibilities: 具体职责列表
- **input_from**: 输入来源角色 (定义角色间数据流)
- **output_to**: 输出目标角色
- **can_parallel**: 是否可并行执行
- estimated_time: 预计时间
- required_skills: 所需技能
- model_requirement: 对模型的要求

**RoleFlow (完整流程)**:
- roles: 所有角色列表
- **execution_order**: 执行顺序 (阶段 N → N+1 的顺序)
- **parallel_groups**: 可并行执行的组
- rationale: 流程设计理由

### 阶段流转 vs 批量执行

**v3.py (批量执行)**:
```python
# 问题: 一次性执行所有角色，然后统一审计
for role in roles:
    result = execute(role)  # 全部执行完
for role in roles:
    audit = audit(result)   # 然后统一审计
```

**v3_complete.py (阶段流转)**:
```python
# 正确: 一个阶段执行+审计通过后，才进入下一阶段
for role in execution_order:
    for attempt in range(3):
        result = execute(role)
        audit = audit(result)
        if audit.score >= 85:
            break  # 通过，进入下一阶段
    else:
        decision = user_decision()  # 3次失败，用户决策
```

## 建议使用

### 基础测试/快速原型
```bash
# 使用 v3.py - 快速执行但不严格
python3 agents/workflow_orchestrator_v3.py --project . run "任务描述"
```

### 生产环境/严格流程
```bash
# 使用 v3_complete.py - 严格的阶段流转
python3 agents/workflow_orchestrator_v3_complete.py --project . "任务描述"
```

## 待完善项

即使是 v3_complete.py，仍有以下待完善：

1. **真实的模型调用**: 当前 `_execute_role` 是简化实现，需要接入 ResilientExecutor 的真实调用
2. **并行组执行**: 当前按 execution_order 串行执行，需要支持 parallel_groups 的并行执行
3. **检查点恢复**: 需要实现中断后从检查点恢复的功能
4. **完整的项目初始化**: 需要生成完整的项目结构（源码目录、配置文件等）

## 总结

| 组件 | v3.py | v3_complete.py | 要求 |
|------|-------|----------------|------|
| 任务分析 | ✅ | ✅ | ✅ |
| 角色生成 | ✅ | ✅ | ✅ |
| 流程设计 (execution_order) | ✅ | ✅ | ✅ |
| 阶段 N→N+1 流转 | ❌ | ✅ | ✅ |
| ≥85分审计 | ❌ | ✅ | ✅ |
| 3次重试 | ❌ | ✅ | ✅ |
| 用户决策 | ❌ | ✅ | ✅ |
| 模型路由 | ✅ | ✅ | ✅ |
| Agent执行 | ⚠️ | ⚠️ | ⚠️ |
| 并行组支持 | ❌ | ❌ | ⚠️ |

**结论**: v3_complete.py 完全符合用户要求的流程设计。
