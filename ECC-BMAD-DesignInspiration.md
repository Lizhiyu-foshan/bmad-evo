# ECC 对 BMAD-EVO 的设计启发

> **文档名称**：ECC-BMAD-DesignInspiration.md  
> **创建时间**：2026-03-21  
> **分析对象**：Everything Claude Code (ECC) - GitHub 7万星项目  
> **目的**：借鉴 ECC 设计思想，为 BMAD-EVO 优化提供参考

---

## 一、ECC 核心架构解析

### 1.1 五大核心模块

| 模块 | 数量 | 核心功能 | 设计思想 |
|------|------|---------|---------|
| **Agents** | 25+ | 专业化子代理分工 | **角色专业化** - 让 AI 分裂成团队 |
| **Skills** | 102+ | 结构化工作流模板 | **流程固化** - 把经验变成可执行指令 |
| **Commands** | 57+ | 斜杠命令快速触发 | **交互简化** - 一行指令启动复杂工作流 |
| **Hooks** | 8-20个事件 | 自动化质量门禁 | **事件驱动** - 在关键点自动拦截/处理 |
| **Rules** | 34+ | 始终遵循的编码规范 | **约束前置** - 让规范成为默认行为 |

### 1.2 关键设计亮点

#### 1.2.1 Instinct（直觉）学习系统
- **观察**：记录用户的编码习惯和项目偏好
- **沉淀**：将高频模式提取为「直觉」规则
- **复用**：下次遇到类似场景自动应用
- **进化**：Skills 执行失败时自动分析、修补、评估

#### 1.2.2 Harness Performance System
- **Token 优化**：模型选择、系统提示精简、后台进程
- **内存持久化**：Hooks 自动保存/加载跨会话上下文
- **验证循环**：Checkpoint vs 持续评估、评分器类型、pass@k 指标
- **并行化**：Git worktrees、cascade 方法、实例扩展

#### 1.2.3 跨工具兼容性
- **AGENTS.md** 作为通用文件（Claude Code、Cursor、Codex、OpenCode 都支持）
- **DRY Adapter 模式**：Cursor 复用 Claude Code 的 Hook 脚本
- **Skills 格式标准化**：YAML frontmatter，跨工具通用

---

## 二、BMAD-EVO vs ECC 对比分析

### 2.1 架构层次对比

| 维度 | BMAD-EVO (当前) | ECC | 差距分析 |
|------|----------------|-----|---------|
| **约束定义** | project-charter.yaml (静态) | Rules + Hooks (动态执行) | ECC 约束可执行，BMAD-EVO 偏文档 |
| **角色分工** | 规划者-调度者-执行者三层 | 25+ 专业化 Agent | ECC 角色更细，覆盖更多场景 |
| **经验固化** | 复盘后人工更新 | Skills + Instinct 自动学习 | ECC 有自动学习机制 |
| **交互方式** | 对话式 + 命令行 | 斜杠命令 + Hooks 自动化 | ECC 交互更高效 |
| **质量门禁** | 阶段检查点 | Hooks 事件驱动 | ECC 门禁更自动化 |
| **跨工具** | OpenClaw 专用 | 4大工具通用 | ECC 生态更广 |

### 2.2 核心机制对比

#### 约束机制
```yaml
# BMAD-EVO (当前) - 声明式
constraints:
  - id: C001
    rule: "函数必须有输入验证"
    severity: HIGH
    # 需要人工检查

# ECC - 可执行式
rules/common/security.md:
  "所有输入必须经过验证，不信任外部数据"
  
hooks/pre-tool-use.json:
  {
    "matcher": "tool == 'Edit' && file_path matches '\\.(py|js)$'",
    "action": "检查输入验证是否存在"
  }
```

#### 学习机制
| BMAD-EVO | ECC |
|---------|-----|
| 项目结束统一复盘 | 会话中实时学习 (Instinct) |
| 人工总结模式 | 自动提取模式 |
| 沉淀到 MEMORY.md | 沉淀为 Skills + Instincts |
| 跨项目复用需人工迁移 | 自动应用学到的模式 |

---

## 三、对 BMAD-EVO 的具体借鉴建议

### 3.1 【P0】引入 Hooks 事件驱动机制

**现状问题**：BMAD-EVO 的阶段检查是显式调用，容易遗漏。

**借鉴 ECC**：
```python
# 在关键事件自动触发检查
HOOKS = {
    "pre_phase_start": ["check_constraints"],
    "post_tool_call": ["validate_output", "update_context"],
    "on_error": ["trigger_reflection"],
    "session_end": ["persist_memory", "extract_patterns"]
}
```

**具体实现**：
1. 在 `.bmad/hooks/` 下定义事件处理器
2. 每个阶段自动触发相关检查
3. 错误时自动触发自反思流程

### 3.2 【P0】Skills 模板化 - 经验固化的最佳实践

