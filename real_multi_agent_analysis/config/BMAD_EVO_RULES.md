# BMAD-EVO v3.1 系统规则与配置

**版本**: v3.1  
**最后更新**: 2026-04-06  
**适用**: 所有多模型协同分析任务

---

## 一、系统架构规则

### 1.1 目录结构规范

```
BMAD-EVO/
├── agents/                 # 核心框架（保持不变）
├── config/                 # 配置文件
├── lib/                    # 核心库（保持不变）
│   └── v3/                 # v3.1 动态系统
│       ├── task_analyzer.py
│       ├── role_generator.py
│       ├── model_router.py
│       ├── context_budget.py   # 上下文预算管理（新增）
│       ├── resilient_executor.py
│       └── bmad_evo3.py
├── examples/               # 示例代码
├── templates/              # 模板文件
├── scripts/                # 工具脚本
├── docs/                   # 文档
└── [任务目录]/            # 具体任务目录（如：real_multi_agent_analysis/）
    ├── tasks/             # 任务入口脚本
    ├── config/            # 任务专属配置
    ├── results/           # 分析结果
    └── docs/              # 任务文档
```

**规则**:
- ✅ 所有任务入口脚本必须放在 `任务目录/tasks/` 下
- ✅ 所有任务结果必须放在 `任务目录/results/` 下
- ✅ 所有任务配置必须放在 `任务目录/config/` 下
- ❌ 禁止在主目录下直接创建任务脚本（除系统级工具外）

---

## 二、模型调用规则

### 2.1 可用模型列表

#### GLM Coding Plan 模型（主要）

| 模型ID | 模型名称 | 定位 | 上下文窗口(输入/输出) |
|--------|----------|------|----------------------|
| `glm-5.1` | GLM-5.1 旗舰 (推理级) | 复杂推理、系统架构 | 200K / 128K |
| `glm-4.7` | GLM-4.7 全能主力 | 通用编码、多轮对话 | 200K / 128K |
| `glm-4.7-flash` | GLM-4.7-Flash 轻量开源 | 低延迟、快速实验 | 200K / 128K |
| `glm-4.7-flashx` | GLM-4.7-FlashX 云端极速 | 高并发、批量任务 | 200K / 128K |
| `glm-4.6` | GLM-4.6 上一代主力 | 稳定编码、通用编程 | 200K / 128K |
| `glm-4.6v` | GLM-4.6V 多模态编码 | 设计图转代码、视觉调试 | 128K / 128K |
| `glm-4.5-air` | GLM-4.5-Air 超轻量 | 极简场景、快速补全 | 128K / 128K |

#### 绝对回退模型

| 模型ID | 模型名称 | 用途 |
|--------|----------|------|
| `kimi-coding/k2p5` | Kimi K2P5 | 所有 GLM 模型均失败时的终极回退 |

### 2.2 角色模型分配规则

| 角色类型 | 主模型 | 备选模型 | 理由 |
|----------|--------|----------|------|
| 需求分析/产品经理 | `glm-4.7` | glm-5.1, glm-4.7-flash | 全能主力，逻辑推理 |
| 架构设计 | `glm-5.1` | glm-4.7, glm-4.7-flash | 深度推理，系统规划 |
| 代码开发 | `glm-5.1` | glm-4.7, glm-4.7-flash | 代码能力最强 |
| UX设计/视觉 | `glm-4.6v` | glm-4.7, glm-5.1 | 多模态能力 |
| QA/测试审查 | `glm-4.7-flash` | glm-4.7, glm-4.5-air | 快速细致 |
| 部署/运维 | `glm-4.7` | glm-4.7-flash, glm-5.1 | 稳定通用 |

### 2.3 核心调用规则

#### 规则1: 模型回退链

```
主模型 (GLM)
  ↓ 失败
备选模型1 (GLM)
  ↓ 失败
备选模型2 (GLM)
  ↓ 失败
绝对回退 (kimi-coding/k2p5)
  ↓ 失败
生成失败回退输出
```

**代码实现**:
```python
# 每个角色的模型链
model_chain = [primary_model, fallback1, fallback2, "kimi-coding/k2p5"]

for model in model_chain:
    try:
        result = call_model(model, prompt, system_prompt)
        if result.success:
            return result
    except Exception:
        continue

# 所有模型失败
return generate_fallback_output(role_id, task_context)
```

#### 规则2: 上下文预算管理

```python
HEADROOM_RATIO = 0.20  # 预留20%余量防止幻觉

# 检查预算
usable_input = model_context_window * (1 - HEADROOM_RATIO)
if estimated_tokens > usable_input:
    # 建议: 拆分任务 或 切换更大窗口模型
    suggest_task_split()
```

#### 规则3: 超时处理

| 模型 | 超时时间 | 超时动作 |
|------|----------|----------|
| GLM-5.1 | 120秒 | 记录超时，触发回退 |
| GLM-4.7 | 120秒 | 记录超时，触发回退 |
| GLM-4.7-Flash/FlashX | 60秒 | 记录超时，触发回退 |
| GLM-4.6/4.6V | 90秒 | 记录超时，触发回退 |
| GLM-4.5-Air | 60秒 | 记录超时，触发回退 |
| Kimi K2P5 (回退) | 120秒 | 记录超时，生成回退输出 |

---

## 三、任务执行流程

### 3.1 标准执行流程 (v3.1)

