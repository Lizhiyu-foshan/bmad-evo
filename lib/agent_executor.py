"""
BMAD-EVO Agent Executor

Supports two modes:
1. OpenCode mode: call models via opencode adapter (recommended)
2. Local mode: for testing with BMAD_EVO_USE_MOCK=1
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import subprocess
import tempfile
import os

from .config_loader import get_config, get_model_for_component, get_timeout

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    name: str
    model: Optional[str] = None
    description: str = ""
    system_prompt: str = ""
    timeout: Optional[int] = None
    max_tokens: Optional[int] = None

    def get_effective_model(self) -> str:
        if self.model:
            return self.model
        primary, _ = get_model_for_component("agent_execution")
        return primary

    def get_effective_timeout(self) -> int:
        if self.timeout is not None:
            return self.timeout
        return get_timeout("agent_execution")

    def get_effective_max_tokens(self) -> int:
        if self.max_tokens is not None:
            return self.max_tokens
        return get_config()["models"]["call_defaults"]["max_tokens"]


@dataclass
class AgentResult:
    """Agent 执行结果"""

    success: bool
    output: str
    model_used: str
    execution_time: float
    token_usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None


# 预定义角色配置
DEFAULT_AGENTS = {
    "analyst": AgentConfig(
        name="analyst",
        model=None,
        description="需求分析师 - 分析需求并提取关键信息",
        system_prompt="""你是 BMAD-EVO 框架中的需求分析师。
你的职责是：
1. 深入理解用户需求
2. 提取功能性和非功能性需求
3. 识别潜在风险和约束
4. 输出结构化的需求文档

输出格式要求：
- 使用 Markdown 格式
- 包含：需求概述、功能需求、非功能需求、风险分析
- 代码示例使用代码块""",
        timeout=300,
    ),
    "pm": AgentConfig(
        name="pm",
        model=None,
        description="产品经理 - 制定产品规划和里程碑",
        system_prompt="""你是 BMAD-EVO 框架中的产品经理。
你的职责是：
1. 基于需求制定产品规划
2. 设计功能优先级
3. 制定开发里程碑
4. 输出产品规格文档

输出格式要求：
- 使用 Markdown 格式
- 包含：产品愿景、功能列表、优先级、里程碑、验收标准""",
        timeout=300,
    ),
    "architect": AgentConfig(
        name="architect",
        model=None,
        description="架构师 - 设计系统架构和技术选型",
        system_prompt="""你是 BMAD-EVO 框架中的系统架构师。
你的职责是：
1. 设计系统整体架构
2. 选择合适的技术栈
3. 定义模块边界和接口
4. 输出架构设计文档

输出格式要求：
- 使用 Markdown 格式
- 包含：架构概述、技术选型、模块设计、接口定义、数据流
- 使用 Mermaid 图表展示架构""",
        timeout=400,
    ),
    "ux": AgentConfig(
        name="ux",
        model=None,
        description="UX设计师 - 设计用户交互流程",
        system_prompt="""你是 BMAD-EVO 框架中的UX设计师。
你的职责是：
1. 设计用户交互流程
2. 定义界面布局
3. 输出原型设计文档

输出格式要求：
- 使用 Markdown 格式
- 包含：用户流程图、界面结构、交互说明
- 使用 ASCII 或文字描述界面""",
        timeout=300,
    ),
    "development": AgentConfig(
        name="development",
        model=None,
        description="开发工程师 - 编写高质量代码",
        system_prompt="""你是 BMAD-EVO 框架中的开发工程师。
你的职责是：
1. 根据设计文档编写代码
2. 遵循编码规范
3. 添加必要的注释和文档
4. 确保代码可测试

编码规范：
- 函数不超过40行
- 必须有输入验证
- 必须有异常处理
- 禁止裸 except
- 所有函数必须有 docstring

输出格式：
- 直接输出代码
- 使用代码块标记语言
- 最后附上简要说明""",
        timeout=600,
    ),
    "qa": AgentConfig(
        name="qa",
        model=None,
        description="QA工程师 - 测试用例设计和执行",
        system_prompt="""你是 BMAD-EVO 框架中的QA工程师。
你的职责是：
1. 设计测试用例
2. 执行代码审查
3. 输出测试报告

