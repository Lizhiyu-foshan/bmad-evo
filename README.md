# BMAD-EVO v4.0

**多Agent深度分析框架** — 支持三种集成模式

BMAD-EVO 是一个基于约束驱动的多Agent智能分析框架，支持深度分析、Pipeline集成和快速应用构建。通过统一配置管理、思考链引擎（增量数据采集+双向反馈+自我反思）和全动态角色生成，适应从简单到极复杂的各类分析任务。

## 三种调用模式

| 模式 | 用途 | 输出 | 调用方式 |
|------|------|------|---------|
| **analyze** | 终端分析报告 | Markdown 报告 | Python / CLI / OpenCode Skill |
| **pipeline** | Pipeline 集成 | 结构化 JSON | Python / CLI |
| **build** | 分析+编码 | 分析文档 + 代码 | Python / CLI / OpenCode Skill |

## 快速开始

### 1. Python 库调用

```python
from api import analyze, pipeline, build

# 分析报告 — 返回 AnalysisReport
report = analyze("分析霍尔木兹海峡封锁对全球原油市场的影响")
print(report.markdown)                  # 完整 Markdown 报告
print(report.metadata["complexity"])    # 复杂度评分
print(report.role_outputs)              # 各角色输出

# Pipeline — 返回 PipelineOutput
result = pipeline({
    "description": "评估供应链风险",
    "context": {"region": "asia", "commodity": "semiconductor"},
})
downstream_system.process(result.json_str)  # JSON 字符串传给下游

# 构建 — 返回 BuildResult
app = build("开发CSV数据清洗工具，支持去重和缺失值填充", output_dir="./my_project")
for filename, content in app.code_files.items():
    print(f"Generated: {filename}")
```

### 2. CLI 命令行

```bash
# 分析报告
python -m bmad_evo analyze "分析全球能源转型的地缘政治风险" --output ./report

# Pipeline（从JSON读取任务，输出JSON）
python -m bmad_evo pipeline --input task.json --output-file result.json

# 构建
python -m bmad_evo build "开发REST API" --lang python --output ./my_project

# 通用选项
python -m bmad_evo analyze "..." --no-data          # 禁用数据采集
python -m bmad_evo analyze "..." --non-interactive   # 非交互模式
python -m bmad_evo analyze "..." --config custom.json # 自定义配置
python -m bmad_evo analyze "..." --pass-threshold 90 # 审计阈值
```

### 3. OpenCode Skill

在 OpenCode TUI 中直接用自然语言触发。已配置在 `.opencode/skills/bmad-evo.md`：

- **"分析XXX"** → 自动触发 analyze 模式
- **"生成pipeline分析XXX"** → 自动触发 pipeline 模式
- **"开发/构建XXX"** → 自动触发 build 模式

也可在 OpenCode 项目级或系统级配置 Skill：
- 项目级: `.opencode/skills/bmad-evo.md`
- 系统级: `~/.config/opencode/skills/bmad-evo.md`

## 核心特性

### 全动态智能生成
- 零硬编码规则，完全由模型驱动
- 动态角色生成和任务分解（1-8个角色）
- 智能模型路由和任务调度

### 思考链引擎 (v4.0)
- **增量数据采集**: 根据任务分析动态决定是否需要，每个角色按需收集补充数据
- **双向反馈**: 后续角色向前序角色发送修正反馈
- **自我反思**: 评估输出质量并触发重新执行
- 自动按复杂度选择模式: 简单任务走 v3.1 单向流，复杂任务走 v4.0 思考链

### 约束驱动开发
- 任务约束定义和验证
- 上下文预算管理（预留20%余量防止幻觉）
- 输出验证和质量保证

### 统一配置管理
- 所有参数集中在 `config/bmad.json`
- 环境变量覆盖支持 CI/CD
- Python API 参数覆盖配置文件（无需手工改 JSON）

## Pipeline 集成

当作为 Pipeline 节点使用时，BMAD-EVO 输出标准化的 JSON：

```python
from api import pipeline

result = pipeline(task="评估半导体供应链风险")

# 输出结构
result.analysis     # {"summary": "...", "findings": [...], "role_outputs": {...}}
result.json_str     # 完整 JSON 字符串
result.metadata     # {"complexity": 8, "status": "success", "needs_data_collection": true}
result.status       # "success" | "partial" | "failed"
```

Pipeline 模式特点：
- **非交互** — 跳过所有用户确认步骤
- **JSON 输出** — 结构化数据供下游系统消费
- **确定性** — 相同任务产生相同结构的输出

## 返回类型