**ECC 的 Skills 设计**：
```markdown
---
name: tdd-workflow
triggers: ["/tdd"]
tools: ["Bash", "Read", "Edit"]
---

# TDD 工作流

1. **RED**: 写失败的测试
2. **GREEN**: 实现最小代码
3. **REFACTOR**: 重构改进
4. **VERIFY**: 覆盖率 >= 80%
```

**BMAD-EVO 改造建议**：
```yaml
# .bmad/skills/constraint-check.yaml
name: 约束检查
phase: pre_execution
triggers: ["phase_start"]

workflow:
  1. 加载 project-charter.yaml
  2. 对当前输出执行约束检查
  3. 如果未通过:
     - 生成违规报告
     - 触发自反思流程
     - 阻断进入下一阶段
```

### 3.3 【P1】Instinct 自动学习系统

**ECC 的 Instinct 机制**：
- 观察用户重复提示的模式
- 自动保存为 Skill
- 下次类似场景自动加载

**BMAD-EVO 可借鉴**：
```python
# 在每次会话结束后自动分析
class InstinctLearner:
    def extract_patterns(self, session_log):
        # 1. 识别重复出现的问题
        # 2. 提取解决模式
        # 3. 保存为 Instinct 规则
        # 4. 下次自动应用
```

**应用场景**：
- 你反复要求「检查约束」→ 自动添加 pre_phase 钩子
- 你经常在特定类型项目上添加相同约束 → 沉淀为项目模板

### 3.4 【P1】Commands 快捷命令体系

**借鉴 ECC 的斜杠命令**：
```bash
# 建议为 BMAD-EVO 添加：
/bmad-init          # 初始化项目
/bmad-check         # 执行约束检查
/bmad-reflect       # 触发自反思
/bmad-evolve        # 查看改进建议
/bmad-promote       # 将项目规则提升为全局规则
/bmad-audit         # 生成审计报告
```

### 3.5 【P2】Rules 分层架构

**ECC 的 Rules 结构**：
```
rules/
  common/           # 通用规则（所有项目）
  typescript/       # TypeScript 专用
  python/           # Python 专用
  golang/           # Go 专用
```

**BMAD-EVO 可借鉴**：
```
.bmad/rules/
  common/           # 所有项目通用约束
  web-app/          # Web 应用专用
  cli-tool/         # CLI 工具专用
  data-pipeline/    # 数据管道专用
```

### 3.6 【P2】AGENTS.md 跨工具兼容

**ECC 的 AGENTS.md 被 4 大工具同时支持**：
- Claude Code
- Cursor
- Codex
- OpenCode

**BMAD-EVO 可借鉴**：
- 在项目根目录创建 AGENTS.md
- 定义项目角色和约束
- 即使不用 OpenClaw，其他工具也能读取

---

## 四、具体改造路线图

### Phase 1: Hooks 事件系统（1周）
- [ ] 设计 Hook 事件类型（pre_phase, post_tool, on_error, session_end）
- [ ] 实现 Hook 执行引擎
- [ ] 添加默认 Hooks（约束检查、自反思触发）

### Phase 2: Skills 模板库（1周）
- [ ] 定义 Skills YAML 格式
- [ ] 创建常用 Skills（约束检查、复盘、测试驱动）
- [ ] 实现 Skills 加载和执行机制

### Phase 3: Commands 快捷命令（3天）
- [ ] 实现 /bmad-* 命令体系
- [ ] 集成到 OpenClaw
- [ ] 添加命令补全

### Phase 4: Instinct 学习（2周）
- [ ] 设计模式提取算法
- [ ] 实现 Instinct 存储和应用
- [ ] 添加用户确认机制

---

## 五、与 AGENTS.md 规则的整合建议

将 ECC 的最佳实践整合到现有的 AGENTS.md：

```markdown
### 规则X：Hooks 强制检查
**触发条件**：代码/脚本修改
**执行逻辑**：
1. 修改前自动执行约束检查
2. 未通过则阻断提交
3. 记录到 .learnings/HOOK_VIOLATIONS.md

### 规则Y：Skills 自动加载
**触发条件**：新项目启动
**执行逻辑**：
1. 根据项目类型自动加载对应 Skills
2. 显示已加载的 Skills 列表
3. 用户可通过 /bmad-skills 查看详情
```

---

## 六、总结

**ECC 给 BMAD-EVO 的最大启示**：

1. **从"建议"到"强制"**：约束不只是文档，而是要通过 Hooks 自动化执行
2. **从"人工"到"自动"**：经验固化不应该依赖人工复盘，而要像 Instinct 一样自动学习
3. **从"专用"到"通用"**：通过 AGENTS.md 等通用格式，让框架价值超越单一工具

**下一步行动**：
- 你想先实施哪个 Phase？
- 需要我为某个具体改造写详细设计文档吗？

---

*文档版本：v1.0*  
*状态：待优化*
