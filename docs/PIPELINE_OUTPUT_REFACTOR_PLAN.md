# Pipeline 输出重构计划

## 问题

当前 `pipeline()` 模式把完整分析内容塞进 JSON 字符串字段：
- 几万字的分析报告在 JSON 里失去 Markdown 格式优势
- JSON 膨胀，下游系统解析慢
- 机器要双重解析：JSON → 提取字符串 → 再解析 Markdown
- 没有利用 Markdown 文件天然适合长文本的优势

## 设计原则

**JSON 存元数据，Markdown 存内容，文件路径做桥梁**

```
pipeline 输出目录/
├── pipeline_result.json          ← 结构化元数据（小而精）
├── full_report.md                ← 完整分析报告（大而全）
└── roles/                        ← 各角色独立输出
    ├── 01_geopolitical_analyst.md
    ├── 02_energy_economist.md
    └── 03_risk_manager.md
```

## pipeline_result.json 结构

```json
{
  "task": "分析霍尔木兹海峡封锁对全球原油市场的影响",
  "status": "success",
  "summary": "200字以内的执行摘要",
  "metadata": {
    "complexity": 8,
    "task_type": "geopolitical_analysis",
    "total_roles": 7,
    "completed_roles": 7,
    "needs_data_collection": true,
    "collected_data_sources": ["commodity_prices", "market_indices"],
    "analysis_mode": "complex_thinking_chain",
    "avg_audit_score": 88.5
  },
  "findings": [
    {
      "role": "geopolitical_analyst",
      "title": "地缘政治分析师",
      "key_points": [
        "军事冲突升级概率60%",
        "航运路线受阻将影响全球20%原油运输"
      ],
      "confidence": 0.85,
      "output_file": "roles/01_geopolitical_analyst.md"
    },
    {
      "role": "energy_economist",
      "title": "能源经济学家",
      "key_points": [
        "原油价格短期冲击至$120-150/bbl",
        "长期替代效应将加速新能源转型"
      ],
      "confidence": 0.78,
      "output_file": "roles/02_energy_economist.md"
    }
  ],
  "outputs": {
    "full_report": "full_report.md",
    "role_outputs": {
      "geopolitical_analyst": "roles/01_geopolitical_analyst.md",
      "energy_economist": "roles/02_energy_economist.md",
      "risk_manager": "roles/03_risk_manager.md"
    }
  },
  "collected_data_summary": {
    "sources_accessed": 3,
    "queries_executed": 5,
    "data_freshness": "2026-05-06T15:30:00Z"
  }
}
```

## 改动清单

### 1. output_types.py — PipelineOutput 增加文件路径字段

```python
@dataclass
class PipelineOutput:
    status: str = "success"
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    output_files: Dict[str, str] = field(default_factory=dict)  # 新增：文件路径映射
    output_dir: Optional[str] = None                            # 新增：输出目录
    json_str: str = ""
    error: Optional[str] = None
```

### 2. agents/workflow_orchestrator_v3_final.py — _build_pipeline_output 改为写文件

当前：`summary_parts.append({"role": rn, "summary": output[:500]})`
改为：
- 将每个 role 的完整输出写入 `roles/XX_rolename.md`
- 生成完整报告写入 `full_report.md`
- `_build_pipeline_output()` 返回的 JSON 只包含元数据和文件路径
- 增加 `_save_pipeline_files()` 方法

### 3. api.py — pipeline() 函数适配

- 调用编排器后，读取生成的文件路径
- 构造新的 PipelineOutput（包含文件路径而非内嵌内容）
- `json_str` 只包含元数据 JSON（不含完整报告内容）

### 4. __main__.py — CLI pipeline 子命令适配

- `--output-file` 仍然输出 pipeline_result.json
- `--output` 指定输出目录（包含 md 文件和 json）

### 5. README.md — 更新 Pipeline 文档

## 不改什么

- `analyze()` 模式不变（仍然返回内嵌 Markdown）
- `build()` 模式不变
- 编排器内部流程不变
- 测试适配新增字段即可

## 向后兼容

- `PipelineOutput.analysis` 保留（填充 summary 级别的简短数据）
- `PipelineOutput.json_str` 仍然可用（内容是元数据 JSON）
- 新增 `output_files` 和 `output_dir` 字段，旧代码忽略即可
