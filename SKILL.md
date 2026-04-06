---
name: bmad-evo
description: BMAD-EVO v3.1 进化版多Agent开发框架。基于 GLM Coding Plan 模型体系，支持上下文预算管理、交互式任务分解确认、分解后约束审计、多轮迭代执行。所有 GLM 模型失败时自动回退到 kimi-coding/k2p5。
---

# BMAD-EVO v3.1

**进化版多Agent开发框架** - 约束驱动 + 强制审计 + 阶段拦截 + 用户决策 + 复盘优化 + **全动态角色生成** + **上下文预算管理** + **多轮迭代执行**

## v3.1 功能全景

| 阶段 | 功能 | 状态 |
|------|------|------|
| **Phase 1** | 🔒 强制约束审计 | ✅ 已完成 |
| | 📊 审计报告生成 | ✅ 已完成 |
| | 🎯 约束模板 | ✅ 已完成 |
| **Phase 2** | 🚧 阶段流转拦截 | ✅ 已完成 |
| | 👤 用户决策界面 | ✅ 已完成 |
| | 🔄 工作流编排 | ✅ 已完成 |
| | 🤖 **Agent 执行层** | ✅ 已完成 |
| **Phase 3** | 🧠 **全动态角色生成** | ✅ 已完成 |
| | 📋 任务类型检测 | ✅ 已完成 |
| | 📊 复杂度评估 | ✅ 已完成 |
| | 🎭 动态角色流程 | ✅ 已完成 |
| | 🎯 智能模型路由 | ✅ 已完成 |
| **Phase 3.1** | 📐 **上下文预算管理** | ✅ **新增** |
| | 💬 **交互式任务分解确认** | ✅ **新增** |
| | 🔍 **分解后约束审计** | ✅ **新增** |
| | 🔄 **多轮迭代执行** | ✅ **新增** |
| | 📁 **任务目录管理** | ✅ **新增** |

---

## 核心流程

### v3.1 全动态流程（推荐）

```
用户输入
    ↓
项目生成
    ↓
定义全局约束
    ↓
任务类型检测 → 复杂度评估
    ↓
上下文预算检查（预留20%余量）
    ↓
角色流程生成（包含模型选择）
    ├─ 动态生成角色（1-7个，根据复杂度）
    ├─ 定义执行顺序（execution_order）
    ├─ 标记可并行角色（parallel_groups）
    └─ 定义输入输出关系（input_from/output_to）
    ↓
【交互式任务分解确认】（多轮对话完善）
    ├─ [Enter] 确认方案
    ├─ m 修改方案（重新生成）
    └─ c 取消
    ↓
【分解结果约束审计】
    ├─ 检查角色职责完整性
    ├─ 检查模型成本合理性
    ├─ 检查上下文预算充足性
    └─ 用户决策（继续/修改/中止）
    ↓
【阶段网关】启动阶段 N
    ↓
【Agent 执行】调用对应模型角色按流程执行
    ↓
【强制审计】自动触发
    ├── 通过（≥85分）→ 【网关】进入阶段 N+1
    └── 未通过
           ↓
      首次未通过 → 【关键节点确认】
           ├── c 继续自动迭代
           ├── f 输入反馈（作为下一轮新约束）
           ├── force 强制通过
           └── abort 中止
           ↓
      自动迭代（直到通过或达到上限）
           ↓
      达到上限 → 【决策界面】用户决策
                   ├── 手动修复 → 重试
                   ├── 放宽约束 → 重试
                   ├── 强制通过 → 继续
                   └── 中止 → 退出
```

---

## 模型体系

### GLM Coding Plan 模型表

| 模型 ID | 定位 | 上下文窗口(输入/输出) | 擅长领域 |
|---------|------|----------------------|---------|
| `glm-5.1` | 旗舰 (推理级) | 200K / 128K | 复杂代码、深度推理、长程Agent、系统架构 |
| `glm-4.7` | 全能主力 | 200K / 128K | 通用编码、多轮对话、工具调用、前端/后端 |
| `glm-4.7-flash` | 轻量开源 | 200K / 128K | 低延迟、轻量Agent、快速实验 |
| `glm-4.7-flashx` | 云端极速 | 200K / 128K | 高并发、生产低延迟、批量任务 |
| `glm-4.6` | 上一代主力 | 200K / 128K | 稳定编码、长上下文 |
| `glm-4.6v` | 多模态编码 | 128K / 128K | 设计图转代码、视觉调试、截图转HTML/CSS |
| `glm-4.5-air` | 超轻量 | 128K / 128K | 极简场景、快速补全 |

### 模型回退链

```
主模型 (GLM) → 备选模型1 (GLM) → 备选模型2 (GLM) → kimi-coding/k2p5 (绝对回退)
```

**规则**: 所有 GLM 模型均失败时，自动回退到 `kimi-coding/k2p5`。

### 角色模型分配

| 角色类型 | 主模型 | 备选模型 | 理由 |
|----------|--------|----------|------|
| 需求分析 | glm-4.7 | glm-5.1, glm-4.7-flash | 全能主力，逻辑推理 |
| 产品经理 | glm-5.1 | glm-4.7, glm-4.7-flash | 深度规划 |
| 架构设计 | glm-5.1 | glm-4.7, glm-4.7-flash | 深度推理，系统规划 |
| UX设计 | glm-4.6v | glm-4.7, glm-5.1 | 多模态能力 |
| 代码开发 | glm-5.1 | glm-4.7, glm-4.7-flash | 代码能力最强 |
| QA测试 | glm-4.7-flash | glm-4.7, glm-4.5-air | 快速细致 |
| 部署运维 | glm-4.7 | glm-4.7-flash, glm-5.1 | 稳定通用 |

