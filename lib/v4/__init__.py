"""
BMAD-EVO v4.0 - Thinking Chain Analysis System

核心改进（相比v3.1单向流）:
1. 增量数据采集: 每个角色执行前自动规划并收集该角色专属数据
2. 双向反馈循环: 后续角色可向前置角色发送反馈，触发重新分析
3. 自我反思链: 最终环节评估整个报告的立场、观点、遗漏、假设合理性
4. 分析模式分流: 简单分析用单向流(complexity<=6)，复杂分析用思考链(complexity>=7)

模块:
- thinking_chain: 思考链引擎核心组件
"""

from .thinking_chain import (
    AnalysisMode,
    DataCollectionSpec,
    DataCollectionPlanner,
    FeedbackMessage,
    ReflectionIssue,
    SelfReflectionEngine,
    ThinkingChainState,
    ThinkingChainExecutor,
)

try:
    from .data_collector import DataCollector
    _HAS_DATA_COLLECTOR = True
except ImportError:
    _HAS_DATA_COLLECTOR = False

FeedbackProcessor = DataCollectionPlanner

__all__ = [
    "AnalysisMode",
    "DataCollectionSpec",
    "DataCollectionPlanner",
    "FeedbackMessage",
    "FeedbackProcessor",
    "ReflectionIssue",
    "SelfReflectionEngine",
    "ThinkingChainState",
    "ThinkingChainExecutor",
    "DataCollector",
]

__version__ = "4.1.0"
