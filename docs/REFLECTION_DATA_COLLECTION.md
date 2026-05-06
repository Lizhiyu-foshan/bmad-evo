# 反思: v4.0 增量数据采集功能为何形同虚设

## 缺陷现象

v4.0 宣称支持"增量数据采集"，但实际运行时：
1. `DataCollectionPlanner.plan_for_role()` 只有签名，没有实现 — 调用即 `AttributeError`
2. 没有任何代码实际执行 HTTP 请求获取实时数据
3. `enhanced_context` 在编排器中计算后从未传递给角色执行
4. `ThinkingChainExecutor` 缺少 `execute_full_chain()` 入口
5. 最终角色分析全部基于 LLM 编造的"合理数字"，而非真实市场数据

## 根因分析

### 1. 接口先行，实现后补 — 但后补从未发生

v4.0 设计阶段先定义了 `DataCollectionSpec`、`DataCollectionPlanner`、`FeedbackProcessor` 等数据类和类签名。这是合理的接口设计方式。问题在于：**没有为这些类编写测试，导致"已声明但未实现"的状态不会被检测到。**

**教训**: 每个声明的公共方法必须有对应的测试。即使实现是 stub，测试也应该验证方法可调用且返回合法类型。

### 2. 集成测试缺失

`ThinkingChainExecutor` 的 `get_pre_execution_context()` 调用了 `self.data_planner.plan_for_role()`，但没有任何测试验证这条调用链。如果有一个简单的集成测试，第一步就会发现 `plan_for_role` 不存在。

**教训**: 关键调用链（executor → planner → collector）必须有端到端集成测试，哪怕只验证"不会崩溃"。

### 3. 编排器与引擎的职责边界模糊

`workflow_orchestrator` 调用 `tc.get_pre_execution_context()` 获取了 `enhanced_context`，但没有传递给 `_execute_agent()`。这表明编排器的作者和引擎的作者之间没有明确的契约：谁负责注入上下文？

**教训**: 跨模块接口必须有显式的参数契约，且在方法签名中强制体现（`additional_context` 参数）。

### 4. "能跑就行"的综合症

整个 v4.0 思考链路径的 `execute_full_chain()` 入口从未实现，但因为编排器自己实现了正向执行循环（`_tc_forward_pass`），所以从编排器入口来看"能跑"。真正的执行路径绕过了引擎的入口，直接操作引擎内部方法。

**教训**: 不应该绕过引擎的公共入口直接调用内部方法。如果公共入口不够用，应该扩展入口而不是在外部复制逻辑。

### 5. 未区分"需要数据"和"不需要数据"的任务

数据采集流程被无条件嵌入思考链模式，即使任务类型是代码重构、算法设计等完全不需要实时数据的场景也会触发 LLM 调用去"规划数据采集"。

**教训**: 功能开关应该由任务分析阶段决定，不是全局一刀切。

## 改进措施（已实施）

| 问题 | 修复 |
|------|------|
| `plan_for_role()` 未实现 | 完整实现，含 LLM 调用、JSON 提取、错误回退 |
| 无实际 HTTP 数据采集 | 新建 `DataCollector`，支持商品/市场/经济/新闻四类数据源 |
| `enhanced_context` 未传递 | 三层方法签名链 `_execute_phase_with_iteration` → `_execute_agent_with_feedback` → `_execute_agent` 均新增 `additional_context` 参数 |
| 缺少 `execute_full_chain()` 入口 | 完整实现，含角色排序、重执行、自我反思循环 |
| 无条件数据采集 | `TaskAnalysis.needs_data_collection` 由 LLM 在任务分析阶段决定 |
| 零测试 | 20 个单元测试覆盖所有核心类和方法 |

## 防范清单（未来开发必查）

1. **每个公共方法必须有测试** — 在写完类签名后立即写测试 stub
2. **关键调用链必须有集成测试** — 验证 A→B→C 不会在中间断链
3. **跨模块参数传递必须通过方法签名** — 不依赖"对方知道要把这个值传下去"
4. **功能开关由任务分析决定** — 不在引擎层做全局假设
5. **公共入口优先** — 不在外部复制引擎内部逻辑
6. **CI 必须跑测试** — 防止"声明但未实现"溜进主分支
