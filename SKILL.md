---
name: bmad-evo
description: BMAD-EVO 进化版多Agent开发框架。在BMAD基础上增加约束驱动、决策记录、自反思和复盘优化能力。支持项目全局约束定义、阶段自动检查、违反约束时自反思寻找解决方案、项目结束统一复盘形成可复用模式。
---

# BMAD-EVO v2.0

**进化版多Agent开发框架** - 约束驱动 + 强制审计 + 阶段拦截 + 用户决策 + 复盘优化

## v2.0 功能全景

| 阶段 | 功能 | 状态 |
|------|------|------|
| **Phase 1** | 🔒 强制约束审计 | ✅ 已完成 |
| | 📊 审计报告生成 | ✅ 已完成 |
| | 🎯 约束模板 | ✅ 已完成 |
| **Phase 2** | 🚧 阶段流转拦截 | ✅ 已完成 |
| | 👤 用户决策界面 | ✅ 已完成 |
| | 🔄 工作流编排 | ✅ 已完成 |
| | 🤖 **Agent 执行层** | ✅ **已完成** |

---

## 核心流程（v2.0 完整版）

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

### 1. 初始化项目

```bash
cd /path/to/your/project

# 使用定时任务模板
bmad-evo init --template cron-job

# 或使用API服务模板  
bmad-evo init --template api-service
```

### 2. 运行工作流（推荐）

```bash
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

### 项目命令
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

## Agent 执行层

BMAD-EVO v2.0 内置 **7 个预定义角色**，每个角色对应不同的模型和职责：

| 角色 | 模型 | 职责 | 系统提示词 |
|------|------|------|-----------|
| `analyst` | K2.5 | 需求分析师 | 分析需求、提取关键信息、识别风险 |
| `pm` | GLM-5 | 产品经理 | 制定规划、设计优先级、里程碑 |
| `architect` | K2.5 | 架构师 | 系统设计、技术选型、模块边界 |
| `ux` | GLM-5 | UX设计师 | 交互流程、界面布局 |
| `development` | K2.5 | 开发工程师 | 编码实现、遵循约束规范 |
| `qa` | Qwen3.5 | QA工程师 | 测试设计、代码审查 |
| `deployment` | K2.5 | 运维工程师 | 部署方案、监控配置 |

### 上下文传递

各阶段自动传递上下文，形成完整的工作流：

```
analyst 输出 → pm 输入 → architect 输入 → development 输入 → qa 输入
```

### 执行模式

| 模式 | 说明 | 使用场景 |
|------|------|---------|
| `local` | 本地模拟模式，使用预置输出或模拟响应 | 调试、测试 |
| `openclaw` | 真实模型调用，通过 `openclaw sessions spawn` | 生产环境 |

### 自定义配置

创建 `.bmad/agent-config.json` 自定义角色配置：

```json
{
  "agents": {
    "development": {
      "name": "development",
      "model": "kimi-coding/k2p5",
      "timeout": 600,
      "system_prompt": "自定义系统提示词..."
    }
  }
}
```

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
BMAD-EVO v2.0
│
├── agents/
│   ├── constraint_auditor.py      # 约束审计
│   ├── phase_gateway.py           # 阶段网关 ⭐ Phase 2
│   ├── decision_interface.py      # 决策界面 ⭐ Phase 2
│   └── workflow_orchestrator.py   # 工作流编排 ⭐ Phase 2
│
├── lib/
│   ├── constraint_checker.py      # 检查引擎
│   ├── audit_report.py            # 报告生成
│   └── agent_executor.py          # Agent 执行层 ⭐ 新增
│
├── templates/constraints/
│   ├── cron-job.yaml              # 定时任务模板
│   └── api-service.yaml           # API服务模板
│
└── bmad-evo                       # CLI入口
```

---

## 与 BMAD 的关系

| 版本 | 特性 |
|------|------|
| BMAD | 多Agent串行协作 |
| BMAD-EVO v1.0 | BMAD + 约束驱动（建议） |
| BMAD-EVO v2.0 | BMAD + **强制审计** + **阶段拦截** + **用户决策** + **Agent执行层** |

---

## 版本历史

- **v2.0 Phase 1** (2026-03-16): 强制约束审计、审计报告、约束模板
- **v2.0 Phase 2** (2026-03-16): 阶段网关、用户决策、工作流编排
- **v2.0 Phase 3** (2026-03-21): **Agent 执行层** - 7个预定义角色、多模型调用、上下文传递

---

*BMAD-EVO v2.0 - 强制约束驱动的多Agent开发框架*
