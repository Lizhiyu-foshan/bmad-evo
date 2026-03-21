"""
BMAD-EVO v3.0 - 全动态智能生成系统

模块:
- task_analyzer: 智能任务分析器
- role_generator: 动态角色生成器
- model_router: 模型智能路由器
- resilient_executor: 弹性执行器
- bmad_evo3: 主入口类
"""

from .task_analyzer import TaskAnalyzer, TaskAnalysis, analyze_task
from .role_generator import (
    DynamicRoleGenerator, RoleDefinition, RoleFlow,
    generate_roles
)
from .model_router import (
    ModelRouter, RoleModelMapping, RoutingResult,
    route_models, ModelConfig, ModelCapability
)
from .resilient_executor import (
    ResilientExecutor, WorkflowExecutor, ExecutionResult, ExecutionLog,
    execute_with_fallback
)
from .bmad_evo3 import BMADEVO3, execute_task

__all__ = [
    # Task Analyzer
    "TaskAnalyzer",
    "TaskAnalysis",
    "analyze_task",
    
    # Role Generator
    "DynamicRoleGenerator",
    "RoleDefinition",
    "RoleFlow",
    "generate_roles",
    
    # Model Router
    "ModelRouter",
    "RoleModelMapping",
    "RoutingResult",
    "route_models",
    "ModelConfig",
    "ModelCapability",
    
    # Resilient Executor
    "ResilientExecutor",
    "WorkflowExecutor",
    "ExecutionResult",
    "ExecutionLog",
    "execute_with_fallback",
    
    # Main Entry
    "BMADEVO3",
    "execute_task",
]

__version__ = "3.0.0"
