"""
BMAD-EVO v4.1 - 类型化输出

三种模式的返回类型:
- AnalysisReport: 终端分析报告 (markdown)
- PipelineOutput: Pipeline 节点输出 (JSON元数据 + Markdown文件)
- BuildResult: 分析+编码输出 (docs + code)
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AnalysisReport:
    """终端分析报告 — analyze() 的返回类型"""

    markdown: str
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    role_outputs: Dict[str, str] = field(default_factory=dict)
    collected_data: Dict[str, str] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PipelineOutput:
    """Pipeline 节点输出 — pipeline() 的返回类型

    设计: JSON 存元数据（小而精），Markdown 存内容（大而全），文件路径做桥梁。
    """

    status: str = "success"
    summary: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    output_files: Dict[str, str] = field(default_factory=dict)
    output_dir: Optional[str] = None
    json_str: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)

    def get_metadata_json(self, indent: int = 2) -> str:
        d = {
            "status": self.status,
            "summary": self.summary,
            "metadata": self.metadata,
            "findings": self.findings,
            "output_files": self.output_files,
        }
        if self.error:
            d["error"] = self.error
        return json.dumps(d, indent=indent, ensure_ascii=False, default=str)


@dataclass
class BuildResult:
    """分析+编码输出 — build() 的返回类型"""

    analysis: str = ""
    code_files: Dict[str, str] = field(default_factory=dict)
    test_files: Dict[str, str] = field(default_factory=dict)
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
