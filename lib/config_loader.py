"""
BMAD-EVO Config Loader
统一配置加载器 — 从 config/bmad.json 读取所有配置

加载优先级:
1. config/bmad.json（用户自定义）
2. 内置默认值（DEFAULTS 字典）
3. 环境变量覆盖（BMAD_PRIMARY_MODEL 等）
"""

import json
import os
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).parent.parent / "config"
_CONFIG_FILE = _CONFIG_DIR / "bmad.json"

_ROLE_OUTPUT_FORMAT_MAP = {
    "analysis_terminal": "markdown_report",
    "pipeline_tool": "structured_json",
    "analysis_and_code": "mixed",
}

_LOADED_CONFIG: Optional[Dict[str, Any]] = None

DEFAULTS: Dict[str, Any] = {
    "system": {
        "role": "analysis_terminal",
        "output_format": "auto",
        "language": "auto",
        "interactive": True,
    },
    "models": {
        "primary": "glm-5.1",
        "secondary": "glm-4.7",
        "absolute_fallback": "kimi-coding/k2.6",
        "fallback_chain": ["glm-5.1", "glm-4.7", "kimi-coding/k2.6"],
        "overrides": {},
        "context_windows": {
            "glm-5.1": {"input": 200000, "output": 128000},
            "glm-4.7": {"input": 200000, "output": 128000},
            "glm-4.7-flash": {"input": 200000, "output": 128000},
            "glm-4.6": {"input": 200000, "output": 128000},
            "glm-4.6v": {"input": 128000, "output": 128000},
            "kimi-coding/k2.6": {"input": 200000, "output": 128000},
        },
        "context_windows_defaults": {"input": 100000, "output": 32000},
        "call_defaults": {"max_tokens": 8000, "timeout": 120},
    },
    "execution": {
        "mode": "opencode",
        "cli": {"command": "opencode", "extra_buffer_timeout": 30, "version_check_timeout": 10},
    },
    "analysis": {
        "mode": "auto",
        "thinking_chain_complexity_threshold": 7,
        "thinking_chain": {
            "incremental_data_collection": True,
            "bidirectional_feedback": True,
            "self_reflection": True,
            "max_re_executions_per_role": 2,
            "max_reflection_rounds": 2,
            "data_collection_timeout": 120,
            "feedback_timeout": 120,
            "reflection_timeout": 180,
        },
        "complexity_to_roles": {
            "simple": {"max_complexity": 3, "min_roles": 1, "max_roles": 2},
            "medium": {"max_complexity": 6, "min_roles": 3, "max_roles": 4},
            "complex": {"max_complexity": 8, "min_roles": 5, "max_roles": 6},
            "very_complex": {"max_complexity": 10, "min_roles": 7, "max_roles": 8},
        },
    },
    "quality": {
        "pass_threshold": 85,
        "force_proceed_min_score": 70,
        "relax_step": 10,
        "relax_floor": 60,
        "max_iterations": 5,
        "max_retries": 3,
        "context_headroom_ratio": 0.20,
        "output_validation": {
            "min_word_count": 5000,
            "recommended_word_count": 10000,
            "bonus_word_count": 15000,
            "min_h2_sections": 5,
            "min_h3_sections": 10,
            "min_section_chars": 200,
            "min_data_points": 20,
            "min_analysis_keywords": 5,
            "min_recommendation_keywords": 5,
            "min_content_density": 0.6,
            "min_avg_line_length": 50,
            "score_penalties": {"CRITICAL": 20, "HIGH": 10, "MEDIUM": 5, "LOW": 2},
        },
    },
    "paths": {
        "analysis_output_dir": "real_multi_agent_analysis",
        "pipeline_output_method": "file",
        "pipeline_output_file": "analysis_output.json",
        "analysis_doc_subdir": "docs",
        "code_output_subdir": "src",
        "bmad_dir": ".bmad",
        "versions_dir": ".bmad/versions",
        "decisions_dir": ".bmad/decisions",
        "checkpoints_dir": ".bmad/checkpoints",
        "reports_dir": ".bmad/reports",
        "constraints_dir": ".bmad/constraints",
        "logs_dir": ".bmad/logs",
        "default_project_path": "./analysis_output",
    },
    "code_constraints": {
        "max_function_lines": 50,
        "max_file_lines": 500,
        "min_variable_length": 2,
        "check_null": True,
        "check_empty": True,
        "check_io": True,
        "check_network": True,
        "no_bare_except": True,
        "check_secrets": True,
        "no_hardcoded_keys": True,
    },
    "timeouts": {
        "task_analyzer": 120,
        "role_generator": 180,
        "model_router": 120,
        "agent_execution": 600,
        "resilient_executor": 600,
        "opencode_adapter": 120,
    },
    "version": "4.0.0",
    "config_schema_version": 1,
}


def _deep_merge(base: Dict, override: Dict) -> Dict:
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def load_config(config_path: Optional[str] = None, force_reload: bool = False) -> Dict[str, Any]:
    global _LOADED_CONFIG

    if _LOADED_CONFIG is not None and not force_reload:
        return _LOADED_CONFIG

    path = Path(config_path) if config_path else _CONFIG_FILE

    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            config = _deep_merge(DEFAULTS, file_config)
            logger.info(f"Config loaded from {path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {path}: {e}, using defaults")
            config = deepcopy(DEFAULTS)
    else:
        config = deepcopy(DEFAULTS)
        logger.info("No config file found, using built-in defaults")

    config = _apply_env_overrides(config)

    _LOADED_CONFIG = config
    return config


