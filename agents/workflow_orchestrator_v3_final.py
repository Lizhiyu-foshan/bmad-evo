"""
BMAD-EVO Workflow Orchestrator v3.0 - 修正流程实现

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
角色流程生成（包含选择合适的模型）
↓
【阶段网关】启动阶段 N
↓
【Agent 执行】调用对应模型角色按流程执行
↓
【强制审计】自动触发
↓
通过（≥85分）→ 【网关】进入阶段 N+1
↓
未通过，三次重试，仍失败就提交用户决策
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WorkflowOrchestratorV3Final:
    """
    BMAD-EVO v3.0 最终工作流编排器
    
    严格按照正确顺序执行：
    项目生成 → 全局约束 → 任务分析 → 角色生成 → 阶段执行
    """
    
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_PASS_THRESHOLD = 85
    
    def __init__(
        self,
        project_path: str,
        interactive: bool = True,
        config: Optional[Dict[str, Any]] = None
    ):
        self.project_path = Path(project_path)
        self.interactive = interactive
        self.config = config or {}
        
        # 配置
        self.max_retries = self.config.get('max_retries', self.DEFAULT_MAX_RETRIES)
        self.pass_threshold = self.config.get('pass_threshold', self.DEFAULT_PASS_THRESHOLD)
        
        # 初始化组件
        self.task_analyzer = TaskAnalyzer(timeout=120)
        self.role_generator = DynamicRoleGenerator(timeout=180)
        self.model_router = ModelRouter()
        self.auditor = ConstraintAuditor(project_path)
        self.decision_interface = DecisionInterface(project_path, interactive)
        
        # 执行状态
        self.role_flow: Optional[RoleFlow] = None
        self.task_analysis = None
        self.model_routing = None
        self.phase_results: Dict[str, Any] = {}
        self.global_constraints = {}
        
        logger.info(f"WorkflowOrchestratorV3Final initialized")
    
    def execute_full_workflow(self, task_description: str) -> Dict[str, Any]:
        """
        执行完整工作流（严格按照正确顺序）
        
        流程:
        1. 用户输入 (参数)
        2. 项目生成
        3. 定义全局约束
        4. 任务类型检测
        5. 复杂度评估
        6. 角色流程生成（包含模型选择）
        7. 阶段执行循环（网关+执行+审计+重试+决策）
        """
        print("="*70)
        print("🚀 BMAD-EVO v3.0 - 修正流程")
        print("="*70)
        print(f"任务: {task_description[:60]}...")
        print("="*70 + "\n")
        
        # ========== 步骤 1: 项目生成 ==========
        print("📋 Step 1: 项目生成")
        print("-"*70)
        self._generate_project(task_description)
        print(f"✅ 项目生成完成: {self.project_path}")
        
        # ========== 步骤 2: 定义全局约束 ==========
        print("\n📋 Step 2: 定义全局约束")
        print("-"*70)
        self._define_global_constraints()
        print("✅ 全局约束定义完成")
        
        # ========== 步骤 3: 任务类型检测 ==========
        print("\n📋 Step 3: 任务类型检测")
        print("-"*70)
        self.task_analysis = self.task_analyzer.analyze(task_description)
        print(f"✅ 任务类型检测完成: {self.task_analysis.task_type}")
        
        # ========== 步骤 4: 复杂度评估 ==========
        print("\n📋 Step 4: 复杂度评估")
        print("-"*70)
        print(f"✅ 复杂度评估完成: {self.task_analysis.complexity_score}/10")
        print(f"   预估时间: {self.task_analysis.estimated_duration}")
        print(f"   推荐角色数: {self.task_analysis.recommended_roles_count}")
        
        # ========== 步骤 5: 角色流程生成（包含模型选择） ==========
        print("\n📋 Step 5: 角色流程生成（包含模型选择）")
        print("-"*70)
        
        # 5.1 生成角色
        self.role_flow = self.role_generator.generate(
            task_description=task_description,
            task_analysis=self.task_analysis.to_dict()
        )
        
        print(f"✅ 角色生成完成: {self.role_flow.total_roles} 个角色")
        print(f"   执行顺序: {' → '.join(self.role_flow.execution_order)}")
        
        # 5.2 模型选择
        self.model_routing = self.model_router.route(
            roles=[r.to_dict() for r in self.role_flow.roles],
            task_type=self.task_analysis.task_type,
            complexity_score=self.task_analysis.complexity_score
        )
        
        print(f"\n✅ 模型选择完成:")
        for mapping in self.model_routing.mappings:
            print(f"   {mapping.role_id}: {mapping.primary_model}")
        print(f"   预估成本: {self.model_routing.estimated_cost_tier}")
        
        # ========== 步骤 6: 阶段执行循环 ==========
        print("\n" + "="*70)
        print("📋 Step 6: 阶段执行（网关 → 执行 → 审计 → 重试/决策）")
        print("="*70)
        
        all_passed = True
        
        for i, role_name in enumerate(self.role_flow.execution_order):
            role = self._get_role_by_name(role_name)
            if not role:
                continue
            
            print(f"\n{'='*70}")
            print(f"🚀 【阶段网关】启动阶段 {i+1}/{len(self.role_flow.execution_order)}: {role.title}")
            print(f"{'='*70}")
            
            # 执行阶段（包含：执行→审计→重试→决策）
            phase_result = self._execute_phase(role, task_description, i+1)
            self.phase_results[role_name] = phase_result
            
            if not phase_result.get('passed'):
                all_passed = False
                if phase_result.get('aborted'):
                    print(f"\n❌ 工作流中止")
                    break
        
        # ========== 生成最终报告 ==========
        return self._generate_final_report(task_description, all_passed)
    
    def _execute_phase(self, role: RoleDefinition, task_description: str, phase_num: int) -> Dict[str, Any]:
        """
        执行单个阶段
        
        流程:
        【Agent 执行】→ 【强制审计】→ 检查≥85分
        ├── 通过 → 返回成功
        └── 未通过 → 重试(最多3次) → 用户决策
        """
        role_name = role.name
        model_mapping = self._get_model_mapping(role_name)
        
        for attempt in range(1, self.max_retries + 1):
            print(f"\n📍 尝试 {attempt}/{self.max_retries}")
            print(f"   角色: {role.title}")
            if model_mapping:
                print(f"   模型: {model_mapping['primary_model']}")
            
            # 【Agent 执行】调用对应模型角色
            print(f"\n   🤖 【Agent 执行】调用模型...")
            exec_result = self._execute_agent(role, task_description, model_mapping)
            
            print(f"   ⏱️  执行时间: {exec_result.get('execution_time', 0):.2f}s")
            
            # 【强制审计】自动触发
            print(f"\n   🔍 【强制审计】检查中...")
            audit = self._perform_audit(role_name, exec_result.get('output', ''))
            audit_score = self._calculate_audit_score(audit)
            
            print(f"   📊 审计分数: {audit_score}/100 (需要≥{self.pass_threshold})")
            
            if audit.get('violations'):
                for v in audit['violations'][:3]:
                    print(f"      ⚠️  [{v.get('severity', 'MEDIUM')}] {v.get('message', '')[:40]}")
            
            # 检查是否通过（≥85分）
            if audit_score >= self.pass_threshold:
                print(f"   ✅ 审计通过！({audit_score}分)")
                return {
                    'passed': True,
                    'phase': phase_num,
                    'role': role_name,
                    'attempt': attempt,
                    'audit_score': audit_score,
                    'output': exec_result.get('output', '')
                }
            
            # 未通过
            print(f"   ❌ 审计未通过 ({audit_score}分 < {self.pass_threshold}分)")
            
            # 还有重试机会？
            if attempt < self.max_retries:
                print(f"   🔄 准备重试...")
                continue
            
            # 3次重试用尽 → 用户决策
            print(f"\n   🚫 3次尝试均失败，提交用户决策")
            decision = self._user_decision(role, audit, audit_score)
            
            if decision == 'force_proceed':
                print(f"   ⚡ 用户选择强制继续")
                return {'passed': True, 'forced': True, 'audit_score': audit_score}
            elif decision == 'relax_constraint':
                print(f"   🔓 用户选择放宽约束")
                self.pass_threshold = max(60, self.pass_threshold - 10)
                return {'passed': True, 'relaxed': True, 'audit_score': audit_score}
            elif decision == 'manual_fix':
                print(f"   🔧 用户选择手动修复")
                return {'passed': False, 'blocked': True, 'waiting_fix': True}
            else:  # abort
                print(f"   ❌ 用户选择中止")
                return {'passed': False, 'aborted': True}
        
        return {'passed': False}
    
    def _generate_project(self, task_description: str):
        """步骤1: 项目生成"""
        # 创建项目目录结构
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (self.project_path / ".bmad").mkdir(exist_ok=True)
        (self.project_path / ".bmad" / "decisions").mkdir(exist_ok=True)
        (self.project_path / ".bmad" / "checkpoints").mkdir(exist_ok=True)
        (self.project_path / ".bmad" / "reports").mkdir(exist_ok=True)
        (self.project_path / ".bmad" / "constraints").mkdir(exist_ok=True)
        
        # 创建项目元数据
        project_meta = {
            'name': self.project_path.name,
            'task_description': task_description[:200],
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': '3.0'
        }
        
        with open(self.project_path / ".bmad" / "project-meta.json", 'w') as f:
            json.dump(project_meta, f, indent=2, ensure_ascii=False)
    
    def _define_global_constraints(self):
        """步骤2: 定义全局约束"""
        # 默认全局约束
        self.global_constraints = {
            'boundary_check': {
                'check_null': True,
                'check_empty': True
            },
            'exception_handling': {
                'check_io': True,
                'check_network': True,
                'no_bare_except': True
            },
            'code_structure': {
                'max_function_lines': 50,
                'max_file_lines': 500,
                'require_type_hints': False
            },
            'security': {
                'check_secrets': True,
                'no_hardcoded_keys': True
            },
            'audit': {
                'pass_threshold': self.pass_threshold,
                'max_retries': self.max_retries,
                'strict_mode': True
            }
        }
        
        # 保存约束配置
        with open(self.project_path / ".bmad" / "constraints" / "global.json", 'w') as f:
            json.dump(self.global_constraints, f, indent=2, ensure_ascii=False)
    
    def _execute_agent(self, role: RoleDefinition, task_description: str, model_mapping: Dict) -> Dict[str, Any]:
        """
        【Agent 执行】调用对应模型角色
        
        使用 AgentExecutor 执行真实 AI 调用，不再返回模拟数据。
        """
        from agent_executor import AgentExecutor, AgentResult
        
        start_time = time.time()
        
        # 构建上下文（前置角色的输出）
        context = self._build_context(role)
        
        # 选择模型
        model = model_mapping.get('primary_model', 'kimi-coding/k2p5') if model_mapping else 'kimi-coding/k2p5'
        
        # 使用 AgentExecutor 执行真实调用
        try:
            executor = AgentExecutor(
                project_path=self.project_path,
                mode="openclaw"  # 使用 OpenClaw 模式进行真实调用
            )
            
            # 执行 agent 任务
            result: AgentResult = executor.execute(
                phase=role.name,
                context=f"Task: {task_description}\n\nContext:\n{context}"
            )
            
            return {
                'output': result.output,
                'model': result.model_used,
                'execution_time': result.execution_time,
                'success': result.success,
                'error': result.error,
                'token_usage': result.token_usage
            }
            
        except Exception as e:
            logger.error(f"Agent execution failed for role {role.name}: {e}")
            # 执行失败，返回错误信息
            return {
                'output': '',
                'model': model,
                'execution_time': time.time() - start_time,
                'success': False,
                'error': str(e)
            }
    
    def _perform_audit(self, role_name: str, output: str) -> Dict:
        """【强制审计】自动触发"""
        audit_result = self.auditor.audit(
            output=output,
            phase=role_name
        )
        
        # 统一返回格式
        violations = []
        for v in audit_result.violations:
            violations.append({
                'severity': v.severity.value if hasattr(v.severity, 'value') else str(v.severity),
                'message': v.description,
                'rule': v.constraint_type.value if hasattr(v.constraint_type, 'value') else str(v.constraint_type)
            })
        
        return {
            'violations': violations,
            'score': audit_result.score,
            'passed': audit_result.passed,
            'raw_result': audit_result
        }
    
    def _calculate_audit_score(self, audit: Dict) -> int:
        """计算审计分数"""
        # 直接使用 audit 返回的 score
        return audit.get('score', 0)
    
    def _user_decision(self, role: RoleDefinition, audit: Dict, score: int) -> str:
        """用户决策"""
        if not self.interactive:
            return 'abort'
        
        print(f"\n{'='*70}")
        print("🚫 阶段阻塞 - 需要用户决策")
        print(f"{'='*70}")
        print(f"角色: {role.title}")
        print(f"审计分数: {score}/100 (需要≥{self.pass_threshold})")
        print(f"\n违规项:")
        for v in audit.get('violations', [])[:5]:
            print(f"  - [{v['severity']}] {v['message'][:50]}")
        
        print(f"\n选项:")
        print(f"  1. manual_fix   - 手动修复后重试")
        print(f"  2. relax        - 放宽约束继续")
        print(f"  3. force        - 强制继续")
        print(f"  4. abort        - 中止工作流")
        
        choice = input("\n请选择 (1/2/3/4): ").strip()
        
        mapping = {'1': 'manual_fix', '2': 'relax_constraint', '3': 'force_proceed', '4': 'abort'}
        return mapping.get(choice, 'abort')
    
    def _get_role_by_name(self, name: str) -> Optional[RoleDefinition]:
        """根据名称获取角色"""
        if not self.role_flow:
            return None
        for role in self.role_flow.roles:
            if role.name == name:
                return role
        return None
    
    def _get_model_mapping(self, role_name: str) -> Optional[Dict]:
        """获取角色的模型映射"""
        if not self.model_routing:
            return None
        for mapping in self.model_routing.mappings:
            if mapping.role_id == role_name:
                return {
                    'primary_model': mapping.primary_model,
                    'fallback_models': mapping.fallback_models
                }
        return None
    
    def _build_context(self, role: RoleDefinition) -> str:
        """构建执行上下文"""
        context_parts = []
        for input_role in role.input_from:
            if input_role in self.phase_results:
                result = self.phase_results[input_role]
                context_parts.append(f"【来自{input_role}】\n{result.get('output', '')}")
        return "\n\n".join(context_parts)
    
    def _generate_final_report(self, task_description: str, all_passed: bool) -> Dict[str, Any]:
        """生成最终报告"""
        print("\n" + "="*70)
        print("📊 工作流执行总结")
        print("="*70)
        
        total_phases = len(self.role_flow.execution_order) if self.role_flow else 0
        completed = sum(1 for p in self.phase_results.values() if p.get('passed'))
        
        print(f"\n任务: {task_description[:50]}...")
        print(f"总阶段: {total_phases}")
        print(f"通过: {completed}")
        
        for role_name in self.role_flow.execution_order if self.role_flow else []:
            result = self.phase_results.get(role_name, {})
            role = self._get_role_by_name(role_name)
            status = "✅" if result.get('passed') else "❌"
            print(f"   {status} {role.title if role else role_name}")
        
        return {
            'success': all_passed,
            'total_phases': total_phases,
            'completed_phases': completed,
            'phase_results': self.phase_results
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='BMAD-EVO v3.0 最终流程')
    parser.add_argument('--project', default='./test_project', help='Project path')
    parser.add_argument('task', help='Task description')
    args = parser.parse_args()
    
    orchestrator = WorkflowOrchestratorV3Final(project_path=args.project)
    result = orchestrator.execute_full_workflow(args.task)
    
    print("\n最终结果:", json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