输出格式要求：
- 使用 Markdown 格式
- 包含：测试策略、测试用例、覆盖率分析、问题清单""",
        timeout=400,
    ),
    "deployment": AgentConfig(
        name="deployment",
        model="glm-4.7",
        description="运维工程师 - 部署和发布",
        system_prompt="""你是 BMAD-EVO 框架中的运维工程师。
你的职责是：
1. 设计部署方案
2. 编写部署脚本
3. 配置监控和告警
4. 输出部署文档

输出格式要求：
- 使用 Markdown 格式
- 包含：部署架构、部署步骤、回滚方案、监控配置""",
        timeout=300,
    ),
}


class AgentExecutor:
    """
    Agent 执行器
    负责调用不同模型执行各阶段任务
    """

    def __init__(self, project_path: str, mode: str = "opencode"):
        """
        Args:
            project_path: project path
            mode: execution mode - "opencode" or "local"
        """
        self.project_path = Path(project_path)
        self.mode = mode
        self.agents_dir = self.project_path / ".bmad" / "agents"
        self.agents_dir.mkdir(parents=True, exist_ok=True)

        # 加载自定义配置
        self.config = self._load_config()

        logger.info(f"AgentExecutor initialized (mode: {mode})")

    def _load_config(self) -> Dict[str, Any]:
        """加载 Agent 配置"""
        config_file = self.project_path / ".bmad" / "agent-config.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_agent_config(self, phase: str) -> AgentConfig:
        """获取角色配置"""
        # 优先使用自定义配置
        if phase in self.config.get("agents", {}):
            cfg = self.config["agents"][phase]
            return AgentConfig(**cfg)

        # 使用默认配置
        if phase in DEFAULT_AGENTS:
            return DEFAULT_AGENTS[phase]

        # 通用配置
        return AgentConfig(
            name=phase,
            model=config.get_effective_model(),
            description=f"{phase} 阶段执行者",
            system_prompt=f"你是 BMAD-EVO 框架中的 {phase} 阶段执行者。请根据上下文完成相应任务。",
        )

    def execute(
        self, phase: str, context: str, retry_feedback: Optional[str] = None
    ) -> AgentResult:
        """
        执行 Agent 任务

        Args:
            phase: 阶段名称
            context: 上下文信息（前一阶段的输出）
            retry_feedback: 重试时的审计反馈

        Returns:
            AgentResult: 执行结果
        """
        config = self.get_agent_config(phase)

        logger.info(f"Executing agent: {phase} (model: {config.get_effective_model()})")

        # 构建提示词
        prompt = self._build_prompt(phase, config, context, retry_feedback)

        # 根据模式执行
        if self.mode == "opencode":
            return self._execute_opencode(config, prompt)
        else:
            return self._execute_local(config, prompt)

    def _build_prompt(
        self,
        phase: str,
        config: AgentConfig,
        context: str,
        retry_feedback: Optional[str] = None,
    ) -> str:
        """构建完整提示词"""
        parts = [
            f"# {config.description}",
            "",
            config.system_prompt,
            "",
            "## 上下文信息",
            "```",
            context if context else "（无前序阶段输出）",
            "```",
        ]

        if retry_feedback:
            parts.extend(
                [
                    "",
                    "## 审计反馈（需要修复的问题）",
                    "```",
                    retry_feedback,
                    "```",
                    "",
                    "请根据以上反馈修复问题，然后重新输出。",
                ]
            )

        parts.extend(["", "## 任务", f"请完成 {phase} 阶段的任务，输出结果。"])

        return "\n".join(parts)

    def _execute_opencode(self, config: AgentConfig, prompt: str) -> AgentResult:
        """Execute via OpenCode adapter"""
        import time

        start_time = time.time()

        try:
            from opencode_adapter import call_model
            output = call_model(
                model=config.get_effective_model(),
                prompt=prompt,
                timeout=config.get_effective_timeout(),
                max_tokens=config.get_effective_max_tokens(),
            )

            execution_time = time.time() - start_time

            output_file = self.agents_dir / f"{config.name}_output.txt"
            output_file.write_text(output, encoding="utf-8")

            return AgentResult(
                success=True,
                output=output,
                model_used=config.get_effective_model(),
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"OpenCode execution error: {e}")
            return AgentResult(
                success=False,
                output="",
                model_used=config.get_effective_model(),
                execution_time=execution_time,
                error=str(e),
            )

    def _execute_local(self, config: AgentConfig, prompt: str) -> AgentResult:
        """
        Local mode execution (for testing only)

        WARNING: This method does not generate real AI output. To get real output:
        1. Use mode='opencode' (recommended)
        2. Or set BMAD_EVO_USE_MOCK=1 env var (testing only)
        """
        import time
        import os

        start_time = time.time()

        if os.environ.get("BMAD_EVO_USE_MOCK") == "1":
            logger.warning(
                "BMAD_EVO_USE_MOCK=1 - Using mock output for testing only!"
            )

            mock_file = self.project_path / ".bmad" / f"{config.name}-output.txt"
            if mock_file.exists():
                output = mock_file.read_text(encoding="utf-8")
                execution_time = time.time() - start_time

                logger.info(f"Using mock output from: {mock_file}")

                return AgentResult(
                    success=True,
                    output=output,
                    model_used=f"{config.get_effective_model()}(MOCK-FOR-TESTING)",
                    execution_time=execution_time,
                )

            output = f"""# MOCK OUTPUT - FOR TESTING ONLY

