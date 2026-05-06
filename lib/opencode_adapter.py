# -*- coding: utf-8 -*-
"""
OpenCode Model Adapter

Unified model calling interface for BMAD-EVO.
In OpenCode environment, model calls are handled by the OpenCode agent context.

NOTE: In OpenCode mode, the model is selected by the user in opencode UI.
The model parameter in call_model() is informational only — it cannot
override the user's selection. Fallback logic only applies in CLI mode.
"""

import os
import json
import logging
import subprocess
import tempfile
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

from .config_loader import get_config, get_model_chain_for_component, get_timeout

logger = logging.getLogger(__name__)


@dataclass
class ModelResponse:
    text: str
    model: str
    usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None


class OpenCodeModelAdapter:
    """
    OpenCode model adapter

    In OpenCode environment (OPENCODE env var set), the agent context
    handles model calls directly. The adapter outputs structured prompts
    and the OpenCode runtime processes them.

    Outside OpenCode environment, falls back to opencode CLI if available.
    """

    def _get_absolute_fallback(self) -> str:
        try:
            return get_config()["models"]["absolute_fallback"]
        except Exception:
            return "kimi-coding/k2.6"

    def __init__(self):
        self.in_opencode = "OPENCODE" in os.environ or "OPENCODE_VERSION" in os.environ
        logger.info(f"OpenCodeModelAdapter initialized (in_opencode={self.in_opencode})")

    def call_model(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:
        if timeout is None:
            timeout = get_timeout("opencode_adapter")
        if max_tokens is None:
            max_tokens = get_config()["models"]["call_defaults"]["max_tokens"]
        """
        Call model

        In OpenCode environment: returns the prompt as structured output
        for the OpenCode agent to process with the specified model.

        Outside OpenCode: attempts opencode CLI.
        """
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        if self.in_opencode:
            return self._call_in_opencode_env(model, full_prompt)
        else:
            return self._call_via_cli(model, full_prompt, timeout)

    def _call_in_opencode_env(self, model: str, prompt: str) -> ModelResponse:
        """
        Inside OpenCode environment.

        The OpenCode agent runtime handles model calls.
        We output a structured instruction for the agent to process.
        """
        instruction = (
            f"[BMAD-EVO Model Call]\n"
            f"Model: {model}\n"
            f"Prompt:\n{prompt}"
        )
        return ModelResponse(text=instruction, model=model)

    def _call_via_cli(self, model: str, prompt: str, timeout: int) -> ModelResponse:
        """
        Outside OpenCode environment: try opencode CLI.
        Falls back to absolute fallback model on failure.
        """
        output = self._run_cli(model, prompt, timeout)

        if output is not None:
            return ModelResponse(text=output, model=model)

        abs_fallback = self._get_absolute_fallback()
        if model != abs_fallback:
            logger.info(f"Trying absolute fallback: {abs_fallback}")
            output = self._run_cli(abs_fallback, prompt, timeout)
            if output is not None:
                return ModelResponse(text=output, model=abs_fallback)

        return ModelResponse(text="", model=model, error="All model calls failed")

    def _run_cli(self, model: str, prompt: str, timeout: int) -> Optional[str]:
        """Run opencode CLI for model call"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            cmd = [
                "opencode",
                "--model", model,
                "--task-file", prompt_file,
                "--timeout", str(timeout),
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout + 30
            )

            if result.returncode != 0:
                raise RuntimeError(f"Model call failed: {result.stderr}")

            return result.stdout

        except Exception as e:
            logger.error(f"CLI call failed for {model}: {e}")
            return None
        finally:
            try:
                Path(prompt_file).unlink(missing_ok=True)
            except Exception:
                pass


_model_adapter: Optional[OpenCodeModelAdapter] = None


def get_model_adapter() -> OpenCodeModelAdapter:
    global _model_adapter
    if _model_adapter is None:
        _model_adapter = OpenCodeModelAdapter()
    return _model_adapter


def set_model_adapter(adapter: OpenCodeModelAdapter):
    global _model_adapter
    _model_adapter = adapter


def call_model(
    model: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    timeout: Optional[int] = None,
    max_tokens: Optional[int] = None,
) -> str:
    """Convenience function: call model"""
    adapter = get_model_adapter()
    response = adapter.call_model(model, prompt, system_prompt, timeout, max_tokens)

    if response.error:
        raise RuntimeError(f"Model call failed: {response.error}")

    return response.text


def check_environment() -> Dict[str, Any]:
    """Check OpenCode environment configuration"""
    in_opencode = "OPENCODE" in os.environ or "OPENCODE_VERSION" in os.environ

    opencode_available = False
    try:
        result = subprocess.run(
            ["opencode", "--version"],
            capture_output=True, text=True, timeout=10,
        )
        opencode_available = result.returncode == 0
    except Exception:
        pass

    return {
        "in_opencode_env": in_opencode,
        "opencode_cli_available": opencode_available,
    }
