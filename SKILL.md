---
name: bmad-evo
description: BMAD-EVO 进化版多Agent开发框架。在BMAD基础上增加约束驱动、决策记录、自反思和复盘优化能力。支持项目全局约束定义、阶段自动检查、违反约束时自反思寻找解决方案、项目结束统一复盘形成可复用模式。v3.0新增全动态智能生成系统，零硬编码规则，模型驱动角色生成。
---

# BMAD-EVO v3.0

**进化版多Agent开发框架** - 约束驱动 + 强制审计 + 阶段拦截 + 用户决策 + 复盘优化 + **全动态角色生成**

## v3.0 功能全景

| 阶段 | 功能 | 状态 |
|------|------|------|
| **Phase 1** | 🔒 强制约束审计 | ✅ 已完成 |
| | 📊 审计报告生成 | ✅ 已完成 |
| | 🎯 约束模板 | ✅ 已完成 |
| **Phase 2** | 🚧 阶段流转拦截 | ✅ 已完成 |
| | 👤 用户决策界面 | ✅ 已完成 |
| | 🔄 工作流编排 | ✅ 已完成 |
| | 🤖 **Agent 执行层** | ✅ 已完成 |
| **Phase 3** | 🧠 **全动态角色生成** | ✅ **已完成** |
| | 📋 任务类型检测 | ✅ **已完成** |
| | 📊 复杂度评估 | ✅ **已完成** |
| | 🎭 动态角色流程 | ✅ **已完成** |
| | 🎯 智能模型路由 | ✅ **已完成** |

---

## 核心流程

### v3.0 全动态流程（推荐）

```
用户输入
    ↓
项目生成
    ↓
定义全局约束
    ↓
任务类型检测 → 复杂度评估
    ↓
角色流程生成（包含模型选择）
    ├─ 动态生成角色（1-7个，根据复杂度）
    ├─ 定义执行顺序（execution_order）
    ├─ 标记可并行角色（parallel_groups）
    └─ 定义输入输出关系（input_from/output_to）
    ↓
【阶段网关】启动阶段 N
    ↓
【Agent 执行】调用对应模型角色按流程执行
    ↓
【强制审计】自动触发
    ├── 通过（≥85分）→ 【网关】进入阶段 N+1
    └── 未通过
           ↓
      第1次重试
           ↓
      第2次重试
           ↓
      第3次重试
           ↓
      仍失败 → 【决策界面】用户决策
                  ├── 手动修复 → 重试
                  ├── 放宽约束 → 重试
                  ├── 强制通过 → 继续
                  └── 中止 → 退出
```

### v2.0 固定角色流程（兼容）

```
项目启动
    ↓
定义全局约束（使用模板或自定义）
    ↓
【阶段网关】启动阶段 N
    ↓
【Agent 执行】调用对应模型角色
    ├── analyst (K2.5) → 需求分析
    ├── pm (GLM-5) → 产品规划  
    ├── architect (K2.5) → 架构设计
    ├── development (K2.5) → 编码开发
    └── qa (Qwen3.5) → 测试审查
    ↓
【强制审计】自动触发
    ├── 通过（≥85分）→ 【网关】进入阶段 N+1
    └── 未通过
           ↓
      第1次重试（K2.5 + 审计反馈）
           ↓
      第2次重试（K2.5 + 审计反馈）
           ↓
      第3次重试（GLM-5 + 审计反馈）
           ↓
      仍失败 → 【决策界面】用户决策
                  ├── 手动修复 → 重试
                  ├── 放宽约束 → 重试
                  ├── 强制通过 → 继续
                  └── 中止 → 退出
```

---

## 快速开始

### v3.0 动态角色工作流（推荐）

```bash
# 进入项目目录
cd /path/to/your/project

# 运行动态角色工作流
bmad-evo run-v3 "开发用户认证系统" --strict

# 自定义参数
bmad-evo run-v3 "开发用户认证系统" \
    --strict \
    --pass-threshold 85 \
    --max-retries 3

# Python API
from agents.workflow_orchestrator_v3_final import WorkflowOrchestratorV3Final

orchestrator = WorkflowOrchestratorV3Final(
    project_path="./my_project",
    interactive=True
)

result = orchestrator.execute_full_workflow(
    "开发用户认证系统"
)
```

### v2.0 固定角色工作流（兼容）

```bash
# 初始化项目
cd /path/to/your/project

# 使用定时任务模板
bmad-evo init --template cron-job

# 或使用API服务模板  
bmad-evo init --template api-service

# 完整工作流（严格模式）
bmad-evo run --strict

# 指定阶段
bmad-evo run --strict --phases development qa

# CI/CD 非交互模式
bmad-evo run --strict --ci

# 本地调试模式（使用模拟输出）
bmad-evo run --strict --mode local

# 真实模型调用模式（需 OpenClaw Gateway 运行）
bmad-evo run --strict --mode openclaw
```

