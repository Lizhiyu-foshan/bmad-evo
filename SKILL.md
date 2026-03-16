---
name: bmad-evo
description: BMAD-EVO 进化版多Agent开发框架。在BMAD基础上增加约束驱动、决策记录、自反思和复盘优化能力。支持项目全局约束定义、阶段自动检查、违反约束时自反思寻找解决方案、项目结束统一复盘形成可复用模式。
---

# BMAD-EVO v2.0

**进化版多Agent开发框架** - 约束驱动 + 强制审计 + 决策记录 + 复盘优化

## v2.0 新增（Phase 1 已完成）

🔒 **强制约束审计** - 约束不满足则阻断阶段流转，自动重试（最多3次），第3次失败切换GLM-5
📊 **审计报告** - 生成详细的Markdown审计报告和JSON日志
🎯 **约束模板** - 预置cron-job、api-service等场景模板
📈 **历史追踪** - 保存历次审计结果，支持质量趋势分析

---

## 核心流程（v2.0）

```
项目启动
    ↓
定义全局约束（使用模板或自定义）
    ↓
阶段N执行（K2.5）
    ↓
强制约束审计（自动触发）
    ├── 通过（≥85分）→ 进入阶段N+1
    └── 未通过
           ↓
      第1次重试（K2.5 + 审计反馈）
           ↓
      第2次重试（K2.5 + 审计反馈）
           ↓
      第3次重试（GLM-5 + 审计反馈）  ← 模型切换
           ↓
      仍失败 → 暂停，用户决策
```

---

## 快速开始

### 1. 初始化项目（使用约束模板）

```bash
# 进入项目目录
cd /path/to/your/project

# 使用定时任务模板初始化
bmad-evo init --template cron-job

# 或使用API服务模板
bmad-evo init --template api-service
```

### 2. 单命令审计（独立使用）

```bash
# 审计代码文件
bmad-evo audit --phase development --file src/main.py

# 审计标准输入
cat code.py | bmad-evo audit --phase development

# 查看审计历史
bmad-evo history --limit 10

# 检查是否可以进入下一阶段
bmad-evo check --phase development
```

### 3. 完整流程（自动审计）

```bash
# 执行完整流程（每个阶段后自动审计）
bmad-evo run --strict-mode
```

---

## 约束检查机制（v2.0 强化版）

### 审计维度

| 维度 | 检查内容 | 严重级别 |
|------|---------|---------|
| **边界检查** | 空值检查、范围验证、空集合处理 | 🔴 HIGH |
| **异常处理** | try-except块、具体异常类型、网络超时 | 🔴 HIGH |
| **代码结构** | 函数长度、文件长度、模块化 | 🟡 MEDIUM |
| **可读性** | 变量命名、注释、文档字符串 | 🟢 LOW |
| **安全性** | 硬编码密钥、注入攻击、输入验证 | 🔴 HIGH |
| **自定义** | 项目特定约束（YAML配置） | 可配置 |

### 评分规则

- **满分**: 100分
- **通过阈值**: 85分
- **扣分**:
  - HIGH violation: -15分
  - MEDIUM violation: -8分
  - LOW violation: -3分
- **阻断条件**: 存在HIGH级别违规，即使总分≥85也阻断

### 重试策略

| 尝试 | 模型 | 策略 |
|------|------|------|
| 1 | K2.5 | 初始执行 |
| 2 | K2.5 | 携带审计反馈重试 |
| 3 | GLM-5 | 切换模型，不同思路 |
| 4+ | - | 暂停，用户决策 |

---

## 约束定义（project-charter.yaml）

```yaml
project:
  name: "定时任务监控系统"
  vision: "自动检测AI文章处理链路健康状态"

constraints:
  # 边界检查
  boundary_check:
    - check_null: true
    - check_empty: true
  
  # 异常处理（定时任务关键）
  exception_handling:
    - check_io: true
    - check_network: true
    - no_bare_except: true
    - require_finally: true
  
  # 代码结构
  code_structure:
    - max_function_lines: 40
    - max_file_lines: 400
  
  # 可读性
  readability:
    - require_docstrings: true
    - min_variable_length: 3
  
  # 安全性
  security:
    - check_secrets: true
    - validate_inputs: true
  
  # 自定义约束（OpenClaw定时任务特有）
  custom:
    - pattern: "record_message_received"
      must_exist: true
      severity: high
      description: "必须使用消息去重机制"
      suggestion: "参考 feishu_receive_dedup 模块"
```

---

## 文件结构

```
.bmad/
├── project-charter.yaml      # 项目章程（含约束定义）
├── decisions/                # 决策记录
├── checkpoints/              # 阶段检查点
│   └── development-checkpoint.json
├── logs/                     # 审计日志（新增）
│   ├── audit-development-20260316_102030.md
│   ├── audit-development-20260316_102030.json
│   └── audit-development-20260316_102500.md
└── retrospective.md          # 复盘报告
```

---

## 审计报告示例

审计后自动生成 `.bmad/logs/audit-{phase}-{timestamp}.md`：

```markdown
# BMAD-EVO 约束审计报告

**审计时间**: 2026-03-16 10:20:30
**阶段**: development
**尝试次数**: 1
**审计结果**: ❌ 未通过
**得分**: 72/100 (阈值: 85)

## 摘要

审计未通过 (得分: 72/100，阈值: 85)。发现问题: 2个高优先级, 1个中优先级, 0个低优先级。请修复高优先级问题后重试。

## 违规项详情

### 🔴 高优先级 (必须修复)

1. **异常处理**
   - **问题**: 网络请求缺少异常处理
   - **证据**: `发现模式: requests\.(get|post)...`
   - **建议**: 添加try-except块捕获具体异常(如requests.Timeout)

2. **边界检查**
   - **问题**: 函数缺少输入参数为空值的检查
   - **证据**: `函数定义: def fetch_data(url):...`
   - **建议**: 添加 if url is None: raise ValueError(...)

## 下一步行动

1. **自动重试**：修复高优先级问题后自动重新审计
2. **手动修复**：根据违规项详情手动修改代码
3. **调整约束**：如果约束设定过严，可修改约束配置
4. **强制通过**：不推荐，除非明确接受质量风险
```

---

## 与 BMAD 的关系

| 版本 | 特性 |
|------|------|
| BMAD | 多Agent串行协作 |
| BMAD-EVO v1.0 | BMAD + 约束驱动（建议性质） |
| **BMAD-EVO v2.0** | BMAD + **强制约束审计** + 决策记录 + 复盘优化 |

---

## Phase 2 计划（开发中）

- [ ] 阶段流转自动拦截
- [ ] 用户交互决策界面
- [ ] 模式库（跨项目约束复用）
- [ ] 多模型配置（角色级模型映射）

---

*BMAD-EVO v2.0 - Phase 1 已完成（强制约束审计）*
