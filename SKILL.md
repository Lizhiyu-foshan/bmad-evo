---
name: bmad-evo
description: BMAD-EVO v4.0 多Agent深度分析框架。三种集成模式: analyze(报告) / pipeline(JSON) / build(编码)。支持思考链引擎、增量数据采集、双向反馈、自我反思。所有参数通过 config/bmad.json 配置。
---

# BMAD-EVO v4.0

**多Agent深度分析框架** — 三种集成模式 + 思考链引擎 + 全动态角色生成

## 三种调用方式

### Python 库
```python
from api import analyze, pipeline, build

report = analyze("分析XXX")           # → AnalysisReport (Markdown)
result = pipeline({"description": "..."})  # → PipelineOutput (JSON)
app = build("开发XXX工具")            # → BuildResult (代码)
```

### CLI
```bash
python -m bmad_evo analyze "任务描述" --output ./report
python -m bmad_evo pipeline --input task.json --output-file result.json
python -m bmad_evo build "开发XXX" --lang python --output ./project
```

### OpenCode Skill
在 `.opencode/skills/bmad-evo.md` 中定义触发规则。

## 核心流程

```
用户输入 → 任务分析(复杂度1-10 + 是否需要数据采集)
  ↓
[复杂度 < 7] → v3.1 单向顺序执行
[复杂度 ≥ 7] → v4.0 思考链 (增量采集 + 双向反馈 + 自我反思)
  ↓
约束审计(≥85分) → 按模式输出
```

## v4.0 功能

| 功能 | 说明 |
|------|------|
| 增量数据采集 | 任务分析器决定是否需要，DataCollector 动态构建 URL |
| 双向反馈 | 后续角色向前序角色发送修正反馈 |
| 自我反思 | 评估整体报告质量，触发重新分析 |
| 统一配置 | config/bmad.json + Python 参数覆盖 |
| 三种模式 | analyze / pipeline / build，入口即模式 |
