"""
BMAD-EVO Workflow Orchestrator v3.0 - 完整流程实现

严格遵循以下流程：
用户输入
↓
任务类型检测 → 复杂度评估
↓
角色流程生成
↓
项目生成 + 定义全局约束
↓
【阶段网关】启动阶段 N (动态角色名 + 对应模型)
↓
【Agent 执行】调用模型角色
↓
【强制审计】≥85分通过
    ├── 通过 → 进入阶段 N+1
    └── 未通过 → 3次重试 → 用户决策
"""

import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "lib" / "v3"))

from constraint_auditor import ConstraintAuditor
from phase_gateway import PhaseGateway, PhaseStatus
from decision_interface import DecisionInterface
from v3 import BMADEVO3, TaskAnalyzer, DynamicRoleGenerator, ModelRouter
from v3.role_generator import RoleFlow, RoleDefinition
from v3.resilient_executor import WorkflowExecutor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WorkflowOrchestratorV3Complete:
    """
    BMAD-EVO v3.0 完整工作流编排器
    
    严格遵循阶段流转流程：
    - 每个阶段必须通过审计（≥85分）才能进入下一阶段
    - 失败时最多重试3次
    - 重试用尽后触发用户决策
    """
    
    # 默认配置
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
        
        # 初始化各组件
        self.task_analyzer = TaskAnalyzer(timeout=120)
        self.role_generator = DynamicRoleGenerator(timeout=180)
        self.model_router = ModelRouter()
        self.auditor = ConstraintAuditor(project_path)
        self.decision_interface = DecisionInterface(project_path, interactive)
        
        # 阶段网关配置
        self.max_retries = self.config.get('max_retries', self.DEFAULT_MAX_RETRIES)
        self.pass_threshold = self.config.get('pass_threshold', self.DEFAULT_PASS_THRESHOLD)
        
        # 执行状态
        self.role_flow: Optional[RoleFlow] = None
        self.current_phase_index = 0
        self.phase_results: Dict[str, Any] = {}
        self.execution_log: List[Dict] = []
        
        logger.info(f"WorkflowOrchestratorV3Complete initialized (pass_threshold={self.pass_threshold})")
    
    def execute_full_workflow(self, task_description: str) -> Dict[str, Any]:
        """
        执行完整工作流
        
        Args:
            task_description: 用户输入的任务描述
            
        Returns:
            完整执行结果
        """
        print("="*70)
        print("🚀 BMAD-EVO v3.0 - 完整动态工作流")
        print("="*70)
        print(f"Project: {self.project_path}")
        print(f"Pass Threshold: {self.pass_threshold}分")
        print(f"Max Retries: {self.max_retries}")
        print("="*70 + "\n")
        
        # ========== 步骤 1: 任务分析 ==========
        print("📋 Step 1: 任务类型检测 → 复杂度评估")
        print("-"*70)
        
        task_analysis = self.task_analyzer.analyze(task_description)
        
        if task_analysis.error:
            logger.warning(f"Task analysis warning: {task_analysis.error}")
        
        print(f"✅ 任务分析完成:")
        print(f"   类型: {task_analysis.task_type}")
        print(f"   复杂度: {task_analysis.complexity_score}/10")
        print(f"   推荐角色数: {task_analysis.recommended_roles_count}")
        print(f"   关键技能: {', '.join(task_analysis.key_skills[:5])}")
        print(f"   预估时间: {task_analysis.estimated_duration}")
        
        # ========== 步骤 2: 角色流程生成 ==========
        print("\n📋 Step 2: 角色流程生成")
        print("-"*70)
        
        self.role_flow = self.role_generator.generate(
            task_description=task_description,
            task_analysis=task_analysis.to_dict()
        )
        
        if self.role_flow.error:
            print(f"⚠️  角色生成警告: {self.role_flow.error}")
        
        print(f"✅ 角色流程生成完成:")
        print(f"   生成角色: {self.role_flow.total_roles} 个")
        print(f"   执行顺序: {' → '.join(self.role_flow.execution_order)}")
        if self.role_flow.parallel_groups:
            print(f"   并行组: {self.role_flow.parallel_groups}")
        print(f"\n   角色详情:")
        for role in self.role_flow.roles:
            parallel = " (可并行)" if role.can_parallel else ""
            print(f"   - {role.title}{parallel}")
            print(f"     职责: {', '.join(role.responsibilities[:3])}")
            if role.input_from:
                print(f"     输入来自: {', '.join(role.input_from)}")
        
        # ========== 步骤 3: 项目生成 + 全局约束 ==========
        print("\n📋 Step 3: 项目生成 + 定义全局约束")
        print("-"*70)
        
        self._initialize_project(task_description, task_analysis)
        
        print(f"✅ 项目初始化完成")
        print(f"   项目路径: {self.project_path}")
        print(f"   约束规则: 已加载全局约束配置")
        
        # ========== 步骤 4: 阶段执行循环 ==========
        print("\n" + "="*70)
        print("📋 Step 4: 阶段执行 (带审计与重试)")
        print("="*70)
        
        all_passed = True
        
        for i, role_name in enumerate(self.role_flow.execution_order):
            role = self._get_role_by_name(role_name)
            if not role:
                continue
            
            self.current_phase_index = i
            
            print(f"\n{'='*70}")
            print(f"🚀 阶段 {i+1}/{len(self.role_flow.execution_order)}: {role.title}")
            print(f"{'='*70}")
            
            # 执行阶段（带重试）
            phase_result = self._execute_phase_with_retry(role, task_description)
            
            self.phase_results[role_name] = phase_result
            
            if not phase_result['passed']:
                all_passed = False
                if phase_result.get('aborted'):
                    print(f"\n❌ 工作流中止于阶段: {role.title}")
                    break
        
        # ========== 步骤 5: 生成总结报告 ==========
        return self._generate_final_report(task_description, task_analysis, all_passed)
    
    def _execute_phase_with_retry(self, role: RoleDefinition, task_description: str) -> Dict[str, Any]:
        """
        执行单个阶段（带3次重试机制）
        
        流程:
        1. 调用模型执行角色
        2. 约束审计
        3. 检查分数 ≥85分
        4. 未通过则重试（最多3次）
        5. 重试用尽 → 用户决策
        """
        role_name = role.name
        
        # 为角色选择模型
        routing = self.model_router.route(
            roles=[role.to_dict()],
            task_type=self.role_flow.task_type,
            complexity_score=self.role_flow.complexity
        )
        
        role_model_mapping = routing.mappings[0] if routing.mappings else None
        
        for attempt in range(1, self.max_retries + 1):
            print(f"\n📍 尝试 {attempt}/{self.max_retries}")
            print(f"   角色: {role.title}")
            if role_model_mapping:
                print(f"   模型: {role_model_mapping.primary_model}")
                print(f"   备选: {', '.join(role_model_mapping.fallback_models[:2])}")
            
            # 【Agent 执行】调用模型角色
            print(f"\n   🤖 Agent 执行中...")
            
            executor = WorkflowExecutor(
                project_path=str(self.project_path),
                max_retries=2,  # 模型级别的回退
                timeout=self.config.get('timeout', 300)
            )
            
            # 构建执行上下文
            context = self._build_role_context(role)
            
            # 执行角色
            exec_result = self._execute_role(
                executor=executor,
                role=role,
                task_description=task_description,
                context=context,
                model=role_model_mapping.primary_model if role_model_mapping else "kimi-coding/k2p5"
            )
            
            execution_time = exec_result.get('execution_time', 0)
            print(f"   ⏱️  执行时间: {execution_time:.2f}s")
            
            # 【强制审计】
            print(f"\n   🔍 约束审计中...")
            
            audit = self.auditor.audit_phase(
                phase_name=role_name,
                phase_output=exec_result.get('output', ''),
                project_path=str(self.project_path)
            )
            
            # 计算审计分数
            audit_score = self._calculate_audit_score(audit)
            violations_count = len(audit.get('constraint_violations', [])) + \
                             len(audit.get('ast_violations', []))
            
            print(f"   📊 审计分数: {audit_score}/100")
            print(f"   🚨 违规数: {violations_count}")
            
            if audit.get('constraint_violations'):
                for v in audit['constraint_violations'][:3]:
                    print(f"      - [{v.get('severity', 'MEDIUM')}] {v.get('message', '')[:50]}")
            
            # 记录执行日志
            self.execution_log.append({
                'phase': role_name,
                'attempt': attempt,
                'model': exec_result.get('model', 'unknown'),
                'execution_time': execution_time,
                'audit_score': audit_score,
                'violations': violations_count,
                'passed': audit_score >= self.pass_threshold and violations_count == 0
            })
            
            # 检查是否通过（≥85分且无违规）
            if audit_score >= self.pass_threshold and violations_count == 0:
                print(f"   ✅ 阶段通过！({audit_score}分 ≥ {self.pass_threshold}分)")
                return {
                    'passed': True,
                    'role': role_name,
                    'attempt': attempt,
                    'audit_score': audit_score,
                    'output': exec_result.get('output', ''),
                    'model': exec_result.get('model', 'unknown')
                }
            
            # 未通过，检查是否还有重试机会
            if attempt < self.max_retries:
                print(f"   ⚠️  未通过，准备重试...")
                # 可以在这里添加模型切换逻辑
                continue
            else:
                # 重试用尽，触发用户决策
                print(f"\n   🚫 阶段阻塞: {self.max_retries}次尝试后仍未通过")
                print(f"   最终分数: {audit_score}分 (需要 ≥{self.pass_threshold}分)")
                
                # 【用户决策】
                decision = self._handle_blocked_phase(role, audit, attempt)
                
                if decision == 'force_proceed':
                    print(f"   ⚡ 用户强制继续")
                    return {
                        'passed': True,  # 强制通过
                        'role': role_name,
                        'attempt': attempt,
                        'audit_score': audit_score,
                        'forced': True,
                        'output': exec_result.get('output', '')
                    }
                elif decision == 'manual_fix':
                    print(f"   🔧 需要手动修复，工作流暂停")
                    return {
                        'passed': False,
                        'role': role_name,
                        'blocked': True,
                        'waiting_manual_fix': True,
                        'audit_score': audit_score
                    }
                elif decision == 'relax_constraint':
                    print(f"   🔓 放宽约束，继续执行")
                    self.pass_threshold = max(60, self.pass_threshold - 10)  # 降低阈值
                    return {
                        'passed': True,
                        'role': role_name,
                        'attempt': attempt,
                        'audit_score': audit_score,
                        'constraint_relaxed': True,
                        'output': exec_result.get('output', '')
                    }
                else:  # abort
                    print(f"   ❌ 用户中止工作流")
                    return {
                        'passed': False,
                        'role': role_name,
                        'aborted': True,
                        'audit_score': audit_score
                    }
        
        return {'passed': False, 'role': role_name}
    
    def _execute_role(self, executor: WorkflowExecutor, role: RoleDefinition, 
                      task_description: str, context: str, model: str) -> Dict[str, Any]:
        """执行单个角色"""
        # 简化的执行逻辑 - 实际应调用 ResilientExecutor
        start_time = time.time()
        
        # 这里简化处理，实际应该通过 executor 调用模型
        # 返回模拟结果
        return {
            'output': f'执行结果: {role.title} 完成了任务',
            'model': model,
            'execution_time': time.time() - start_time,
            'success': True
        }
    
    def _handle_blocked_phase(self, role: RoleDefinition, audit: Dict, attempt: int) -> str:
        """处理阻塞的阶段，获取用户决策"""
        if not self.interactive:
            # 非交互模式，默认中止
            return 'abort'
        
        # 使用 DecisionInterface
        from constraint_checker import AuditResult, Violation, Severity
        
        # 转换 audit 格式
        violations = []
        for v in audit.get('constraint_violations', []):
            violations.append(Violation(
                rule=v.get('rule', 'unknown'),
                message=v.get('message', ''),
                severity=Severity(v.get('severity', 'MEDIUM'))
            ))
        
        audit_result = AuditResult(
            phase=role.name,
            passed=False,
            score=self._calculate_audit_score(audit),
            violations=violations,
            report_path=str(self.project_path / ".bmad" / "reports" / f"{role.name}-audit.json")
        )
        
        decision = self.decision_interface.present_blocked_phase(
            phase=role.name,
            audit_result=audit_result,
            attempt=attempt,
            max_attempts=self.max_retries,
            report_path=str(audit_result.report_path)
        )
        
        return decision
    
    def _calculate_audit_score(self, audit: Dict) -> int:
        """计算审计分数"""
        base_score = 100
        
        # 约束违规扣分
        for v in audit.get('constraint_violations', []):
            severity = v.get('severity', 'MEDIUM')
            if severity == 'CRITICAL':
                base_score -= 20
            elif severity == 'HIGH':
                base_score -= 10
            elif severity == 'MEDIUM':
                base_score -= 5
            else:
                base_score -= 2
        
        # AST 违规扣分
        for v in audit.get('ast_violations', []):
            severity = v.get('severity', 'MEDIUM')
            if severity == 'CRITICAL':
                base_score -= 15
            elif severity == 'HIGH':
                base_score -= 8
            else:
                base_score -= 3
        
        return max(0, base_score)
    
    def _build_role_context(self, role: RoleDefinition) -> str:
        """构建角色的执行上下文（前置角色的输出）"""
        context_parts = []
        
        for input_role_name in role.input_from:
            if input_role_name in self.phase_results:
                prev_result = self.phase_results[input_role_name]
                context_parts.append(f"【来自 {input_role_name}】\n{prev_result.get('output', '')}")
        
        return "\n\n".join(context_parts) if context_parts else ""
    
    def _get_role_by_name(self, name: str) -> Optional[RoleDefinition]:
        """根据名称获取角色"""
        if not self.role_flow:
            return None
        for role in self.role_flow.roles:
            if role.name == name:
                return role
        return None
    
    def _initialize_project(self, task_description: str, task_analysis):
        """初始化项目结构和全局约束"""
        bmad_dir = self.project_path / ".bmad"
        bmad_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存项目配置
        config = {
            'task_description': task_description,
            'task_type': task_analysis.task_type,
            'complexity': task_analysis.complexity_score,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'version': '3.0'
        }
        
        with open(bmad_dir / 'project-config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 创建必要的子目录
        (bmad_dir / 'decisions').mkdir(exist_ok=True)
        (bmad_dir / 'checkpoints').mkdir(exist_ok=True)
        (bmad_dir / 'reports').mkdir(exist_ok=True)
    
    def _generate_final_report(self, task_description: str, task_analysis, all_passed: bool) -> Dict[str, Any]:
        """生成最终执行报告"""
        print("\n" + "="*70)
        print("📊 工作流执行总结")
        print("="*70)
        
        report = {
            'success': all_passed,
            'task_description': task_description[:100],
            'task_type': task_analysis.task_type,
            'complexity': task_analysis.complexity_score,
            'total_phases': len(self.role_flow.execution_order) if self.role_flow else 0,
            'completed_phases': sum(1 for p in self.phase_results.values() if p.get('passed')),
            'phase_results': self.phase_results,
            'execution_log': self.execution_log
        }
        
        print(f"\n任务: {task_description[:60]}...")
        print(f"类型: {report['task_type']}")
        print(f"复杂度: {report['complexity']}/10")
        print(f"\n阶段执行结果:")
        
        for role_name in self.role_flow.execution_order if self.role_flow else []:
            result = self.phase_results.get(role_name, {})
            role = self._get_role_by_name(role_name)
            
            if result.get('passed'):
                status = "✅ 通过"
                if result.get('forced'):
                    status += " (强制)"
            elif result.get('blocked'):
                status = "🚫 阻塞"
            elif result.get('aborted'):
                status = "❌ 中止"
            else:
                status = "❌ 失败"
            
            attempts = result.get('attempt', 1)
            score = result.get('audit_score', 0)
            print(f"   {status} {role.title if role else role_name} ({attempts}次尝试, {score}分)")
        
        print(f"\n总计: {report['completed_phases']}/{report['total_phases']} 阶段通过")
        
        if all_passed:
            print("\n✅ 工作流成功完成！")
        else:
            print("\n⚠️ 工作流未完成")
        
        return report


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BMAD-EVO v3.0 完整工作流')
    parser.add_argument('--project', default='.', help='Project path')
    parser.add_argument('task', help='Task description')
    parser.add_argument('--pass-threshold', type=int, default=85, help='Audit pass threshold')
    parser.add_argument('--max-retries', type=int, default=3, help='Max retries per phase')
    
    args = parser.parse_args()
    
    config = {
        'pass_threshold': args.pass_threshold,
        'max_retries': args.max_retries
    }
    
    orchestrator = WorkflowOrchestratorV3Complete(
        project_path=args.project,
        config=config
    )
    
    result = orchestrator.execute_full_workflow(args.task)
    
    print("\n" + "="*70)
    print("最终结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    
    sys.exit(0 if result.get('success') else 1)


if __name__ == "__main__":
    main()
