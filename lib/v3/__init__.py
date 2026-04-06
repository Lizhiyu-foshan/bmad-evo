"""
BMAD-EVO v3.1 - 全动态智能生成系统

模块:
- task_analyzer: 智能任务分析器
- role_generator: 动态角色生成器
- model_router: 模型智能路由器 (GLM Coding Plan)
- context_budget: 上下文预算管理器
- resilient_executor: 弹性执行器
- task_directory_manager: 任务目录管理器
- bmad_evo3: 主入口类
"""

from .task_analyzer import TaskAnalyzer, TaskAnalysis, analyze_task
from .role_generator import (
    DynamicRoleGenerator,
    RoleDefinition,
    RoleFlow,
    generate_roles,
)
from .model_router import (
    ModelRouter,
    RoleModelMapping,
    RoutingResult,
    route_models,
    ModelConfig,
    ModelCapability,
    AVAILABLE_MODELS,
)
from .context_budget import (
    ContextBudgetManager,
    TokenBudget,
    BudgetCheckResult,
    MODEL_CONTEXT_WINDOWS,
    HEADROOM_RATIO,
    estimate_tokens,
)
from .resilient_executor import (
    ResilientExecutor,
    WorkflowExecutor,
    ExecutionResult,
    ExecutionLog,
    execute_with_fallback,
)
from .task_directory_manager import (
    TaskDirectoryManager,
    create_task_directory,
    OutputType,
    TaskStatus,
    VersionInfo,
    VersionIndex,
)
from .bmad_evo3 import BMADEVO3, execute_task

__all__ = [
    "TaskAnalyzer",
    "TaskAnalysis",
    "analyze_task",
    "DynamicRoleGenerator",
    "RoleDefinition",
    "RoleFlow",
    "generate_roles",
    "ModelRouter",
    "RoleModelMapping",
    "RoutingResult",
    "route_models",
    "ModelConfig",
    "ModelCapability",
    "AVAILABLE_MODELS",
    "ContextBudgetManager",
    "TokenBudget",
    "BudgetCheckResult",
    "MODEL_CONTEXT_WINDOWS",
    "HEADROOM_RATIO",
    "estimate_tokens",
    "ResilientExecutor",
    "WorkflowExecutor",
    "ExecutionResult",
    "ExecutionLog",
    "execute_with_fallback",
    "TaskDirectoryManager",
    "create_task_directory",
    "OutputType",
    "TaskStatus",
    "VersionInfo",
    "VersionIndex",
    "BMADEVO3",
    "execute_task",
]

__version__ = "3.1.0"