def reload_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    return load_config(config_path, force_reload=True)


def get_config() -> Dict[str, Any]:
    return load_config()


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    env_map = {
        "BMAD_PRIMARY_MODEL": ("models", "primary"),
        "BMAD_SECONDARY_MODEL": ("models", "secondary"),
        "BMAD_ABSOLUTE_FALLBACK": ("models", "absolute_fallback"),
        "BMAD_EXECUTION_MODE": ("execution", "mode"),
        "BMAD_ANALYSIS_MODE": ("analysis", "mode"),
        "BMAD_SYSTEM_ROLE": ("system", "role"),
        "BMAD_LANGUAGE": ("system", "language"),
        "BMAD_INTERACTIVE": ("system", "interactive"),
    }
    for env_var, path in env_map.items():
        value = os.environ.get(env_var)
        if value is not None:
            section, key = path
            if value.lower() in ("true", "1", "yes"):
                value = True
            elif value.lower() in ("false", "0", "no"):
                value = False
            config[section][key] = value
            logger.info(f"Config override from env: {env_var} -> {'.'.join(path)}")

    custom_chain = os.environ.get("BMAD_FALLBACK_CHAIN")
    if custom_chain:
        config["models"]["fallback_chain"] = [m.strip() for m in custom_chain.split(",")]

    return config


def get_model_for_component(component: str) -> Tuple[str, str]:
    """Get primary/fallback model for a component.

    NOTE: In OpenCode mode, these values are read but not used to control
    actual model selection — the user chooses the model in opencode.
    Only effective in CLI/API mode.
    """
    config = get_config()
    overrides = config["models"].get("overrides", {})
    if component in overrides:
        ov = overrides[component]
        return ov.get("primary", config["models"]["primary"]), ov.get("fallback", config["models"]["secondary"])
    return config["models"]["primary"], config["models"]["secondary"]


def get_model_chain_for_component(component: str) -> List[str]:
    config = get_config()
    primary, fallback = get_model_for_component(component)
    absolute = config["models"]["absolute_fallback"]
    chain = [primary]
    if fallback != primary:
        chain.append(fallback)
    if absolute not in chain:
        chain.append(absolute)
    return chain


def get_effective_output_format(config: Optional[Dict] = None) -> str:
    if config is None:
        config = get_config()
    fmt = config["system"]["output_format"]
    if fmt == "auto":
        return _ROLE_OUTPUT_FORMAT_MAP.get(config["system"]["role"], "markdown_report")
    return fmt


def get_timeout(component: str) -> int:
    config = get_config()
    return config["timeouts"].get(component, config["models"]["call_defaults"]["timeout"])


def get_context_window(model_id: str) -> Tuple[int, int]:
    config = get_config()
    windows = config["models"]["context_windows"]
    defaults = config["models"]["context_windows_defaults"]
    if model_id in windows:
        w = windows[model_id]
        return w["input"], w["output"]
    return defaults["input"], defaults["output"]


def get_quality_threshold(key: str, default: Any = None) -> Any:
    config = get_config()
    return config["quality"].get(key, default)


def get_max_retries(component: str, default: int = 3) -> int:
    config = get_config()
    retries = config["models"]["call_defaults"].get("max_retries", default)
    return retries


def get_output_validation_config() -> Dict[str, Any]:
    config = get_config()
    return config["quality"]["output_validation"]


def get_thinking_chain_config() -> Dict[str, Any]:
    config = get_config()
    return config["analysis"]["thinking_chain"]


def get_path(key: str) -> str:
    config = get_config()
    return config["paths"].get(key, "")


def get_complexity_to_roles() -> Dict[str, Dict]:
    config = get_config()
    return config["analysis"]["complexity_to_roles"]


def determine_analysis_mode(complexity_score: int) -> str:
    config = get_config()
    mode_setting = config["analysis"]["mode"]
    if mode_setting == "auto":
        threshold = config["analysis"]["thinking_chain_complexity_threshold"]
        return "complex_thinking_chain" if complexity_score >= threshold else "simple"
    return mode_setting


def determine_output_strategy() -> Dict[str, Any]:
    config = get_config()
    role = config["system"]["role"]
    output_format = get_effective_output_format(config)

    strategy = {
        "role": role,
        "output_format": output_format,
        "language": config["system"]["language"],
    }

    if role == "analysis_terminal":
        strategy["output_dir"] = config["paths"]["analysis_output_dir"]
        strategy["interactive"] = config["system"]["interactive"]
    elif role == "pipeline_tool":
        method = config["paths"]["pipeline_output_method"]
        strategy["pipeline_method"] = method
        if method == "file":
            strategy["output_file"] = config["paths"]["pipeline_output_file"]
    elif role == "analysis_and_code":
        strategy["doc_subdir"] = config["paths"]["analysis_doc_subdir"]
        strategy["code_subdir"] = config["paths"]["code_output_subdir"]
        strategy["interactive"] = True

    return strategy
