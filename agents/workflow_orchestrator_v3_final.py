"""
BMAD-EVO Workflow Orchestrator v3.1 - 修正流程实现

严格遵循正确流程：
用户输入
↓
项目生成
↓
定义全局约束
↓
任务类型检测
↓
复杂度评估
↓
上下文预算检查
↓
角色流程生成（包含选择合适的模型）
↓
【交互式任务分解确认】（多轮对话完善）
↓
【分解结果约束审计】（用户决策）
↓
【阶段网关】启动阶段 N
↓
【Agent 执行】调用对应模型角色按流程执行
↓
【强制审计】自动触发
↓
通过（≥85分）→ 【网关】进入阶段 N+1
↓
未通过 → 多轮迭代执行（关键节点确认模式）
"""

import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "lib" / "v3"))

from constraint_auditor import ConstraintAuditor
from decision_interface import DecisionInterface
from v3 import TaskAnalyzer, DynamicRoleGenerator, ModelRouter
from v3.role_generator import RoleFlow, RoleDefinition
from v3.resilient_executor import WorkflowExecutor
from v3.context_budget import ContextBudgetManager, estimate_tokens
from v3.task_directory_manager import TaskDirectoryManager, OutputType, TaskStatus

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WorkflowOrchestratorV3Final:
    """
    BMAD-EVO v3.1 最终工作流编排器

    严格按照正确顺序执行：
    项目生成 → 全局约束 → 任务分析 → 上下文预算 → 角色生成 →
    交互确认 → 约束审计 → 阶段执行（多轮迭代）
    """

    DEFAULT_MAX_RETRIES = 3
    DEFAULT_PASS_THRESHOLD = 85
    DEFAULT_MAX_ITERATIONS = 5

    def __init__(
        self,
        project_path: str,
        interactive: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.project_path = Path(project_path)
        self.interactive = interactive
        self.config = config or {}

        self.max_retries = self.config.get("max_retries", self.DEFAULT_MAX_RETRIES)
        self.pass_threshold = self.config.get(
            "pass_threshold", self.DEFAULT_PASS_THRESHOLD
        )
        self.max_iterations = self.config.get(
            "max_iterations", self.DEFAULT_MAX_ITERATIONS
        )

        self.task_analyzer = TaskAnalyzer(timeout=120)
        self.role_generator = DynamicRoleGenerator(timeout=180)
        self.model_router = ModelRouter()
        self.auditor = ConstraintAuditor(project_path)
        self.decision_interface = DecisionInterface(project_path, interactive)
        self.budget_manager = ContextBudgetManager()

        self.role_flow: Optional[RoleFlow] = None
        self.task_analysis = None
        self.model_routing = None
        self.phase_results: Dict[str, Any] = {}
        self.global_constraints = {}
        self.iteration_feedback: List[str] = []

        self.task_dir_manager: Optional[TaskDirectoryManager] = None

        logger.info(f"WorkflowOrchestratorV3Final initialized (v3.1)")

    def execute_full_workflow(self, task_description: str) -> Dict[str, Any]:
        """
        执行完整工作流（严格按照正确顺序）

        流程:
        1. 用户输入 (参数)
        2. 项目生成
        3. 定义全局约束
        4. 任务类型检测
        5. 复杂度评估
        5.5. 上下文预算检查
        6. 角色流程生成（包含模型选择）
        6.5. 交互式任务分解确认
        6.6. 分解结果约束审计
        7. 阶段执行循环（网关+执行+审计+多轮迭代+决策）
        """
        self._print_workflow_header(task_description)

        self._step1_generate_project(task_description)
        self._step2_define_global_constraints()
        self._step3_task_type_detection(task_description)
        self._step4_complexity_assessment()
        self._step5_role_flow_generation(task_description)
        self._step55_context_budget_check(task_description)

        if not self._step56_interactive_plan_confirmation(task_description):
            return {"success": False, "reason": "user_cancelled"}

        if not self._step57_plan_constraint_audit(task_description):
            return {"success": False, "reason": "constraint_audit_failed"}

        all_passed = self._step6_phase_execution_loop(task_description)

        return self._generate_final_report(task_description, all_passed)

    def _print_workflow_header(self, task_description: str):
        """打印工作流头部信息"""
        print("=" * 70)
        print("🚀 BMAD-EVO v3.1 - 修正流程")
        print("=" * 70)
        print(f"任务: {task_description[:60]}...")
        print("=" * 70 + "\n")

    def _step1_generate_project(self, task_description: str):
        """步骤1: 项目生成"""
        print("📋 Step 1: 项目生成")
        print("-" * 70)
        self._generate_project(task_description)
        print(f"✅ 项目生成完成: {self.project_path}")

    def _step2_define_global_constraints(self):
        """步骤2: 定义全局约束"""
        print("\n📋 Step 2: 定义全局约束")
        print("-" * 70)
        self._define_global_constraints()
        print("✅ 全局约束定义完成")

    def _step3_task_type_detection(self, task_description: str):
        """步骤3: 任务类型检测"""
        print("\n📋 Step 3: 任务类型检测")
        print("-" * 70)
        self.task_analysis = self.task_analyzer.analyze(task_description)
        print(f"✅ 任务类型检测完成: {self.task_analysis.task_type}")

    def _step4_complexity_assessment(self):
        """步骤4: 复杂度评估"""
        print("\n📋 Step 4: 复杂度评估")
        print("-" * 70)
        print(f"✅ 复杂度评估完成: {self.task_analysis.complexity_score}/10")
        print(f"   预估时间: {self.task_analysis.estimated_duration}")
        print(f"   推荐角色数: {self.task_analysis.recommended_roles_count}")

    def _step5_role_flow_generation(self, task_description: str):
        """步骤5: 角色流程生成（包含模型选择）"""
        print("\n📋 Step 5: 角色流程生成（包含模型选择）")
        print("-" * 70)

        self.role_flow = self.role_generator.generate(
            task_description=task_description,
            task_analysis=self.task_analysis.to_dict(),
        )

        print(f"✅ 角色生成完成: {self.role_flow.total_roles} 个角色")
        print(f"   执行顺序: {' → '.join(self.role_flow.execution_order)}")

        self.model_routing = self.model_router.route(
            roles=[r.to_dict() for r in self.role_flow.roles],
            task_type=self.task_analysis.task_type,
            complexity_score=self.task_analysis.complexity_score,
        )

        print(f"\n✅ 模型选择完成:")
        for mapping in self.model_routing.mappings:
            print(f"   {mapping.role_id}: {mapping.primary_model}")
        print(f"   预估成本: {self.model_routing.estimated_cost_tier}")

    def _step55_context_budget_check(self, task_description: str):
        """步骤5.5: 上下文预算检查"""
        print("\n📋 Step 5.5: 上下文预算检查")
        print("-" * 70)
        self._check_context_budget(task_description)

    def _step56_interactive_plan_confirmation(self, task_description: str) -> bool:
        """步骤5.6: 交互式任务分解确认"""
        print("\n📋 Step 5.6: 交互式任务分解确认")
        print("-" * 70)
        return self._interactive_plan_confirmation(task_description)

    def _step57_plan_constraint_audit(self, task_description: str) -> bool:
        """步骤5.7: 分解结果约束审计"""
        print("\n📋 Step 5.7: 分解结果约束审计")
        print("-" * 70)
        return self._plan_constraint_audit(task_description)

    def _step6_phase_execution_loop(self, task_description: str) -> bool:
        """步骤6: 阶段执行循环（多轮迭代）"""
        print("\n" + "=" * 70)
        print("📋 Step 6: 阶段执行（网关 → 执行 → 审计 → 多轮迭代）")
        print("=" * 70)

        all_passed = True

        for i, role_name in enumerate(self.role_flow.execution_order):
            role = self._get_role_by_name(role_name)
            if not role:
                continue

            print(f"\n{'=' * 70}")
            print(
                f"🚀 【阶段网关】启动阶段 {i + 1}/{len(self.role_flow.execution_order)}: {role.title}"
            )
            print(f"{'=' * 70}")

            phase_result = self._execute_phase_with_iteration(
                role, task_description, i + 1
            )
            self.phase_results[role_name] = phase_result

            if not phase_result.get("passed"):
                all_passed = False
                if phase_result.get("aborted"):
                    print(f"\n❌ 工作流中止")
                    break

        return all_passed

    def _check_context_budget(self, task_description: str):
        """上下文预算检查"""
        roles = [r.to_dict() for r in self.role_flow.roles]
        model_routing = {}
        for mapping in self.model_routing.mappings:
            model_routing[mapping.role_id] = [
                mapping.primary_model
            ] + mapping.fallback_models

        budget_results = self.budget_manager.check_workflow_budget(
            roles=roles,
            model_routing=model_routing,
            task_description=task_description,
        )

        report = self.budget_manager.format_budget_report(budget_results)
        print(report)

        for result in budget_results:
            if not result["check"]["sufficient"]:
                print(f"\n   ⚠️  角色预算不足: {result['role_name']}")
                for suggestion in result["check"]["suggestions"]:
                    print(f"      💡 {suggestion}")

        # 更新 assignment.md 文档（任务分解和模型指派）
        if self.task_dir_manager:
            self.task_dir_manager.update_assignment_document(
                self.role_flow,
                self.model_routing,
                report,
            )
            print("   ✅ 已更新 tasks/assignment.md")

    def _interactive_plan_confirmation(self, task_description: str) -> bool:
        """
        交互式任务分解确认（支持多轮对话完善）

        列出执行方案，默认回车同意，支持多轮对话完善。
        """
        if not self.interactive:
            print("   非交互模式，自动确认执行方案")
            return True

        while True:
            print(f"\n   📋 执行方案概览:")
            print(f"   {'─' * 50}")
            print(f"   任务: {task_description[:80]}...")
            print(f"   任务类型: {self.task_analysis.task_type}")
            print(f"   复杂度: {self.task_analysis.complexity_score}/10")
            print(f"   角色数: {self.role_flow.total_roles}")
            print(f"   {'─' * 50}")
            print(f"   执行顺序:")

            for i, role_name in enumerate(self.role_flow.execution_order, 1):
                role = self._get_role_by_name(role_name)
                model_mapping = self._get_model_mapping(role_name)
                model_str = model_mapping["primary_model"] if model_mapping else "auto"
                title = role.title if role else role_name
                print(f"     {i}. {title} (模型: {model_str})")

            print(f"   {'─' * 50}")
            print(f"   预估成本等级: {self.model_routing.estimated_cost_tier}")

            if self.role_flow.execution_order:
                print(f"\n   角色职责:")
                for role_name in self.role_flow.execution_order:
                    role = self._get_role_by_name(role_name)
                    if role:
                        print(f"     [{role.title}]")
                        for resp in role.responsibilities[:3]:
                            print(f"       - {resp}")

            print(f"\n   选项:")
            print(f"     [Enter] 确认执行方案，开始执行")
            print(f"     m       修改方案（输入修改建议）")
            print(f"     c       取消工作流")

            choice = input("\n   请选择: ").strip().lower()

            if choice == "" or choice == "y" or choice == "yes":
                print("   ✅ 执行方案已确认")
                return True
            elif choice == "c" or choice == "cancel":
                return False
            elif choice == "m" or choice == "modify":
                feedback = input("   请输入修改建议: ").strip()
                if feedback:
                    self.iteration_feedback.append(feedback)
                    print(f"   📝 已记录修改建议，重新生成执行方案...")
                    self._refine_plan(feedback, task_description)
                else:
                    print("   未输入建议，保持原方案")
            else:
                print("   ✅ 默认确认执行方案")
                return True

    def _refine_plan(self, feedback: str, task_description: str):
        """根据用户反馈完善执行方案"""
        try:
            enriched_description = f"{task_description}\n\n用户额外要求: {feedback}"
            for old_fb in self.iteration_feedback[:-1]:
                enriched_description += f"\n- {old_fb}"

            self.role_flow = self.role_generator.generate(
                task_description=enriched_description,
                task_analysis=self.task_analysis.to_dict(),
            )

            self.model_routing = self.model_router.route(
                roles=[r.to_dict() for r in self.role_flow.roles],
                task_type=self.task_analysis.task_type,
                complexity_score=self.task_analysis.complexity_score,
            )

            print(f"   ✅ 方案已更新: {self.role_flow.total_roles} 个角色")
        except Exception as e:
            logger.warning(f"Plan refinement failed: {e}, keeping original plan")
            print(f"   ⚠️ 方案更新失败，保持原方案: {e}")

    def _plan_constraint_audit(self, task_description: str) -> bool:
        """
        分解结果约束审计

        检查执行方案是否满足全局约束，提醒用户决策。
        """
        warnings = []
        suggestions = []

        if self.role_flow:
            for role in self.role_flow.roles:
                if not role.responsibilities:
                    warnings.append(f"角色 '{role.title}' 没有定义职责")

            if len(self.role_flow.execution_order) > 7:
                warnings.append(
                    f"角色数量较多 ({len(self.role_flow.execution_order)})，可能增加执行时间和成本"
                )
                suggestions.append("考虑合并相似角色以减少阶段数")

        if self.model_routing:
            expensive_count = sum(
                1
                for m in self.model_routing.mappings
                if m.primary_model in ("glm-5.1",)
            )
            if expensive_count > len(self.model_routing.mappings) / 2:
                warnings.append(
                    f"超过半数角色使用高成本模型 (glm-5.1: {expensive_count}个)"
                )
                suggestions.append("考虑对非关键角色使用 glm-4.7 或 glm-4.7-flash")

        for role_name in self.role_flow.execution_order:
            model_mapping = self._get_model_mapping(role_name)
            if model_mapping:
                primary = model_mapping["primary_model"]
                budget_check = self.budget_manager.check_budget(
                    model_id=primary,
                    system_prompt="",
                    context_from_previous="",
                    task_description=task_description,
                )
                if not budget_check.sufficient:
                    warnings.append(
                        f"角色 '{role_name}' (模型: {primary}) 上下文预算不足"
                    )

        if not warnings:
            print("   ✅ 约束审计通过，执行方案满足全局约束")
            return True

        print(f"   ⚠️  约束审计发现 {len(warnings)} 个问题:")
        for i, w in enumerate(warnings, 1):
            print(f"      {i}. {w}")

        if suggestions:
            print(f"\n   💡 建议:")
            for s in suggestions:
                print(f"      - {s}")

        if not self.interactive:
            print("   非交互模式，自动继续")
            return True

        print(f"\n   选项:")
        print(f"     [Enter] 确认继续（接受警告）")
        print(f"     m       返回修改方案")
        print(f"     a       中止工作流")

        choice = input("   请选择: ").strip().lower()
        if choice == "a":
            return False
        elif choice == "m":
            feedback = input("   请输入修改建议: ").strip()
            if feedback:
                self.iteration_feedback.append(feedback)
                self._refine_plan(feedback, task_description)
                return self._plan_constraint_audit(task_description)
            return True
        else:
            print("   ✅ 已确认继续")
            return True

    def _execute_phase_with_iteration(
        self, role: RoleDefinition, task_description: str, phase_num: int
    ) -> Dict[str, Any]:
        """
        执行单个阶段（多轮迭代）

        关键节点确认模式：
        - 首次执行后询问用户
        - 之后自动迭代直到审计通过或达到上限
        - 用户反馈作为下一轮新约束
        """
        role_name = role.name
        model_mapping = self._get_model_mapping(role_name)
        accumulated_feedback: List[str] = []
        first_iteration = True

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n📍 迭代 {iteration}/{self.max_iterations}")
            self._print_iteration_info(role, model_mapping)

            exec_result = self._execute_agent_with_feedback(
                role, task_description, model_mapping, accumulated_feedback
            )
            print(f"   ⏱️  执行时间: {exec_result.get('execution_time', 0):.2f}s")

            audit_result, audit_score = self._perform_and_score_audit(
                role_name, exec_result.get("output", "")
            )
            self._print_audit_results(audit_result, audit_score)

            if audit_score >= self.pass_threshold:
                return self._create_passed_result(
                    phase_num, role_name, iteration, audit_score, exec_result
                )

            accumulated_feedback.append(
                self._create_violation_feedback(iteration, audit_score, audit_result)
            )

            first_iteration_result = self._handle_first_iteration_interaction(
                role,
                audit_score,
                iteration,
                exec_result,
                phase_num,
                role_name,
                accumulated_feedback,
            )
            if first_iteration_result is not None:
                return first_iteration_result

            if iteration < self.max_iterations:
                print(f"   🔄 自动迭代改进中...")
                continue

        return self._handle_max_iterations_reached(
            role, audit_result, audit_score, exec_result, phase_num, role_name
        )

    def _print_iteration_info(
        self, role: RoleDefinition, model_mapping: Optional[Dict]
    ):
        """打印迭代信息"""
        print(f"   角色: {role.title}")
        if model_mapping:
            print(f"   模型: {model_mapping['primary_model']}")

    def _execute_agent_with_feedback(
        self,
        role: RoleDefinition,
        task_description: str,
        model_mapping: Optional[Dict],
        accumulated_feedback: List[str],
    ) -> Dict[str, Any]:
        """执行 agent（包含反馈）"""
        iteration_feedback = (
            "\n".join(accumulated_feedback) if accumulated_feedback else None
        )
        return self._execute_agent(
            role, task_description, model_mapping, iteration_feedback
        )

    def _perform_and_score_audit(self, role_name: str, output: str) -> tuple:
        """执行审计并评分"""
        print(f"\n   🔍 【强制审计】检查中...")
        audit = self._perform_audit(role_name, output)
        audit_score = self._calculate_audit_score(audit)
        return audit, audit_score

    def _print_audit_results(self, audit: Dict, audit_score: int):
        """打印审计结果"""
        print(f"   📊 审计分数: {audit_score}/100 (需要≥{self.pass_threshold})")

        if audit.get("violations"):
            for v in audit["violations"][:3]:
                print(
                    f"      ⚠️  [{v.get('severity', 'MEDIUM')}] {v.get('message', '')[:40]}"
                )

        if audit_score < self.pass_threshold:
            print(f"   ❌ 审计未通过 ({audit_score}分 < {self.pass_threshold}分)")

    def _create_passed_result(
        self,
        phase_num: int,
        role_name: str,
        iteration: int,
        audit_score: int,
        exec_result: Dict,
    ) -> Dict[str, Any]:
        """创建审计通过的结果"""
        print(f"   ✅ 审计通过！({audit_score}分)")
        return {
            "passed": True,
            "phase": phase_num,
            "role": role_name,
            "iteration": iteration,
            "audit_score": audit_score,
            "output": exec_result.get("output", ""),
        }

    def _create_violation_feedback(
        self, iteration: int, audit_score: int, audit: Dict
    ) -> str:
        """创建违规反馈"""
        violation_summary = "; ".join(
            v.get("message", "")[:50] for v in audit.get("violations", [])[:3]
        )
        return f"[迭代{iteration}未通过, 分数={audit_score}] {violation_summary}"

    def _handle_first_iteration_interaction(
        self,
        role: RoleDefinition,
        audit_score: int,
        iteration: int,
        exec_result: Dict,
        phase_num: int,
        role_name: str,
        accumulated_feedback: List[str],
    ) -> Optional[Dict[str, Any]]:
        """处理首次迭代的用户交互"""
        if not self.interactive:
            return None

        print(f"\n   🔔 首次执行未通过，需要用户确认:")
        print(
            f"      c       继续自动迭代（直到通过或达到{self.max_iterations}轮上限）"
        )
        print(f"      f       输入反馈作为下一轮约束")
        print(f"      force   强制通过（接受当前质量）")
        print(f"      abort   中止工作流")

        choice = input("   请选择: ").strip().lower()

        if choice == "force":
            print(f"   ⚡ 用户选择强制通过")
            return {
                "passed": True,
                "forced": True,
                "audit_score": audit_score,
                "phase": phase_num,
                "role": role_name,
                "iteration": iteration,
                "output": exec_result.get("output", ""),
            }
        elif choice == "abort":
            print(f"   ❌ 用户选择中止")
            return {"passed": False, "aborted": True}
        elif choice == "f":
            user_feedback = input("   请输入反馈: ").strip()
            if user_feedback:
                accumulated_feedback.append(f"[用户反馈] {user_feedback}")
            print(f"   🔄 将反馈纳入下一轮迭代...")

        return None

    def _handle_max_iterations_reached(
        self,
        role: RoleDefinition,
        audit: Dict,
        audit_score: int,
        exec_result: Dict,
        phase_num: int,
        role_name: str,
    ) -> Dict[str, Any]:
        """处理达到最大迭代次数的情况"""
        print(f"\n   🚫 达到最大迭代次数 ({self.max_iterations})，提交用户决策")
        decision = self._user_decision(role, audit, audit_score)

        if decision == "force_proceed":
            print(f"   ⚡ 用户选择强制继续")
            return {
                "passed": True,
                "forced": True,
                "audit_score": audit_score,
                "phase": phase_num,
                "role": role_name,
                "iteration": self.max_iterations,
                "output": exec_result.get("output", ""),
            }
        elif decision == "relax_constraint":
            print(f"   🔓 用户选择放宽约束")
            self.pass_threshold = max(60, self.pass_threshold - 10)
            return {
                "passed": True,
                "relaxed": True,
                "audit_score": audit_score,
                "phase": phase_num,
                "role": role_name,
                "iteration": self.max_iterations,
                "output": exec_result.get("output", ""),
            }
        elif decision == "manual_fix":
            print(f"   🔧 用户选择手动修复")
            return {"passed": False, "blocked": True, "waiting_fix": True}
        else:
            print(f"   ❌ 用户选择中止")
            return {"passed": False, "aborted": True}

    def _execute_agent(
        self,
        role: RoleDefinition,
        task_description: str,
        model_mapping: Dict,
        iteration_feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Agent 执行"""
        from agent_executor import AgentExecutor, AgentResult

        start_time = time.time()
        context = self._build_context(role)

        model = (
            model_mapping.get("primary_model", "glm-4.7")
            if model_mapping
            else "glm-4.7"
        )

        try:
            executor = AgentExecutor(project_path=self.project_path, mode="openclaw")

            full_context = f"Task: {task_description}\n\nContext:\n{context}"
            if iteration_feedback:
                full_context += (
                    f"\n\n## 迭代反馈（需要改进的问题）\n{iteration_feedback}"
                )

            result: AgentResult = executor.execute(
                phase=role.name, context=full_context
            )

            return {
                "output": result.output,
                "model": result.model_used,
                "execution_time": result.execution_time,
                "success": result.success,
                "error": result.error,
                "token_usage": result.token_usage,
            }

        except Exception as e:
            logger.error(f"Agent execution failed for role {role.name}: {e}")
            return {
                "output": "",
                "model": model,
                "execution_time": time.time() - start_time,
                "success": False,
                "error": str(e),
            }

    def _perform_audit(self, role_name: str, output: str) -> Dict:
        """强制审计"""
        audit_result = self.auditor.audit(output=output, phase=role_name)

        violations = []
        for v in audit_result.violations:
            violations.append(
                {
                    "severity": v.severity.value
                    if hasattr(v.severity, "value")
                    else str(v.severity),
                    "message": v.description,
                    "rule": v.constraint_type.value
                    if hasattr(v.constraint_type, "value")
                    else str(v.constraint_type),
                }
            )

        return {
            "violations": violations,
            "score": audit_result.score,
            "passed": audit_result.passed,
            "raw_result": audit_result,
        }

    def _calculate_audit_score(self, audit: Dict) -> int:
        return audit.get("score", 0)

    def _user_decision(self, role: RoleDefinition, audit: Dict, score: int) -> str:
        """用户决策"""
        if not self.interactive:
            return "abort"

        print(f"\n{'=' * 70}")
        print("🚫 阶段阻塞 - 需要用户决策")
        print(f"{'=' * 70}")
        print(f"角色: {role.title}")
        print(f"审计分数: {score}/100 (需要≥{self.pass_threshold})")
        print(f"\n违规项:")
        for v in audit.get("violations", [])[:5]:
            print(f"  - [{v['severity']}] {v['message'][:50]}")

        print(f"\n选项:")
        print(f"  1. manual_fix   - 手动修复后重试")
        print(f"  2. relax        - 放宽约束继续")
        print(f"  3. force        - 强制继续")
        print(f"  4. abort        - 中止工作流")

        choice = input("\n请选择 (1/2/3/4): ").strip()
        mapping = {
            "1": "manual_fix",
            "2": "relax_constraint",
            "3": "force_proceed",
            "4": "abort",
        }
        return mapping.get(choice, "abort")

    def _get_role_by_name(self, name: str) -> Optional[RoleDefinition]:
        if not self.role_flow:
            return None
        for role in self.role_flow.roles:
            if role.name == name:
                return role
        return None

    def _get_model_mapping(self, role_name: str) -> Optional[Dict]:
        if not self.model_routing:
            return None
        for mapping in self.model_routing.mappings:
            if mapping.role_id == role_name:
                return {
                    "primary_model": mapping.primary_model,
                    "fallback_models": mapping.fallback_models,
                }
        return None

    def _build_context(self, role: RoleDefinition) -> str:
        context_parts = []
        for input_role in role.input_from:
            if input_role in self.phase_results:
                result = self.phase_results[input_role]
                context_parts.append(
                    f"【来自{input_role}】\n{result.get('output', '')}"
                )
        return "\n\n".join(context_parts)

    def _generate_project(self, task_description: str):
        """
        步骤1: 项目生成 + 任务目录结构创建

        创建完整的目录结构，包括：
        - .bmad/ 目录
        - tasks/ 目录（requirement.md, design.md, assignment.md）
        - outputs/ 目录（reports/, code/, docs/）
        - logs/ 目录
        - 版本索引
        """
        self.project_path.mkdir(parents=True, exist_ok=True)

        (self.project_path / ".bmad").mkdir(exist_ok=True)
        (self.project_path / ".bmad" / "decisions").mkdir(exist_ok=True)
        (self.project_path / ".bmad" / "checkpoints").mkdir(exist_ok=True)
        (self.project_path / ".bmad" / "reports").mkdir(exist_ok=True)
        (self.project_path / ".bmad" / "constraints").mkdir(exist_ok=True)

        # 初始化任务目录管理器
        self.task_dir_manager = TaskDirectoryManager(
            str(self.project_path), task_description
        )

        # 创建完整的任务目录结构
        structure_info = self.task_dir_manager.create_task_structure(
            output_type=OutputType.MIXED,
            task_type=self.task_analysis.task_type if self.task_analysis else "general",
        )

        print(f"✅ 项目生成完成: {self.project_path}")
        print(f"✅ 任务目录结构已创建")

        if self.task_dir_manager:
            print(f"   ├─ tasks/ (requirement.md, design.md, assignment.md)")
            print(f"   ├─ outputs/ (reports/, code/, docs/)")
            print(f"   ├─ .bmad/ (versions/, decisions/, checkpoints/)")
            print(f"   └─ logs/ (execution.log, audit.log)")

        project_meta = {
            "name": self.project_path.name,
            "task_description": task_description[:200],
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "version": "3.1",
            "task_directory": structure_info,
        }

        with open(self.project_path / ".bmad" / "project-meta.json", "w") as f:
            json.dump(project_meta, f, indent=2, ensure_ascii=False)

    def _define_global_constraints(self):
        self.global_constraints = {
            "boundary_check": {
                "check_null": True,
                "check_empty": True,
            },
            "exception_handling": {
                "check_io": True,
                "check_network": True,
                "no_bare_except": True,
            },
            "code_structure": {
                "max_function_lines": 50,
                "max_file_lines": 500,
                "require_type_hints": False,
            },
            "security": {
                "check_secrets": True,
                "no_hardcoded_keys": True,
            },
            "audit": {
                "pass_threshold": self.pass_threshold,
                "max_retries": self.max_retries,
                "max_iterations": self.max_iterations,
                "strict_mode": True,
            },
        }

        with open(
            self.project_path / ".bmad" / "constraints" / "global.json", "w"
        ) as f:
            json.dump(self.global_constraints, f, indent=2, ensure_ascii=False)

    def _generate_final_report(
        self, task_description: str, all_passed: bool
    ) -> Dict[str, Any]:
        print("\n" + "=" * 70)
        print("📊 工作流执行总结")
        print("=" * 70)

        total_phases = len(self.role_flow.execution_order) if self.role_flow else 0
        completed = sum(1 for p in self.phase_results.values() if p.get("passed"))

        print(f"\n任务: {task_description[:50]}...")
        print(f"总阶段: {total_phases}")
        print(f"通过: {completed}")

        for role_name in self.role_flow.execution_order if self.role_flow else []:
            result = self.phase_results.get(role_name, {})
            role = self._get_role_by_name(role_name)
            status = "✅" if result.get("passed") else "❌"
            iter_info = (
                f" (迭代{result.get('iteration', '?')})"
                if result.get("iteration", 1) > 1
                else ""
            )
            forced = " [强制]" if result.get("forced") else ""
            relaxed = " [放宽]" if result.get("relaxed") else ""
            print(
                f"   {status} {role.title if role else role_name}{iter_info}{forced}{relaxed}"
            )

        if self.iteration_feedback:
            print(f"\n📝 用户反馈记录 ({len(self.iteration_feedback)} 条):")
            for i, fb in enumerate(self.iteration_feedback, 1):
                print(f"   {i}. {fb[:60]}...")

        # 创建新版本并保存输出
        current_version = None
        if self.task_dir_manager:
            print(f"\n💾 保存工作流输出...")

            changes = [
                f"完成 {total_phases} 个阶段，{completed} 个通过",
                f"任务类型: {self.task_analysis.task_type if self.task_analysis else '未知'}",
                f"复杂度: {self.task_analysis.complexity_score}/10"
                if self.task_analysis
                else "",
            ]

            output_type = OutputType.MIXED
            if self.task_analysis:
                if (
                    "开发" in self.task_analysis.task_type
                    or "代码" in self.task_analysis.task_type
                ):
                    output_type = OutputType.CODE
                elif (
                    "分析" in self.task_analysis.task_type
                    or "报告" in self.task_analysis.task_type
                ):
                    output_type = OutputType.REPORT
                elif (
                    "写作" in self.task_analysis.task_type
                    or "文档" in self.task_analysis.task_type
                ):
                    output_type = OutputType.DOCUMENT

            current_version = self.task_dir_manager.create_new_version(
                output_type=output_type,
                changes=changes,
                status=TaskStatus.COMPLETED if all_passed else TaskStatus.FAILED,
            )

            print(f"   ✅ 创建版本: {current_version}")

            report_content = self._generate_markdown_report(
                task_description, all_passed
            )

            if output_type == OutputType.REPORT:
                self.task_dir_manager.save_report(
                    current_version,
                    report_content,
                    meta={
                        "total_phases": total_phases,
                        "completed_phases": completed,
                        "all_passed": all_passed,
                        "task_type": self.task_analysis.task_type
                        if self.task_analysis
                        else "unknown",
                        "complexity": self.task_analysis.complexity_score
                        if self.task_analysis
                        else 0,
                    },
                )
                print(f"   ✅ 报告已保存: outputs/reports/{current_version}/report.md")
            elif output_type == OutputType.DOCUMENT:
                self.task_dir_manager.save_document(
                    current_version,
                    report_content,
                    meta={
                        "total_phases": total_phases,
                        "completed_phases": completed,
                        "all_passed": all_passed,
                    },
                )
                print(f"   ✅ 文档已保存: outputs/docs/{current_version}/content.md")
            elif output_type == OutputType.MIXED:
                self.task_dir_manager.save_report(
                    current_version,
                    report_content,
                    meta={
                        "output_type": "mixed",
                        "total_phases": total_phases,
                        "completed_phases": completed,
                        "all_passed": all_passed,
                    },
                )
                print(f"   ✅ 报告已保存: outputs/reports/{current_version}/report.md")

            avg_audit_score = None
            audit_scores = []
            for result in self.phase_results.values():
                if result.get("audit_score"):
                    audit_scores.append(result["audit_score"])
            if audit_scores:
                avg_audit_score = sum(audit_scores) / len(audit_scores)

            max_iterations = max(
                (r.get("iteration", 1) for r in self.phase_results.values()), default=1
            )

            self.task_dir_manager.update_version_status(
                current_version,
                status=TaskStatus.COMPLETED if all_passed else TaskStatus.FAILED,
                audit_score=avg_audit_score,
                iterations=max_iterations,
                user_feedback=self.iteration_feedback,
            )

            print(f"\n📋 版本信息:")
            print(f"   版本号: {current_version}")
            print(f"   状态: {'完成' if all_passed else '失败'}")
            if avg_audit_score:
                print(f"   平均审计分数: {avg_audit_score:.1f}")
            print(f"   总迭代次数: {max_iterations}")

            version_summary = self.task_dir_manager.get_version_summary()
            print(f"\n{version_summary}")

        return {
            "success": all_passed,
            "total_phases": total_phases,
            "completed_phases": completed,
            "phase_results": self.phase_results,
            "iteration_feedback": self.iteration_feedback,
            "version": "3.1",
            "current_version": current_version,
        }

    def _generate_markdown_report(self, task_description: str, all_passed: bool) -> str:
        lines = [
            f"# {self.project_path.name} 工作流执行报告",
            "",
            f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**版本**: v3.1",
            f"**任务描述**: {task_description}",
            "",
            "---",
            "",
            "## 任务概览",
            "",
        ]

        if self.task_analysis:
            lines.extend(
                [
                    f"- **任务类型**: {self.task_analysis.task_type}",
                    f"- **复杂度评分**: {self.task_analysis.complexity_score}/10",
                    f"- **预估时间**: {self.task_analysis.estimated_duration}",
                    f"- **推荐角色数**: {self.task_analysis.recommended_roles_count}",
                    "",
                ]
            )

        if self.role_flow:
            lines.extend(
                [
                    "## 角色流程",
                    "",
                    f"- **总角色数**: {self.role_flow.total_roles}",
                    f"- **执行顺序**: {' → '.join(self.role_flow.execution_order)}",
                    "",
                    "### 角色详情",
                    "",
                ]
            )

            for role in self.role_flow.roles:
                lines.extend(
                    [
                        f"#### {role.title}",
                        f"- **角色ID**: {role.name}",
                        f"- **描述**: {role.description}",
                        f"- **职责**:",
                    ]
                )
                for resp in role.responsibilities:
                    lines.append(f"  - {resp}")
                lines.append("")

        if self.model_routing:
            lines.extend(
                [
                    "## 模型指派",
                    "",
                    f"- **预估成本等级**: {self.model_routing.estimated_cost_tier}",
                    "",
                    "### 模型分配表",
                    "",
                    "| 角色名称 | 主模型 | 备选模型 | 理由 |",
                    "|---------|--------|----------|------|",
                ]
            )

            for mapping in self.model_routing.mappings:
                role = next(
                    (r for r in self.role_flow.roles if r.name == mapping.role_id), None
                )
                title = role.title if role else mapping.role_id
                fallbacks = ", ".join(mapping.fallback_models[:3])
                lines.append(
                    f"| {title} | {mapping.primary_model} | {fallbacks} | {mapping.reasoning[:50]}... |"
                )

            lines.append("")

        lines.extend(
            [
                "## 执行结果",
                "",
            ]
        )

        total_phases = len(self.role_flow.execution_order) if self.role_flow else 0
        completed = sum(1 for p in self.phase_results.values() if p.get("passed"))

        lines.extend(
            [
                f"- **总阶段**: {total_phases}",
                f"- **通过**: {completed}",
                f"- **成功率**: {completed / total_phases * 100:.1f}%"
                if total_phases > 0
                else "- **成功率**: 0%",
                "",
                "### 阶段详情",
                "",
                "| 阶段 | 角色 | 状态 | 审计分数 | 迭代次数 |",
                "|------|------|------|----------|----------|",
            ]
        )

        for role_name in self.role_flow.execution_order if self.role_flow else []:
            result = self.phase_results.get(role_name, {})
            role = self._get_role_by_name(role_name)
            title = role.title if role else role_name
            status = "通过" if result.get("passed") else "失败"
            score = result.get("audit_score") or "-"
            iter_count = result.get("iteration", 1)
            lines.append(
                f"| {role_name} | {title} | {status} | {score} | {iter_count} |"
            )

        lines.append("")

        if self.iteration_feedback:
            lines.extend(
                [
                    "## 用户反馈",
                    "",
                ]
            )
            for i, fb in enumerate(self.iteration_feedback, 1):
                lines.append(f"{i}. {fb}")
            lines.append("")

        lines.extend(
            [
                "---",
                "",
                "*本报告由 BMAD-EVO v3.1 自动生成*",
            ]
        )

        return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="BMAD-EVO v3.1 最终流程")
    parser.add_argument("--project", default="./test_project", help="Project path")
    parser.add_argument(
        "--max-iterations", type=int, default=5, help="Max iterations per phase"
    )
    parser.add_argument("task", help="Task description")
    args = parser.parse_args()

    orchestrator = WorkflowOrchestratorV3Final(
        project_path=args.project, config={"max_iterations": args.max_iterations}
    )
    result = orchestrator.execute_full_workflow(args.task)

    print("\n最终结果:", json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