### 3. 独立审计（调试用）

```bash
# 审计代码文件
bmad-evo audit --phase development --file src/main.py

# 查看审计历史
bmad-evo history --limit 10

# 查看决策历史
bmad-evo decision history

# 查看决策统计
bmad-evo decision summary
```

---

## 命令参考

### v3.0 动态工作流命令
| 命令 | 说明 |
|------|------|
| `bmad-evo run-v3 <task>` | 运行动态角色工作流（推荐） |
| `bmad-evo run-v3 <task> --strict` | 严格模式 |
| `bmad-evo run-v3 <task> --pass-threshold 85` | 自定义通过阈值 |
| `bmad-evo run-v3 <task> --max-retries 3` | 自定义重试次数 |

### v2.0 固定角色工作流命令
| 命令 | 说明 |
|------|------|
| `bmad-evo init [--template]` | 初始化项目 |
| `bmad-evo run [--strict] [--phases] [--ci] [--mode]` | 运行工作流（`--mode`: openclaw/local）|
| `bmad-evo workflow status` | 查看工作流状态 |

### 审计命令
| 命令 | 说明 |
|------|------|
| `bmad-evo audit --phase --file` | 审计代码 |
| `bmad-evo history [--limit]` | 审计历史 |
| `bmad-evo check --phase` | 检查阶段状态 |

### 阶段网关命令
| 命令 | 说明 |
|------|------|
| `bmad-evo phase start <name>` | 开始阶段 |
| `bmad-evo phase status` | 阶段状态 |
| `bmad-evo phase decision <name> --choice` | 用户决策 |

### 决策命令
| 命令 | 说明 |
|------|------|
| `bmad-evo decision history` | 决策历史 |
| `bmad-evo decision summary` | 决策统计 |

---

## v3.0 全动态智能生成系统

### 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| **TaskAnalyzer** | `lib/v3/task_analyzer.py` | 任务类型检测、复杂度评估(1-10)、推荐角色数 |
| **DynamicRoleGenerator** | `lib/v3/role_generator.py` | 动态生成角色、定义执行顺序、标记并行组 |
| **ModelRouter** | `lib/v3/model_router.py` | 为每个角色选择最优模型、配置备选模型 |
| **ResilientExecutor** | `lib/v3/resilient_executor.py` | 弹性执行、失败回退、日志记录 |
| **WorkflowOrchestratorV3Final** | `agents/workflow_orchestrator_v3_final.py` | 完整流程编排 |

### 动态角色生成

**输入**: 任务描述  
**输出**: 定制化角色流程

```python
# 简单任务 (复杂度 1-3) → 1-2 角色
task = "清洗CSV文件"
roles: [数据分析师, 开发工程师]

# 中等任务 (复杂度 4-6) → 2-3 角色  
task = "开发REST API"
roles: [需求分析师, 架构师, 开发工程师]

# 复杂任务 (复杂度 7-8) → 3-5 角色
task = "开发电商平台"
roles: [需求分析师, 架构师, 开发工程师, 测试工程师, 运维工程师]

# 极复杂任务 (复杂度 9-10) → 5-7 角色
task = "开发分布式AI系统"
roles: [需求分析师, 系统架构师, 算法工程师, 开发工程师, 测试工程师, 安全工程师, 运维工程师]
```

### 角色流程设计

**RoleDefinition** 包含：
- `name`: 角色标识
- `title`: 显示名称
- `description`: 职责描述
- `responsibilities`: 具体职责列表
- `input_from`: 输入来源角色（前置依赖）
- `output_to`: 输出目标角色（后续角色）
- `can_parallel`: 是否可与其他角色并行
- `estimated_time`: 预计执行时间
- `required_skills`: 所需技能
- `model_requirement`: 对AI模型的能力要求

**RoleFlow** 包含：
- `roles`: 所有角色列表
- `execution_order`: 执行顺序（阶段 N→N+1）
- `parallel_groups`: 可并行执行的组
- `rationale`: 流程设计理由

### 模型智能路由

根据角色职责和任务复杂度选择最优模型：

| 角色类型 | 主模型 | 备选模型 | 理由 |
|----------|--------|----------|------|
| 需求分析 | GLM-5 | Qwen3.5, K2.5 | 强逻辑推理 |
| 架构设计 | K2.5 | GLM-5, Qwen3.5 | 综合能力最强 |
| 代码开发 | K2.5 | Qwen3.5, GLM-5 | 代码能力最强 |
| 测试审查 | Qwen3.5 | K2.5, GLM-5 | 细致审查 |
| 算法设计 | GLM-5 | K2.5 | 数学能力强 |

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
| **边界检查** | 空值检查、范围验证 | 🔴 HIGH |
| **异常处理** | try-except、超时、重试 | 🔴 HIGH |
| **代码结构** | 函数长度、文件长度 | 🟡 MEDIUM |
| **可读性** | 命名、注释、文档 | 🟢 LOW |
| **安全性** | 密钥、注入、验证 | 🔴 HIGH |
| **自定义** | 项目特定约束 | 可配置 |

