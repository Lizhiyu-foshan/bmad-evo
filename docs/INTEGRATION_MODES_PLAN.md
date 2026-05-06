# BMAD-EVO 集成模式重构计划

## 问题

当前 BMAD-EVO 有三种使用场景，但只有一个入口 `execute_full_workflow()`，
`system.role` 配置存在于 JSON 中但无人调用，切换模式只能手工改配置文件。

## 三种使用场景

| 模式 | 调用者 | 输入 | 输出 | 交互 | 典型用途 |
|------|--------|------|------|------|----------|
| **分析报告** | 终端用户 | 任务描述文本 | Markdown 报告文件 | 可交互 | 市场分析、风险评估 |
| **Pipeline 节点** | 上游系统 | 结构化任务 JSON | 结构化分析 JSON | 无交互 | 作为 Pipeline 的一环 |
| **分析+编码** | 开发者 | 需求描述 | 分析文档 + 代码 | 可交互 | 快速开发小型应用 |

## 设计原则

1. **入口即模式** — 调用哪个函数就决定了模式，不需要配置文件
2. **类型化输出** — 每种模式返回不同的类型化结果，不是泛化 Dict
3. **零配置调用** — 外部系统 import 后直接调用，不需要读 JSON
4. **向后兼容** — `execute_full_workflow()` 保留为默认（分析报告模式）

## 新架构

```
bmad_evo/                          # 顶层包（新）
├── __init__.py                    # 公共 API 入口
├── analyze(task, **options)       # → AnalysisReport
├── pipeline(task, **options)      # → PipelineOutput  
├── build(task, **options)         # → BuildResult
│
├── lib/                           # 现有核心引擎（不动）
│   ├── config_loader.py
│   ├── v3/  v4/  ...
│
├── agents/                        # 现有编排器（不动）
│   ├── workflow_orchestrator_v3_final.py
│
└── config/
    └── bmad.json                  # 保留默认值，但不再是唯一控制方式
```

## 公共 API（3 个入口函数）

### 1. `analyze()` — 分析报告模式

```python
from bmad_evo import analyze

report = analyze(
    task="分析2026年霍尔木兹海峡封锁对全球原油市场的影响",
    interactive=True,              # 是否交互式确认
    enable_data_collection=True,   # 是否采集实时数据
    output_dir="./my_analysis",    # 输出目录
)
# report: AnalysisReport
# report.markdown       → 完整报告文本
# report.metadata       → {"complexity": 8, "roles": 7, ...}
# report.role_outputs   → {"role_a": "...", "role_b": "..."}
# report.file_path      → Path("./my_analysis/report.md")
```

调用方式：
- Python: `from bmad_evo import analyze`
- CLI: `python -m bmad_evo analyze "任务描述" --interactive`
- OpenCode Skill: 在 SKILL.md 中描述，用户说"分析XXX"时触发

### 2. `pipeline()` — Pipeline 节点模式

```python
from bmad_evo import pipeline

result = pipeline(
    task={
        "description": "评估供应链风险",
        "context": {...},           # 上游 Pipeline 传入的结构化数据
        "requirements": [...],      # 分析要求
    },
    output_format="json",          # 固定 json
    enable_data_collection=True,
)
# result: PipelineOutput
# result.analysis     → {"summary": "...", "findings": [...], "data": {...}}
# result.json_str     → JSON 字符串，可直接传给下游
# result.metadata     → {"roles": [...], "confidence": 0.85}
# result.status       → "success" | "partial" | "failed"
```

调用方式：
- Python: `from bmad_evo import pipeline`
- CLI: `python -m bmad_evo pipeline --input task.json --output result.json`
- 外部系统集成: `subprocess.run(["python", "-m", "bmad_evo", "pipeline", "--input", "task.json"])`

### 3. `build()` — 分析+编码模式

```python
from bmad_evo import build

result = build(
    task="开发一个CSV数据清洗工具，支持去重、格式标准化、缺失值填充",
    interactive=True,
    output_dir="./my_project",
    code_language="python",
)
# result: BuildResult
# result.analysis      → 分析文档（需求分析 + 技术方案）
# result.code_files    → {"main.py": "...", "utils.py": "...", "README.md": "..."}
# result.test_files    → {"test_main.py": "..."}
# result.file_path     → Path("./my_project/")
```

调用方式：
- Python: `from bmad_evo import build`
- CLI: `python -m bmad_evo build "开发XXX工具" --lang python`
- OpenCode Skill: 用户说"开发XXX"时触发

## 实现步骤

### Phase 1: 类型化输出 + API 入口

1. 新建 `bmad_evo/types.py` — 定义 `AnalysisReport`, `PipelineOutput`, `BuildResult` 数据类
2. 新建 `bmad_evo/__init__.py` — 导出 `analyze()`, `pipeline()`, `build()`
3. 新建 `bmad_evo/api.py` — 三个入口函数的实现，内部调用现有编排器

### Phase 2: 编排器适配

4. `WorkflowOrchestratorV3Final` 增加构造参数 `mode="analyze"|"pipeline"|"build"`
5. 根据 mode:
   - `analyze`: 现有行为（markdown 报告 + 交互）
   - `pipeline`: 禁用交互，输出 JSON，跳过用户确认步骤
   - `build`: 分析完成后增加代码生成阶段
6. `_generate_final_report()` 根据 mode 输出不同格式

### Phase 3: CLI 子命令

7. `__main__.py` 支持 `python -m bmad_evo analyze|pipeline|build` 子命令
8. 每个子命令有自己的参数集

### Phase 4: OpenCode Skill 集成

9. 更新 `SKILL.md` 描述三种触发方式
10. 每种模式映射到不同的 skill 命令

## 关键决策

### 不改什么
- 现有编排器内部流程（步骤 1-7）不动
- `config/bmad.json` 保留作为默认值
- `config_loader.py` 不动
- 所有 v3/v4 引擎代码不动

### 改什么
- 编排器构造函数增加 `mode` 参数
- `_generate_final_report()` 根据 mode 分支输出
- Pipeline 模式跳过交互步骤（`_step56_interactive_plan_confirmation` 等）
- 新增 3 个文件作为公共 API 层

### `system.role` 配置怎么处理
- **保留**，但降级为"默认模式"
- 如果代码中通过 `analyze()` / `pipeline()` / `build()` 显式指定了模式，覆盖 `system.role`
- 如果直接调用 `execute_full_workflow()`（向后兼容），从 `system.role` 读取默认模式

## 调用关系

```
外部调用者
    │
    ├── bmad_evo.analyze(task, **kw)     → AnalysisReport
    ├── bmad_evo.pipeline(task, **kw)    → PipelineOutput
    ├── bmad_evo.build(task, **kw)       → BuildResult
    │
    └── CLI: python -m bmad_evo <command> <args>
              │
              └── bmad_evo.api.py
                   │
                   └── WorkflowOrchestratorV3Final(mode=...)
                         │
                         └── 现有内部流程（不动）
```