## WARNING
This is a MOCK output generated for testing purposes only.

## Role: {config.description}
## Model: {config.get_effective_model()}
## Timestamp: {datetime.now().isoformat()}

### Prompt Summary (first 200 chars):
```
{prompt[:200]}...
```

### To get real AI output:
1. Use mode='opencode' (recommended)
2. Or implement direct API call in _execute_local()
3. Or set BMAD_EVO_USE_MOCK=1 for testing (current)

---
*This is not real AI output.*
"""

            execution_time = time.time() - start_time

            return AgentResult(
                success=True,
                output=output,
                model_used=f"{config.get_effective_model()}(MOCK-FOR-TESTING)",
                execution_time=execution_time,
            )

        raise RuntimeError(
            f"Local mode does not have a real AI implementation.\n\n"
            f"Role: {config.name}\n"
            f"Model: {config.get_effective_model()}\n\n"
            f"To execute this agent, you have 3 options:\n"
            f"1. Use mode='opencode' (recommended)\n"
            f"2. Implement direct API call in _execute_local() method\n"
            f"3. Set BMAD_EVO_USE_MOCK=1 for testing only\n\n"
            f"Current mode: {self.mode}"
        )

    def save_config(self, custom_agents: Dict[str, Dict[str, Any]]):
        """保存自定义 Agent 配置"""
        config_file = self.project_path / ".bmad" / "agent-config.json"

        config = {"agents": custom_agents, "updated_at": datetime.now().isoformat()}

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        logger.info(f"Agent config saved: {config_file}")

    def list_agents(self) -> Dict[str, AgentConfig]:
        """列出所有可用 Agent"""
        return {k: v for k, v in DEFAULT_AGENTS.items()}


# 便捷函数
def execute_agent(
    phase: str,
    project_path: str,
    context: str = "",
    retry_feedback: Optional[str] = None,
    mode: str = "opencode",
) -> AgentResult:
    """
    便捷函数：执行单个 Agent

    Args:
        phase: 阶段名称
        project_path: 项目路径
        context: 上下文
        retry_feedback: 重试反馈
        mode: 执行模式

    Returns:
        AgentResult
    """
    executor = AgentExecutor(project_path, mode=mode)
    return executor.execute(phase, context, retry_feedback)


if __name__ == "__main__":
    # 测试
    import argparse

    parser = argparse.ArgumentParser(description="BMAD-EVO Agent Executor")
    parser.add_argument("phase", help="Phase to execute")
    parser.add_argument("--project", default=".", help="Project path")
    parser.add_argument("--context", default="", help="Context from previous phase")
    parser.add_argument(
        "--mode", default="opencode", choices=["opencode", "local"], help="Execution mode"
    )
    parser.add_argument("--list", action="store_true", help="List available agents")

    args = parser.parse_args()

    if args.list:
        executor = AgentExecutor(args.project)
        agents = executor.list_agents()
        print("Available Agents:")
        for name, config in agents.items():
            print(f"  - {name}: {config.description} (model: {config.get_effective_model()})")
    else:
        result = execute_agent(args.phase, args.project, args.context, mode=args.mode)
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