### 评分规则

- **满分**: 100分
- **通过阈值**: 85分
- **扣分**: HIGH(-15), MEDIUM(-8), LOW(-3)
- **阻断**: 存在HIGH违规即阻断

### 重试策略

| 尝试 | 模型 | 策略 |
|------|------|------|
| 1 | K2.5 | 初始执行 |
| 2 | K2.5 | 审计反馈重试 |
| 3 | GLM-5 | 模型切换重试 |
| 4+ | - | 用户决策 |

---

## 约束定义（project-charter.yaml）

```yaml
project:
  name: "定时任务监控系统"
  vision: "自动检测AI文章处理链路"

constraints:
  boundary_check:
    - check_null: true
    - check_empty: true
  
  exception_handling:
    - check_io: true
    - check_network: true
    - no_bare_except: true
  
  code_structure:
    - max_function_lines: 40
  
  readability:
    - require_docstrings: true
  
  security:
    - check_secrets: true
  
  # 自定义约束
  custom:
    - pattern: "record_message_received"
      must_exist: true
      severity: high
      description: "必须使用消息去重"
```

---

## 用户决策界面

当阶段被阻断时，系统呈现：

```
🚫 PHASE BLOCKED - USER DECISION REQUIRED

Phase: development
Attempt: 3/3 (all retries exhausted)
Audit Score: 72/100 (threshold: 85)

🔴 HIGH PRIORITY VIOLATIONS:
  1. [异常处理] 网络请求缺少异常处理
  2. [边界检查] 函数缺少空值检查

AVAILABLE OPTIONS:

1. 🔧 MANUAL FIX (Recommended)
   - Edit code to fix violations
   - Risk: None

2. 📝 RELAX CONSTRAINTS
   - Temporarily relax constraints
   - Risk: Lower quality bar

3. ⚠️  FORCE PROCEED
   - Accept current quality
   - Risk: Technical debt

4. ❌ ABORT
   - Cancel phase
   - Risk: Lost progress

Enter your choice (1-4):
```

---

## 文件结构

```
.bmad/
├── project-charter.yaml      # 项目章程
├── phase-state.json          # 阶段状态
├── decisions/                # 决策记录
│   └── decision-{phase}-{ts}.json
├── checkpoints/              # 阶段检查点
│   └── {phase}-checkpoint.json
└── logs/                     # 审计日志
    ├── audit-{phase}-{ts}.md
    └── audit-{phase}-{ts}.json
```

---

## 架构组件

```
BMAD-EVO v3.0
│
├── agents/
│   ├── workflow_orchestrator_v3_final.py   # v3.0 完整流程编排 ⭐
│   ├── constraint_auditor.py               # 约束审计
│   ├── phase_gateway.py                    # 阶段网关
│   ├── decision_interface.py               # 决策界面
│   └── workflow_orchestrator.py            # v2.0 工作流编排
│
├── lib/
│   ├── v3/                                 # v3.0 动态系统 ⭐
│   │   ├── task_analyzer.py                # 任务分析器
│   │   ├── role_generator.py               # 角色生成器
│   │   ├── model_router.py                 # 模型路由器
│   │   ├── resilient_executor.py           # 弹性执行器
│   │   └── bmad_evo3.py                    # v3.0 主入口
│   ├── constraint_checker.py               # 检查引擎
│   ├── audit_report.py                     # 报告生成
│   └── agent_executor.py                   # Agent 执行层
│
├── templates/constraints/
│   ├── cron-job.yaml                       # 定时任务模板
│   └── api-service.yaml                    # API服务模板
│
└── bmad-evo                                # CLI入口
```

---

## 与 BMAD 的关系

| 版本 | 特性 |
|------|------|
| BMAD | 多Agent串行协作 |
| BMAD-EVO v1.0 | BMAD + 约束驱动（建议） |
| BMAD-EVO v2.0 | BMAD + **强制审计** + **阶段拦截** + **用户决策** + **Agent执行层** |
| BMAD-EVO v3.0 | v2.0 + **全动态角色生成** + **模型智能路由** + **零硬编码规则** |

---

## 版本历史

- **v2.0 Phase 1** (2026-03-16): 强制约束审计、审计报告、约束模板
- **v2.0 Phase 2** (2026-03-16): 阶段网关、用户决策、工作流编排
- **v2.0 Phase 3** (2026-03-21): Agent 执行层 - 7个预定义角色、多模型调用、上下文传递
- **v3.0** (2026-03-21): **全动态智能生成系统** - 任务分析、动态角色生成、模型路由、零硬编码

---

*BMAD-EVO v3.0 - 全动态智能生成的多Agent开发框架*