---

## 快速开始

### v3.1 动态角色工作流（推荐）

```bash
cd /path/to/your/project

# 运行动态角色工作流
bmad-evo run-v3 "开发用户认证系统" --strict

# 自定义参数（包括最大迭代次数）
bmad-evo run-v3 "开发用户认证系统" \
    --strict \
    --pass-threshold 85 \
    --max-retries 3 \
    --max-iterations 5

# Python API
from agents.workflow_orchestrator_v3_final import WorkflowOrchestratorV3Final

orchestrator = WorkflowOrchestratorV3Final(
    project_path="./my_project",
    interactive=True,
    config={'max_iterations': 5}
)

result = orchestrator.execute_full_workflow("开发用户认证系统")
```

---

## v3.1 新增功能

### 1. 上下文预算管理

- 每个模型预留 20% 上下文窗口余量防止幻觉
- 检查整个工作流的累积上下文是否超限
- 提供超限时的拆分建议

```python
from lib.v3.context_budget import ContextBudgetManager

manager = ContextBudgetManager()
result = manager.check_budget(
    model_id="glm-4.7",
    system_prompt="...",
    context_from_previous="...",
    task_description="..."
)
print(result.sufficient)  # True/False
```

### 2. 交互式任务分解确认

- 角色流程生成后，列出执行方案供用户确认
- 支持多轮对话完善方案
- 默认回车同意

### 3. 分解后约束审计

- 检查角色职责完整性
- 检查模型成本合理性
- 检查上下文预算充足性
- 提醒用户决策

### 4. 多轮迭代执行

- 关键节点确认模式：首次执行后询问用户
- 之后自动迭代直到审计通过或达到上限
- 用户反馈作为下一轮新约束
- 最大迭代次数可配置（默认5次）

### 5. 任务目录管理（新增）

为每个新任务自动生成标准化的目录结构：

```
project_name/
├── tasks/                   # 任务文档
│   ├── requirement.md       # 需求描述
│   ├── design.md            # 设计文档
│   └── assignment.md        # 任务分解和模型指派
├── outputs/                 # 输出文件
│   ├── reports/            # 分析报告
│   ├── code/               # 代码输出
│   └── docs/               # 文档输出
├── .bmad/                  # BMAD-EVO 配置
│   └── versions/           # 版本索引
└── logs/                   # 执行日志
```

详细说明见 [docs/TASK_DIRECTORY.md](docs/TASK_DIRECTORY.md)

---

## 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| **TaskAnalyzer** | `lib/v3/task_analyzer.py` | 任务类型检测、复杂度评估(1-10) |
| **DynamicRoleGenerator** | `lib/v3/role_generator.py` | 动态生成角色、执行顺序、并行组 |
| **ModelRouter** | `lib/v3/model_router.py` | GLM模型智能路由、备选配置 |
| **ContextBudgetManager** | `lib/v3/context_budget.py` | 上下文预算管理、超限检测 ⭐ |
| **ResilientExecutor** | `lib/v3/resilient_executor.py` | 弹性执行、GLM→kimi回退 |
| **TaskDirectoryManager** | `lib/v3/task_directory_manager.py` | 任务目录管理、版本索引 ⭐新增 |
| **WorkflowOrchestratorV3Final** | `agents/workflow_orchestrator_v3_final.py` | v3.1完整流程编排 |

### 复杂度评估标准

| 分数 | 复杂度 | 示例 | 角色数 |
|------|--------|------|--------|
| 1-3 | 简单 | 数据清洗、格式转换 | 1-2 |
| 4-6 | 中等 | API开发、脚本工具 | 2-3 |
| 7-8 | 复杂 | 完整系统、多服务 | 3-5 |
| 9-10 | 极复杂 | 分布式系统、AI平台 | 5-7 |

### 审计维度

| 维度 | 检查内容 | 严重级别 |
|------|---------|---------|
| **边界检查** | 空值检查、范围验证 | HIGH |
| **异常处理** | try-except、超时、重试 | HIGH |
| **代码结构** | 函数长度、文件长度 | MEDIUM |
| **可读性** | 命名、注释、文档 | LOW |
| **安全性** | 密钥、注入、验证 | HIGH |

---

## 版本历史

- **v3.1** (2026-04-06): **GLM Coding Plan 模型体系** + **上下文预算管理** + **交互式任务分解确认** + **分解后约束审计** + **多轮迭代执行** + **kimi-coding/k2p5 绝对回退** + **任务目录管理系统**
- **v3.0** (2026-03-21): **全动态智能生成系统** - 任务分析、动态角色生成、模型路由、零硬编码
- **v2.0 Phase 3** (2026-03-21): Agent 执行层 - 7个预定义角色、多模型调用、上下文传递
- **v2.0 Phase 2** (2026-03-16): 阶段网关、用户决策、工作流编排
- **v2.0 Phase 1** (2026-03-16): 强制约束审计、审计报告、约束模板

---

*BMAD-EVO v3.1 - GLM Coding Plan 驱动的全动态智能多Agent开发框架*
