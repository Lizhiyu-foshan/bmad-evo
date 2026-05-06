---
description: |
  BMAD-EVO multi-agent analysis framework.
  Use this skill when the user wants to:
  - Analyze a complex topic with multiple expert perspectives (use "analyze")
  - Generate structured analysis data for pipeline consumption (use "pipeline")
  - Build a small application from requirements (use "build")
---

# BMAD-EVO v4.0 Skill

Three modes available:

## Analyze — Deep Analysis Report

Trigger: user asks to analyze, evaluate, assess, or research a topic.

```
python -m bmad_evo analyze "TASK_DESCRIPTION" --output ./output_dir
```

Options:
- `--no-data` — skip real-time data collection
- `--non-interactive` — run without user confirmation
- `--json` — also output structured JSON
- `--config CONFIG_FILE` — custom config
- `--pass-threshold N` — audit score threshold (default 85)
- `--max-iterations N` — max retries per phase (default 5)

Output: Markdown report in `output_dir/`.

## Pipeline — Structured JSON for Downstream

Trigger: user needs analysis output as JSON for integration with other tools.

```
python -m bmad_evo pipeline --input task.json --output-file result.json
```

Options:
- `--no-data` — skip data collection
- `--output-dir DIR` — working directory

Output: JSON with structure:
```json
{
  "analysis": {
    "summary": "...",
    "findings": [{"role": "...", "summary": "..."}],
    "role_outputs": {"role_name": "..."}
  },
  "metadata": {"complexity": 8, "status": "success"},
  "status": "success"
}
```

## Build — Analysis + Code Generation

Trigger: user asks to build, develop, or create a tool/application.

```
python -m bmad_evo build "Build a CSV data cleaning tool" --lang python --output ./my_project
```

Options:
- `--lang LANGUAGE` — target language (python, javascript, typescript, go, rust)
- `--non-interactive` — run without confirmation

Output: Analysis docs + generated code files in `output_dir/src/`.

## Python API

```python
from api import analyze, pipeline, build

report = analyze("Analyze oil market impact")
result = pipeline({"description": "Evaluate risk", "context": {...}})
app = build("Build a REST API for inventory management")
```

## Notes

- Framework auto-selects analysis mode by complexity: simple tasks use sequential execution, complex tasks (complexity >= 7) use thinking chain with data collection, feedback loops, and self-reflection.
- All parameters configured in `config/bmad.json`. No hardcoded values.
- Data collection uses dynamic URL construction based on query keywords.
