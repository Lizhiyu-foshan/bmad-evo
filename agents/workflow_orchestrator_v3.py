"""
BMAD-EVO Workflow Orchestrator v3.0
集成全动态智能生成系统

特性:
- 使用 TaskAnalyzer 动态分析任务
- 使用 DynamicRoleGenerator 生成角色
- 使用 ModelRouter 选择最优模型
- 使用 ResilientExecutor 执行（带回退）
- 与现有约束审计系统集成
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "lib" / "v3"))

from constraint_auditor import ConstraintAuditor
from decision_interface import DecisionInterface
from v3 import BMADEVO3, TaskAnalyzer, DynamicRoleGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WorkflowOrchestratorV3:
    """
    BMAD-EVO v3.0 工作流编排器
    
    完全动态的工作流编排，零硬编码角色
    """
    
    def __init__(
        self,
        project_path: str,
        interactive: bool = True,
        config: Optional[Dict[str, Any]] = None
    ):
        self.project_path = Path(project_path)
        self.interactive = interactive
        self.config = config or {}
        
        # 初始化 v3.0 系统
        self.evo3 = BMADEVO3(
            project_path=project_path,
            timeout=self.config.get('timeout', 300),
            max_retries=self.config.get('max_retries', 3),
            budget_constraint=self.config.get('budget_constraint')
        )
        
        # 初始化约束审计器
        self.auditor = ConstraintAuditor(project_path)
        self.decision_interface = DecisionInterface(project_path, interactive)
        
        # 执行统计
        self.execution_stats = {
            'total_phases': 0,
            'completed_phases': 0,
            'failed_phases': 0,
            'retried_phases': 0,
            'total_execution_time': 0.0
        }
        
        logger.info(f"WorkflowOrchestratorV3 initialized")
    
    def run_workflow(
        self,
        task_description: str,
        strict: bool = True
    ) -> Dict[str, Any]:
        """
        运行动态工作流
        
        Args:
            task_description: 任务描述
            strict: 严格模式（审计失败时阻止继续）
            
        Returns:
            工作流执行结果
        """
        print("="*70)
        print("🚀 BMAD-EVO Workflow Orchestrator v3.0")
        print("="*70)
        print(f"Project: {self.project_path}")
        print(f"Mode: {'STRICT (audit required)' if strict else 'PERMISSIVE'}")
        print(f"Task: {task_description[:60]}...")
        print("="*70 + "\n")
        
        # Step 1: 使用 v3.0 执行任务分析和角色生成
        print("📋 Phase 0: 任务分析与角色生成")
        print("-"*70)
        
        try:
            evo3_result = self.evo3.execute(task_description)
        except Exception as e:
            logger.error(f"v3.0 execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'phase': 'initialization'
            }
        
        if not evo3_result['success']:
            print(f"❌ v3.0 执行失败: {evo3_result.get('error', 'Unknown error')}")
            return evo3_result
        
        # 提取生成的角色
        role_flow = self.evo3.role_flow
        execution_results = self.evo3.execution_results
        
        if not role_flow or not role_flow.roles:
            print("❌ 角色生成失败")
            return {
                'success': False,
                'error': 'Role generation failed',
                'phase': 'role_generation'
            }
        
        # 显示生成的角色
        print(f"\n✅ 任务分析完成:")
        print(f"   类型: {self.evo3.task_analysis.task_type}")
        print(f"   复杂度: {self.evo3.task_analysis.complexity_score}/10")
        print(f"   生成角色: {len(role_flow.roles)} 个")
        print(f"\n   角色列表:")
        for role in role_flow.roles:
            print(f"   - {role.title} ({role.name})")
        
        # Step 2: 为每个角色执行并进行约束审计
        print("\n" + "="*70)
        print("📋 Phase 1-N: 角色执行与约束审计")
        print("="*70)
        
        audit_results = []
        all_passed = True
        
        for role in role_flow.roles:
            role_result = execution_results.get(role.name)
            
            if not role_result:
                print(f"⚠️  角色 {role.name} 无执行结果，跳过")
                continue
            
            print(f"\n🔍 审计角色: {role.title}")
            
            # 获取角色输出
            role_output = role_result.output if role_result.success else ""
            
            # 约束审计
            audit = self.auditor.audit_phase(
                phase_name=role.name,
                phase_output=role_output,
                project_path=str(self.project_path)
            )
            
            audit_results.append({
                'role': role.name,
                'title': role.title,
                'audit': audit,
                'execution_success': role_result.success
            })
            
            # 显示审计结果
            if audit['constraint_violations']:
                print(f"   ⚠️  发现 {len(audit['constraint_violations'])} 个约束违反:")
                for v in audit['constraint_violations']:
                    print(f"      - [{v['severity']}] {v['rule']}: {v['message']}")
                all_passed = False
            else:
                print(f"   ✅ 无约束违反")
            
            if audit['ast_violations']:
                print(f"   ⚠️  AST 发现 {len(audit['ast_violations'])} 个问题:")
                for v in audit['ast_violations'][:3]:  # 只显示前3个
                    print(f"      - [{v['severity']}] {v['message']}")
        
        # Step 3: 生成总结报告
        print("\n" + "="*70)
        print("📊 工作流执行总结")
        print("="*70)
        
        summary = {
            'success': all_passed or not strict,
            'task_type': self.evo3.task_analysis.task_type,
            'complexity': self.evo3.task_analysis.complexity_score,
            'total_roles': len(role_flow.roles),
            'execution_time': evo3_result.get('execution_time', 0),
            'roles': [],
            'audit_summary': {
                'total_audits': len(audit_results),
                'passed': sum(1 for a in audit_results if not a['audit']['constraint_violations']),
                'failed': sum(1 for a in audit_results if a['audit']['constraint_violations'])
            }
        }
        
        for role in role_flow.roles:
            role_exec = execution_results.get(role.name)
            role_audit = next((a for a in audit_results if a['role'] == role.name), None)
            
            summary['roles'].append({
                'name': role.name,
                'title': role.title,
                'success': role_exec.success if role_exec else False,
                'model': role_exec.final_model if role_exec else 'N/A',
                'attempts': role_exec.total_attempts if role_exec else 0,
                'execution_time': role_exec.total_execution_time if role_exec else 0,
                'violations': len(role_audit['audit']['constraint_violations']) if role_audit else 0
            })
        
        # 显示总结
        print(f"\n任务类型: {summary['task_type']}")
        print(f"复杂度: {summary['complexity']}/10")
        print(f"执行时间: {summary['execution_time']:.2f}s")
        print(f"\n角色执行结果:")
        for r in summary['roles']:
            status = "✅" if r['success'] else "❌"
            print(f"   {status} {r['title']}: {r['model']} ({r['attempts']}次尝试)")
        
        print(f"\n约束审计:")
        print(f"   通过: {summary['audit_summary']['passed']}/{summary['audit_summary']['total_audits']}")
        print(f"   失败: {summary['audit_summary']['failed']}/{summary['audit_summary']['total_audits']}")
        
        if all_passed:
            print(f"\n✅ 工作流成功完成！")
        else:
            print(f"\n⚠️  工作流完成，但有约束违反")
        
        return summary


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BMAD-EVO v3.0 Workflow Orchestrator')
    parser.add_argument('--project', default='.', help='Project path')
    parser.add_argument('action', choices=['run'], help='Action')
    parser.add_argument('task', nargs='?', help='Task description')
    parser.add_argument('--strict', action='store_true', help='Strict mode')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout per role')
    parser.add_argument('--max-retries', type=int, default=3, help='Max retries')
    
    args = parser.parse_args()
    
    if args.action == 'run':
        if not args.task:
            # Try to get task from remaining args
            print("Error: Task description required")
            print("Usage: bmad-evo run-v3 'Your task description'")
            sys.exit(1)
        
        config = {
            'timeout': args.timeout,
            'max_retries': args.max_retries
        }
        
        orchestrator = WorkflowOrchestratorV3(
            project_path=args.project,
            config=config
        )
        
        result = orchestrator.run_workflow(args.task, strict=args.strict)
        
        print("\n" + "="*70)
        print("最终结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        
        sys.exit(0 if result.get('success') else 1)


if __name__ == "__main__":
    main()
