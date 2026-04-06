"""
BMAD-EVO Agent Executor
提供真实的 Agent 调用能力，支持多模型角色执行

支持两种模式：
1. OpenClaw 模式：通过 sessions_spawn 调用远程 Agent
2. 本地模式：直接调用本地模型 API（fallback）
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

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent 配置"""

    name: str
    model: str
    description: str
    system_prompt: str
    timeout: int = 300  # 5分钟默认超时
    max_tokens: int = 8000


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
        model="glm-4.7",
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
        model="glm-5.1",
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
        model="glm-5.1",
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
        model="glm-4.6v",
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
        model="glm-5.1",
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
        model="glm-4.7-flash",
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

    def __init__(self, project_path: str, mode: str = "openclaw"):
        """
        Args:
            project_path: 项目路径
            mode: 执行模式 - "openclaw" 或 "local"
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
            model="glm-4.7",
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

        logger.info(f"Executing agent: {phase} (model: {config.model})")

        # 构建提示词
        prompt = self._build_prompt(phase, config, context, retry_feedback)

        # 根据模式执行
        if self.mode == "openclaw":
            return self._execute_openclaw(config, prompt)
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

    def _execute_openclaw(self, config: AgentConfig, prompt: str) -> AgentResult:
        """通过 OpenClaw sessions_spawn 执行"""
        import time

        start_time = time.time()

        try:
            task_file = self._create_openclaw_task_file(prompt, config)
            self._verify_openclaw_available()
            cmd = self._build_openclaw_command(prompt, config)

            logger.info(f"Executing: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout + 30,
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                return self._handle_openclaw_success(
                    result.stdout, config, execution_time
                )
            else:
                return self._handle_openclaw_failure(result, config, execution_time)

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            logger.error(f"OpenClaw execution timeout after {config.timeout}s")
            return AgentResult(
                success=False,
                output="",
                model_used=config.model,
                execution_time=execution_time,
                error=f"Timeout after {config.timeout}s",
            )
        except RuntimeError:
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"OpenClaw execution error: {e}")
            return AgentResult(
                success=False,
                output="",
                model_used=config.model,
                execution_time=execution_time,
                error=str(e),
            )

    def _create_openclaw_task_file(self, prompt: str, config: AgentConfig) -> Path:
        """创建 OpenClaw 任务文件"""
        task_file = (
            self.agents_dir
            / f"{config.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        task_data = {
            "task": prompt,
            "model": config.model,
            "agent_id": f"bmad-{config.name}",
            "timeout": config.timeout,
            "max_tokens": config.max_tokens,
        }

        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(task_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Task saved to: {task_file}")
        return task_file

    def _verify_openclaw_available(self):
        """验证 OpenClaw CLI 是否可用"""
        result = subprocess.run(["which", "openclaw"], capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                "OpenClaw CLI not found. Cannot execute agent in 'openclaw' mode.\n"
                "Please ensure:\n"
                "1. OpenClaw is installed and 'openclaw' command is in PATH\n"
                "2. Or explicitly use mode='local' for testing (not recommended for production)\n"
                "3. Or implement a real AI client (e.g., direct API call) instead of mock"
            )

    def _build_openclaw_command(self, prompt: str, config: AgentConfig) -> List[str]:
        """构建 OpenClaw 命令"""
        return [
            "openclaw",
            "sessions",
            "spawn",
            "--task",
            prompt,
            "--model",
            config.model,
            "--agent-id",
            f"bmad-{config.name}",
            "--timeout",
            str(config.timeout),
            "--cleanup",
            "keep",
        ]

    def _handle_openclaw_success(
        self, output: str, config: AgentConfig, execution_time: float
    ) -> AgentResult:
        """处理 OpenClaw 执行成功"""
        output_file = self.agents_dir / f"{config.name}_output.txt"
        output_file.write_text(output, encoding="utf-8")

        return AgentResult(
            success=True,
            output=output,
            model_used=config.model,
            execution_time=execution_time,
        )

    def _handle_openclaw_failure(
        self,
        result: subprocess.CompletedProcess,
        config: AgentConfig,
        execution_time: float,
    ) -> AgentResult:
        """处理 OpenClaw 执行失败"""
        error_msg = result.stderr or "Unknown error"
        logger.error(f"OpenClaw execution failed: {error_msg}")

        return AgentResult(
            success=False,
            output="",
            model_used=config.model,
            execution_time=execution_time,
            error=error_msg,
        )

    def _execute_local(self, config: AgentConfig, prompt: str) -> AgentResult:
        """
        本地模式执行（仅用于测试或作为真实API调用的模板）

        WARNING: 此方法不再生成模拟数据。要实现真实的本地执行，请：
        1. 使用 OpenClaw 模式（推荐）
        2. 或直接调用模型API（需实现）
        3. 或设置 BMAD_EVO_USE_MOCK=1 环境变量（仅测试，会生成警告日志）
        """
        import time
        import os

        start_time = time.time()

        # 检查是否显式启用mock模式（仅测试用途）
        if os.environ.get("BMAD_EVO_USE_MOCK") == "1":
            logger.warning(
                "⚠️  BMAD_EVO_USE_MOCK=1 - Using mock output for testing only!"
            )

            # 检查是否有预定义的模拟输出文件
            mock_file = self.project_path / ".bmad" / f"{config.name}-output.txt"
            if mock_file.exists():
                output = mock_file.read_text(encoding="utf-8")
                execution_time = time.time() - start_time

                logger.info(f"Using mock output from: {mock_file}")

                return AgentResult(
                    success=True,
                    output=output,
                    model_used=f"{config.model}(MOCK-FOR-TESTING)",
                    execution_time=execution_time,
                )

            # 没有预定义文件时，生成带警告的mock输出
            output = f"""# MOCK OUTPUT - FOR TESTING ONLY

## ⚠️  WARNING
This is a MOCK output generated for testing purposes only.
DO NOT use this in production.

## Role: {config.description}
## Model: {config.model}
## Timestamp: {datetime.now().isoformat()}

### Prompt Summary (first 200 chars):
```
{prompt[:200]}...
```

### To get real AI output:
1. Use mode='openclaw' with OpenClaw Gateway running
2. Or implement direct API call in _execute_local()
3. Or set BMAD_EVO_USE_MOCK=1 for testing (current)

---
*This is not real AI output. This is a placeholder for testing.*
"""

            execution_time = time.time() - start_time

            return AgentResult(
                success=True,
                output=output,
                model_used=f"{config.model}(MOCK-FOR-TESTING)",
                execution_time=execution_time,
            )

        # 默认情况：抛出错误，要求使用真实实现
        raise RuntimeError(
            f"Local mode does not have a real AI implementation.\n\n"
            f"Role: {config.name}\n"
            f"Model: {config.model}\n\n"
            f"To execute this agent, you have 3 options:\n"
            f"1. Use mode='openclaw' with OpenClaw Gateway running (recommended)\n"
            f"2. Implement direct API call in _execute_local() method\n"
            f"3. Set BMAD_EVO_USE_MOCK=1 for testing only (will generate warnings)\n\n"
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
    mode: str = "openclaw",
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
        "--mode", default="local", choices=["openclaw", "local"], help="Execution mode"
    )
    parser.add_argument("--list", action="store_true", help="List available agents")

    args = parser.parse_args()

    if args.list:
        executor = AgentExecutor(args.project)
        agents = executor.list_agents()
        print("Available Agents:")
        for name, config in agents.items():
            print(f"  - {name}: {config.description} (model: {config.model})")
    else:
        result = execute_agent(args.phase, args.project, args.context, mode=args.mode)
        print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
