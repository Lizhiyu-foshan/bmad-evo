"""
BMAD-EVO v4.0 - Public API

Three entry points:
  analyze()   → AnalysisReport    Terminal analysis, markdown output
  pipeline()  → PipelineOutput    Pipeline integration, JSON output
  build()     → BuildResult       Analysis + code generation

All three share the same engine, differ only in output format and behavior.
"""

import json
import logging
import sys
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent


def _ensure_sys_path():
    root = str(_PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def _run_workflow(
    task: str,
    mode: str,
    project_path: Optional[str] = None,
    interactive: bool = True,
    enable_data_collection: bool = True,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    _ensure_sys_path()

    if project_path is None:
        project_path = str(_PROJECT_ROOT / "analysis_output")

    Path(project_path).mkdir(parents=True, exist_ok=True)

    from agents.workflow_orchestrator_v3_final import WorkflowOrchestratorV3Final

    effective_config = dict(config or {})

    orchestrator = WorkflowOrchestratorV3Final(
        project_path=project_path,
        interactive=interactive and mode != "pipeline",
        config=effective_config,
        mode=mode,
    )

    return orchestrator.execute_full_workflow(task)


def analyze(
    task: str,
    project_path: Optional[str] = None,
    interactive: bool = True,
    enable_data_collection: bool = True,
    output_dir: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> "AnalysisReport":
    """
    Terminal analysis mode — returns a rich markdown report.

    Usage:
        from bmad_evo.api import analyze
        report = analyze("Analyze the impact of ...")
        print(report.markdown)
    """
    from output_types import AnalysisReport

    try:
        result = _run_workflow(
            task=task,
            mode="analyze",
            project_path=output_dir or project_path,
            interactive=interactive,
            enable_data_collection=enable_data_collection,
            config=config,
        )

        markdown = _extract_markdown_report(result)
        file_path = _find_report_file(result)

        return AnalysisReport(
            markdown=markdown,
            file_path=file_path,
            metadata=_extract_metadata(result),
            role_outputs=result.get("role_outputs", {}),
            collected_data=result.get("collected_data", {}),
            success=result.get("success", False),
        )
    except Exception as e:
        logger.error(f"analyze() failed: {e}")
        return AnalysisReport(
            markdown="",
            success=False,
            error=str(e),
        )


def pipeline(
    task: Union[str, Dict[str, Any]],
    project_path: Optional[str] = None,
    enable_data_collection: bool = True,
    config: Optional[Dict[str, Any]] = None,
) -> "PipelineOutput":
    """
    Pipeline integration mode — returns structured JSON for downstream systems.

    Usage:
        from bmad_evo.api import pipeline
        result = pipeline({"description": "Evaluate supply chain risk", "context": {...}})
        downstream_system.process(result.json_str)

    Args:
        task: Either a task description string or a structured dict with
              keys like "description", "context", "requirements".
    """
    from output_types import PipelineOutput

    task_str = task if isinstance(task, str) else json.dumps(task, ensure_ascii=False)

    try:
        result = _run_workflow(
            task=task_str,
            mode="pipeline",
            project_path=project_path,
            interactive=False,
            enable_data_collection=enable_data_collection,
            config=config,
        )

        pipeline_data = result.get("pipeline_output", {})

        po = PipelineOutput(
            status=pipeline_data.get("status", "unknown"),
            summary=pipeline_data.get("summary", ""),
            metadata=pipeline_data.get("metadata", {}),
            findings=pipeline_data.get("findings", []),
            output_files=pipeline_data.get("outputs", {}),
            output_dir=pipeline_data.get("output_dir"),
        )
        po.json_str = po.get_metadata_json()

        return po
    except Exception as e:
        logger.error(f"pipeline() failed: {e}")
        return PipelineOutput(
            status="failed",
            error=str(e),
        )


def build(
    task: str,
    project_path: Optional[str] = None,
    interactive: bool = True,
    output_dir: Optional[str] = None,
    code_language: str = "python",
    config: Optional[Dict[str, Any]] = None,
) -> "BuildResult":
    """
    Analysis + code generation mode.

    Usage:
        from bmad_evo.api import build
        result = build("Build a CSV data cleaning tool")
        for filename, content in result.code_files.items():
            print(f"Generated: {filename}")
    """
    from output_types import BuildResult

    try:
        result = _run_workflow(
            task=task,
            mode="build",
            project_path=output_dir or project_path,
            interactive=interactive,
            config=config,
        )

        role_outputs = result.get("role_outputs", {})
        code_files = {}
        test_files = {}
        analysis_parts = []

        for role_name, output in role_outputs.items():
            analysis_parts.append(f"## {role_name}\n{output}")
            _extract_code_blocks(output, code_files, test_files, code_language)

        build_dir = output_dir or project_path
        if build_dir and code_files:
            _write_code_files(build_dir, code_files, test_files)

        return BuildResult(
            analysis="\n\n".join(analysis_parts),
            code_files=code_files,
            test_files=test_files,
            file_path=build_dir,
            metadata=_extract_metadata(result),
            success=result.get("success", False),
        )
    except Exception as e:
        logger.error(f"build() failed: {e}")
        return BuildResult(
            success=False,
            error=str(e),
        )


def _extract_markdown_report(result: Dict[str, Any]) -> str:
    role_outputs = result.get("role_outputs", {})
    if not role_outputs:
        return ""
    parts = []
    for name, output in role_outputs.items():
        parts.append(output)
    return "\n\n---\n\n".join(parts)


def _find_report_file(result: Dict[str, Any]) -> Optional[str]:
    return None


def _extract_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "total_phases": result.get("total_phases", 0),
        "completed_phases": result.get("completed_phases", 0),
        "success": result.get("success", False),
        "mode": result.get("mode", "unknown"),
    }


def _extract_code_blocks(
    text: str, code_files: Dict[str, str], test_files: Dict[str, str], language: str
):
    import re

    pattern = r"```(?:\w+)?\s*\n(.*?)```"
    blocks = re.findall(pattern, text, re.DOTALL)

    for i, block in enumerate(blocks):
        block = block.strip()
        if len(block) < 20:
            continue

        filename = _guess_filename(text, block, i, language)
        if "test" in filename.lower():
            test_files[filename] = block
        else:
            code_files[filename] = block


def _guess_filename(context: str, block: str, index: int, language: str) -> str:
    import re

    patterns = [
        r"(?:file|filename|save.to|write.to)[=:]\s*[`\"']?([^\s`\"':]+)",
        r"###?\s+(?:file|文件)[：:]\s*(\S+)",
    ]
    for p in patterns:
        m = re.search(p, context, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    ext_map = {"python": "py", "javascript": "js", "typescript": "ts", "go": "go", "rust": "rs"}
    ext = ext_map.get(language, "py")

    if "import unittest" in block or "import pytest" in block or "def test_" in block:
        return f"test_module_{index}.{ext}"
    if "def " in block or "class " in block:
        return f"module_{index}.{ext}"
    return f"file_{index}.{ext}"


def _write_code_files(base_dir: str, code_files: Dict[str, str], test_files: Dict[str, str]):
    base = Path(base_dir)
    src_dir = base / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in code_files.items():
        (src_dir / filename).write_text(content, encoding="utf-8")

    if test_files:
        test_dir = base / "tests"
        test_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in test_files.items():
            (test_dir / filename).write_text(content, encoding="utf-8")
