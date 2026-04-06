"""
BMAD-EVO v3.0 - 全动态智能生成系统
主入口模块

使用示例:
    from lib.v3 import BMADEVO3

    system = BMADEVO3(project_path="./my_project")
    result = system.execute("开发一个用户认证系统")
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

from .task_analyzer import TaskAnalyzer, TaskAnalysis
from .role_generator import DynamicRoleGenerator, RoleFlow
from .model_router import ModelRouter, RoutingResult
from .resilient_executor import WorkflowExecutor, ExecutionResult

logger = logging.getLogger(__name__)


class BMADEVO3:
    """
    BMAD-EVO v3.0 全动态智能生成系统

    完全由模型驱动，零硬编码规则
    """

    def __init__(
        self,
        project_path: str = ".",
        timeout: int = 300,
        max_retries: int = 3,
        budget_constraint: Optional[str] = None,
    ):
        self.project_path = Path(project_path)
        self.timeout = timeout
        self.max_retries = max_retries
        self.budget_constraint = budget_constraint

        # 初始化各组件
        self.task_analyzer = TaskAnalyzer(timeout=120)
        self.role_generator = DynamicRoleGenerator(timeout=180)
        self.model_router = ModelRouter()
        self.workflow_executor = WorkflowExecutor(
            project_path=project_path, max_retries=max_retries, timeout=timeout
        )

        # 结果存储
        self.task_analysis: Optional[TaskAnalysis] = None
        self.role_flow: Optional[RoleFlow] = None
        self.routing_result: Optional[RoutingResult] = None
        self.execution_results: Dict[str, ExecutionResult] = {}

        logger.info(f"BMAD-EVO v3.0 initialized (project: {project_path})")

    def execute(self, task_description: str) -> Dict[str, Any]:
        """
        执行任务

        Args:
            task_description: 任务描述

        Returns:
            执行结果
        """
        logger.info(f"Executing task: {task_description[:100]}...")

        # Step 1: 任务分析
        print("\n[Step 1] 任务分析...")
        self.task_analysis = self.task_analyzer.analyze(task_description)

        if self.task_analysis.error:
            logger.warning(
                f"Task analysis completed with error: {self.task_analysis.error}"
            )

        print(f"   任务类型: {self.task_analysis.task_type}")
        print(f"   复杂度: {self.task_analysis.complexity_score}/10")
        print(f"   推荐角色数: {self.task_analysis.recommended_roles_count}")
        print(f"   关键技能: {', '.join(self.task_analysis.key_skills)}")

        # Step 2: 生成角色
        print("\n[Step 2] 生成角色...")
        self.role_flow = self.role_generator.generate(
            task_description=task_description,
            task_analysis=self.task_analysis.to_dict(),
        )

        if self.role_flow.error:
            logger.warning(
                f"Role generation completed with error: {self.role_flow.error}"
            )

        print(f"   生成角色: {self.role_flow.total_roles} 个")
        print(f"   工作流类型: {self.role_flow.task_type}")
        for role in self.role_flow.roles:
            print(f"   - {role.title}: {role.description[:30]}...")

        # Step 3: 模型路由
        print("\n[Step 3] 模型路由...")
        roles_dict = [
            {
                "id": r.name,
                "name": r.title,
                "description": r.description,
                "responsibilities": r.responsibilities,
            }
            for r in self.role_flow.roles
        ]

        self.routing_result = self.model_router.route(
            roles=roles_dict,
            task_type=self.task_analysis.task_type,
            complexity_score=self.task_analysis.complexity_score,
            budget_constraint=self.budget_constraint,
        )

        print(f"   路由完成: {self.routing_result.total_roles} 个映射")
        print(f"   预估成本: {self.routing_result.estimated_cost_tier}")
        for mapping in self.routing_result.mappings:
            print(f"   - {mapping.role_id}: {mapping.primary_model}")

        # Step 4: 执行工作流
        print("\n[Step 4] 执行工作流...")
        model_routing = {
            m.role_id: [m.primary_model] + m.fallback_models
            for m in self.routing_result.mappings
        }

        roles_for_executor = [
            {
                "id": r.name,
                "name": r.title,
                "description": r.description,
                "responsibilities": r.responsibilities,
                "required_skills": r.required_skills,
                "input_from": r.input_from,
            }
            for r in self.role_flow.roles
        ]

        self.execution_results = self.workflow_executor.execute_workflow(
            roles=roles_for_executor,
            model_routing=model_routing,
            task_context=task_description,
            parallel_groups=self.role_flow.parallel_groups,
        )

        success_count = sum(1 for r in self.execution_results.values() if r.success)
        print(f"   执行完成: {success_count}/{len(self.execution_results)} 成功")

        # 返回完整结果
        return {
            "task_description": task_description,
            "task_analysis": self.task_analysis.to_dict(),
            "role_flow": self.role_flow.to_dict(),
            "routing": self.routing_result.to_dict(),
            "execution": {
                role_id: result.to_dict()
                for role_id, result in self.execution_results.items()
            },
            "summary": {
                "total_roles": self.role_flow.total_roles,
                "successful_executions": success_count,
                "failed_executions": len(self.execution_results) - success_count,
                "estimated_cost_tier": self.routing_result.estimated_cost_tier,
            },
        }

    def get_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "task_analysis": self.task_analysis.to_dict()
            if self.task_analysis
            else None,
            "role_flow": self.role_flow.to_dict() if self.role_flow else None,
            "routing": self.routing_result.to_dict() if self.routing_result else None,
            "execution_stats": self.workflow_executor.get_workflow_summary(),
        }

    def export_results(self, output_dir: Optional[str] = None) -> str:
        """导出结果到文件"""
        if output_dir is None:
            output_dir = self.project_path / ".bmad" / "v3_results"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 导出完整结果
        result_file = output_path / "execution_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "task_analysis": self.task_analysis.to_dict()
                    if self.task_analysis
                    else None,
                    "role_flow": self.role_flow.to_dict() if self.role_flow else None,
                    "routing": self.routing_result.to_dict()
                    if self.routing_result
                    else None,
                    "execution": {
                        role_id: result.to_dict()
                        for role_id, result in self.execution_results.items()
                    },
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        logger.info(f"Results exported to: {result_file}")
        return str(result_file)


# 便捷函数
def execute_task(
    task_description: str,
    project_path: str = ".",
    budget_constraint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    便捷函数：执行任务

    Args:
        task_description: 任务描述
        project_path: 项目路径
        budget_constraint: 预算约束 (low/medium/high)

    Returns:
        执行结果
    """
    system = BMADEVO3(project_path=project_path, budget_constraint=budget_constraint)
    return system.execute(task_description)


__all__ = ["BMADEVO3", "execute_task"]
