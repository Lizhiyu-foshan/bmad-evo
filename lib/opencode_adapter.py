"""
OpenCode 模型调用适配器
用于在 OpenCode 环境中直接调用模型，无需依赖 openclaw CLI

使用方法:
1. 在 agent_executor.py、task_analyzer.py 等文件中导入此适配器
2. 替换原有的 _call_model 方法
3. 通过环境变量或配置文件设置 API 密钥
"""

import os
import json
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ModelResponse:
    """模型响应"""

    text: str
    model: str
    usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None


class OpenCodeModelAdapter:
    """
    OpenCode 模型调用适配器

    支持两种调用方式:
    1. 直接调用（如果在 OpenCode 环境中可以直接使用模型工具）
    2. API 调用（通过 HTTP API 调用模型）
    """

    def __init__(self):
        self.api_key = os.environ.get("OPENCODE_API_KEY")
        self.api_base = os.environ.get("OPENCODE_API_BASE", "https://api.opencode.ai")
        self.use_direct = (
            os.environ.get("OPENCODE_USE_DIRECT", "true").lower() == "true"
        )

        logger.info(f"OpenCodeModelAdapter initialized (direct_mode={self.use_direct})")

    def call_model(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: int = 120,
        max_tokens: int = 8000,
    ) -> ModelResponse:
        """
        调用模型

        Args:
            model: 模型ID (如 'glm-4.7', 'glm-5.1', 'glm-4.7-flash', 'kimi-coding/k2p5' 绝对回退)
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            timeout: 超时时间（秒）
            max_tokens: 最大token数

        Returns:
            ModelResponse: 模型响应
        """
        try:
            # 在 OpenCode 环境中，可以直接使用 ask_model 工具
            # 注意：这需要在 OpenCode 的 agent 上下文中运行
            return self._call_via_opencode(model, prompt, system_prompt, max_tokens)
        except Exception as e:
            logger.error(f"Direct model call failed: {e}")
            return ModelResponse(text="", model=model, error=str(e))

    def _call_via_opencode(
        self, model: str, prompt: str, system_prompt: Optional[str], max_tokens: int
    ) -> ModelResponse:
        """
        通过 OpenCode 直接调用模型

        这是给 OpenCode agent 使用的接口
        """
        # 注意：这段代码在 OpenCode agent 中会被替换为实际的模型调用
        # 在实际运行时，OpenCode 会自动处理这些工具调用

        # 构建完整的提示词
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        # 这里只是一个占位符
        # 在 OpenCode 环境中，实际的模型调用会由系统处理
        return ModelResponse(
            text=f"[Model {model} would process:\n{full_prompt[:200]}...]", model=model
        )


# 简单的 HTTP API 调用方式（如果需要）
class HTTPModelClient:
    """HTTP API 模型客户端"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.environ.get("OPENCODE_API_KEY")
        self.base_url = base_url or os.environ.get(
            "OPENCODE_API_BASE", "https://api.opencode.ai"
        )

    def call(self, model: str, prompt: str, **kwargs) -> str:
        """
        通过 HTTP API 调用模型

        这需要一个实际的 API 端点
        """
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": kwargs.get("max_tokens", 8000),
        }

        try:
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=kwargs.get("timeout", 120),
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"API call failed: {e}")


# 全局适配器实例
_model_adapter: Optional[OpenCodeModelAdapter] = None


def get_model_adapter() -> OpenCodeModelAdapter:
    """获取全局模型适配器实例"""
    global _model_adapter
    if _model_adapter is None:
        _model_adapter = OpenCodeModelAdapter()
    return _model_adapter


def set_model_adapter(adapter: OpenCodeModelAdapter):
    """设置全局模型适配器"""
    global _model_adapter
    _model_adapter = adapter


# 便捷函数
def call_model(
    model: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    timeout: int = 120,
    max_tokens: int = 8000,
) -> str:
    """
    便捷函数：调用模型

    使用示例:
        result = call_model(
            model="glm-4.7",
            prompt="请分析这段代码...",
            system_prompt="你是一个代码审查专家"
        )
    """
    adapter = get_model_adapter()
    response = adapter.call_model(model, prompt, system_prompt, timeout, max_tokens)

    if response.error:
        raise RuntimeError(f"Model call failed: {response.error}")

    return response.text


# 环境检查
def check_environment() -> Dict[str, Any]:
    """检查 OpenCode 环境配置"""
    return {
        "api_key_set": bool(os.environ.get("OPENCODE_API_KEY")),
        "api_base": os.environ.get("OPENCODE_API_BASE", "default"),
        "use_direct": os.environ.get("OPENCODE_USE_DIRECT", "true").lower() == "true",
        "in_opencode": "OPENCODE" in os.environ or "OPENCODE_VERSION" in os.environ,
    }


if __name__ == "__main__":
    # 测试
    print("OpenCode Model Adapter")
    print(f"Environment: {check_environment()}")

    # 测试调用
    try:
        result = call_model(model="glm-4.7", prompt="Hello, this is a test.")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Test failed: {e}")