```
开始任务
  ↓
步骤1: 项目生成
  ↓
步骤2: 定义全局约束
  ↓
步骤3: 任务类型检测 + 复杂度评估
  ↓
步骤4: 上下文预算检查
  ↓
步骤5: 角色流程生成 + 模型选择
  ↓
步骤5.6: 交互式任务分解确认（多轮对话完善）
  ↓
步骤5.7: 分解结果约束审计
  ↓
步骤6: 阶段执行循环
  ├─ 阶段N: Agent执行 → 强制审计
  │   ├─ 通过 → 下一阶段
  │   └─ 未通过 → 多轮迭代（关键节点确认模式）
  │       ├─ 首次未通过: 询问用户（继续/反馈/强制/中止）
  │       ├─ 之后自动迭代（直到通过或达到上限）
  │       └─ 达到上限 → 用户决策
  └─ 所有阶段完成
  ↓
步骤7: 生成最终报告
  ↓
结束
```

### 3.2 多轮迭代执行模式

**关键节点确认模式**:
1. 首次执行后询问用户（继续自动迭代 / 输入反馈 / 强制通过 / 中止）
2. 之后自动迭代直到审计通过或达到上限
3. 用户反馈作为下一轮新约束

```python
# 迭代执行逻辑
for iteration in range(1, max_iterations + 1):
    result = execute_agent(role, task, feedback=accumulated_feedback)
    audit = perform_audit(result)
    
    if audit.score >= threshold:
        return passed
    
    if iteration == 1 and interactive:
        # 首次未通过，询问用户
        choice = ask_user()
        if choice == 'feedback':
            accumulated_feedback.append(user_feedback)
    
    # 自动继续迭代
    accumulated_feedback.append(audit_summary)
```

### 3.3 进度追踪要求

每个角色执行时必须显示：
- [ ] 角色编号和名称
- [ ] 使用的模型
- [ ] 当前迭代次数
- [ ] 当前状态（执行中/审计中/迭代中/完成/失败）
- [ ] API调用次数
- [ ] 响应时间
- [ ] 审计分数

---

## 四、输出规范

### 4.1 报告结构

```markdown
# [任务标题]分析报告

**生成时间**: YYYY-MM-DD HH:MM:SS
**版本**: v3.1
**分析状态**: X/N 阶段成功完成
**模型体系**: GLM Coding Plan (回退: kimi-coding/k2p5)

---

## 阶段执行详情

### 阶段 N: [角色名]
**模型**: [模型名]（或回退到 kimi-coding/k2p5）
**迭代**: X 次
**状态**: ✅ 完成 / ❌ 失败
**审计分数**: XX/100
**耗时**: XX秒

[详细内容]

---

## 综合结论

[汇总分析]
```

---

## 五、配置参数

### 5.1 模型调用配置

```python
MODEL_CONFIG = {
    "glm-5.1": {
        "timeout": 120,
        "max_tokens": 8000,
        "max_retries": 3,
        "context_window": 200000,
        "output_window": 128000,
    },
    "glm-4.7": {
        "timeout": 120,
        "max_tokens": 8000,
        "max_retries": 3,
        "context_window": 200000,
        "output_window": 128000,
    },
    "glm-4.7-flash": {
        "timeout": 60,
        "max_tokens": 8000,
        "max_retries": 3,
        "context_window": 200000,
        "output_window": 128000,
    },
    "glm-4.7-flashx": {
        "timeout": 60,
        "max_tokens": 8000,
        "max_retries": 3,
        "context_window": 200000,
        "output_window": 128000,
    },
    "glm-4.6": {
        "timeout": 90,
        "max_tokens": 8000,
        "max_retries": 3,
        "context_window": 200000,
        "output_window": 128000,
    },
    "glm-4.6v": {
        "timeout": 90,
        "max_tokens": 8000,
        "max_retries": 3,
        "context_window": 128000,
        "output_window": 128000,
    },
    "glm-4.5-air": {
        "timeout": 60,
        "max_tokens": 4000,
        "max_retries": 3,
        "context_window": 128000,
        "output_window": 128000,
    },
}

DEFAULT_PRIMARY_MODEL = "glm-4.7"
DEFAULT_FALLBACK_MODEL = "glm-5.1"
ABSOLUTE_FALLBACK_MODEL = "kimi-coding/k2p5"
```

### 5.2 上下文预算配置

```python
HEADROOM_RATIO = 0.20  # 预留20%余量
MAX_ITERATIONS = 5     # 每阶段最大迭代次数
```

---

## 六、质量保证

### 6.1 执行前检查清单

- [ ] 确认 GLM API 可用
- [ ] 确认回退模型 (kimi-coding/k2p5) 可用
- [ ] 检查上下文预算是否充足
- [ ] 验证目录结构正确

### 6.2 执行中监控

- [ ] 实时显示每个阶段的迭代进度
- [ ] 记录API调用日志和模型切换
- [ ] 监控上下文预算消耗
- [ ] 检测异常并提示

### 6.3 执行后验证

- [ ] 检查报告完整性
- [ ] 标注使用回退模型的阶段
- [ ] 确认所有迭代记录已包含
- [ ] 验证上下文预算未超限

---

## 七、附录

### 7.1 更新日志

**v3.1 (2026-04-06)**:
- 模型体系替换为 GLM Coding Plan (7个模型)
- 新增 kimi-coding/k2p5 作为绝对回退
- 新增上下文预算管理（20%余量）
- 新增交互式任务分解确认（多轮对话）
- 新增分解结果约束审计
- 新增多轮迭代执行（关键节点确认模式）
- 用户反馈作为下一轮新约束

**v3.0 (2026-03-30)**:
- 建立3次重试+默认模型回退规则
- 规范目录结构
- 添加模型可用性测试
- 增加进度追踪和透明度要求

---

**文档结束**  
**BMAD-EVO v3.1 System Rules & Configuration**