```python
from output_types import AnalysisReport, PipelineOutput, BuildResult

# AnalysisReport
report.markdown        # str: 完整 Markdown 报告
report.file_path       # Optional[str]: 报告文件路径
report.metadata        # dict: 复杂度、角色数等
report.role_outputs    # dict: {role_name: output}
report.collected_data  # dict: {role_name: collected_text}
report.success         # bool

# PipelineOutput
result.analysis        # dict: 结构化分析结果
result.json_str        # str: JSON 字符串
result.metadata        # dict: 元数据
result.status          # str: "success" | "partial" | "failed"

# BuildResult
result.analysis        # str: 分析文档
result.code_files      # dict: {filename: content}
result.test_files      # dict: {filename: content}
result.file_path       # Optional[str]: 输出目录
result.success         # bool
```

## 工作流程

```
用户输入 (analyze / pipeline / build)
    ↓
项目生成 → 全局约束定义
    ↓
任务分析（类型检测 + 复杂度评估 + 是否需要数据采集）
    ↓
上下文预算检查
    ↓
动态角色生成 + 模型路由
    ↓
[复杂度 < 7] → v3.1 单向顺序执行
[复杂度 ≥ 7] → v4.0 思考链执行
    │              ├── 增量数据采集（按需）
    │              ├── 双向反馈传递
    │              └── 自我反思循环
    ↓
约束审计（≥85分通过）
    ↓
根据模式输出:
  analyze → Markdown 报告
  pipeline → 结构化 JSON
  build → 分析文档 + 代码文件
```

## 项目结构

```
bmad-evo/
├── __main__.py                  # CLI 入口 (python -m bmad_evo)
├── api.py                       # 公共 API (analyze, pipeline, build)
├── output_types.py              # 类型化输出定义
├── config/
│   └── bmad.json                # 统一配置文件
├── lib/
│   ├── config_loader.py         # 配置加载器
│   ├── opencode_adapter.py      # 模型调用适配器
│   ├── agent_executor.py        # Agent 执行器
│   ├── constraint_checker.py    # 约束检查器
│   ├── v3/                      # v3.1 引擎
│   └── v4/                      # v4.0 思考链引擎
│       ├── thinking_chain.py    # 思考链核心
│       └── data_collector.py    # 增量数据采集
├── agents/
│   └── workflow_orchestrator_v3_final.py  # 工作流编排器
├── .opencode/skills/
│   └── bmad-evo.md              # OpenCode Skill 定义
├── tests/
├── docs/
└── examples/
```

## 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| **API** | `api.py` | 三种模式入口 (analyze/pipeline/build) |
| **CLI** | `__main__.py` | 命令行接口 |
| **WorkflowOrchestrator** | `agents/workflow_orchestrator_v3_final.py` | 全流程编排 |
| **TaskAnalyzer** | `lib/v3/task_analyzer.py` | 任务分析 + 是否需要数据采集 |
| **DynamicRoleGenerator** | `lib/v3/role_generator.py` | 动态角色生成 |
| **ThinkingChainExecutor** | `lib/v4/thinking_chain.py` | 思考链引擎 |
| **DataCollector** | `lib/v4/data_collector.py` | 动态URL数据采集 |
| **ConfigLoader** | `lib/config_loader.py` | 统一配置管理 |

## 配置参考

配置文件 `config/bmad.json` 提供默认值，可通过 Python API 参数或 CLI 参数覆盖，无需手工修改 JSON。

### 关键配置项

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `quality.pass_threshold` | `85` | 审计通过阈值 |
| `quality.max_iterations` | `5` | 最大迭代轮数 |
| `analysis.thinking_chain_complexity_threshold` | `7` | 触发思考链的复杂度阈值 |
| `analysis.thinking_chain.max_re_executions_per_role` | `2` | 每角色最大重新执行次数 |
| `analysis.thinking_chain.max_reflection_rounds` | `2` | 最大反思轮数 |

## 测试

```bash
python -m pytest tests/ -v
```

## 版本历史

- **v4.0** (2026-05-06): 三种集成模式 API + CLI + OpenCode Skill + 思考链引擎 + 增量数据采集
- **v3.1** (2026-04-06): GLM模型体系 + 上下文预算 + 交互式确认
- **v3.0** (2026-03-21): 全动态智能生成系统
- **v2.0** (2026-03-16): 阶段网关 + 约束审计 + Agent执行层

## 许可证

MIT License

## 联系方式

- 作者: Lizhiyu-foshan
- 项目主页: https://github.com/Lizhiyu-foshan/bmad-evo
