"""
BMAD-EVO Workflow Orchestrator
Phase 2: Complete workflow orchestration with audit integration

Provides:
- End-to-end workflow management
- Automatic phase transition with audit
- Retry coordination
- User decision handling
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
sys.path.insert(0, str(Path(__file__).parent))

from constraint_auditor import ConstraintAuditor
from phase_gateway import PhaseGateway
from decision_interface import DecisionInterface


class WorkflowOrchestrator:
    """
    Orchestrates complete BMAD-EVO workflow with constraint auditing
    
    Workflow:
    1. Start phase (via gateway)
    2. Execute phase (external)
    3. Audit output (via auditor)
    4. Handle result:
       - Pass → Proceed to next phase
       - Fail + retries left → Retry with feedback
       - Fail + no retries → User decision
    5. Record all decisions and outcomes
    """
    
    def __init__(self, project_path: str, interactive: bool = True):
        self.project_path = Path(project_path)
        self.interactive = interactive
        
        # Initialize components
        self.gateway = PhaseGateway(project_path)
        self.auditor = ConstraintAuditor(project_path)
        self.decision_interface = DecisionInterface(project_path)
        
        # Phase execution handlers (can be customized)
        self.phase_handlers = {
            "analyst": self._execute_analyst,
            "pm": self._execute_pm,
            "architect": self._execute_architect,
            "ux": self._execute_ux,
            "development": self._execute_development,
            "qa": self._execute_qa,
            "deployment": self._execute_deployment
        }
    
    def run_workflow(self, phases: Optional[List[str]] = None, strict: bool = True) -> bool:
        """
        Run complete workflow
        
        Args:
            phases: List of phases to run (default: all)
            strict: If False, don't block on audit failure
            
        Returns:
            True if workflow completed successfully
        """
        if phases is None:
            phases = ["analyst", "pm", "architect", "development", "qa"]
        
        print("="*70)
        print("🚀 BMAD-EVO Workflow Orchestrator v2.0")
        print("="*70)
        print(f"Project: {self.project_path}")
        print(f"Mode: {'STRICT (audit required)' if strict else 'PERMISSIVE'}")
        print(f"Phases: {' → '.join(phases)}")
        print("="*70 + "\n")
        
        for phase in phases:
            success = self._run_phase(phase, strict)
            if not success:
                print(f"\n❌ Workflow halted at phase: {phase}")
                return False
        
        print("\n" + "="*70)
        print("✅ WORKFLOW COMPLETED SUCCESSFULLY")
        print("="*70)
        return True
    
    def _run_phase(self, phase: str, strict: bool) -> bool:
        """Run a single phase with full audit cycle"""
        print(f"\n{'='*70}")
        print(f"📍 PHASE: {phase.upper()}")
        print("="*70)
        
        # 1. Start phase
        if not self.gateway.start_phase(phase):
            return False
        
        # 2. Execute phase
        print(f"\n▶️  Executing {phase}...")
        output = self._execute_phase(phase)
        
        if output is None:
            print(f"❌ Phase {phase} execution failed")
            return False
        
        # Save output
        output_file = self._save_phase_output(phase, output)
        print(f"📝 Output saved: {output_file}")
        
        # 3. Audit output
        if not strict:
            print("⏭️  Permissive mode: skipping audit")
            return True
        
        return self._audit_with_retry(phase, output)
    
    def _audit_with_retry(self, phase: str, output: str) -> bool:
        """Audit with automatic retry and user decision"""
        max_retries = 3
        attempt = 0
        
        while attempt < max_retries:
            attempt += 1
            print(f"\n🔍 Audit attempt {attempt}/{max_retries}")
            
            # Run audit
            result = self.auditor.audit(output, phase, attempt)
            
            if result.passed:
                print(f"✅ Audit passed! Score: {result.score}/100")
                return True
            
            # Failed - check if we should retry
            should_retry, model_hint = self.auditor.should_retry(result, attempt)
            
            if should_retry and attempt < max_retries:
                print(f"⏳ Audit failed ({result.score}/100). Retrying...")
                if model_hint == "glm5":
                    print("🔄 Switching to GLM-5 for retry...")
                    # In real implementation, would switch model here
                
                # Get feedback for retry
                feedback = self.auditor.get_retry_feedback(result)
                print(f"\n💡 Feedback for retry:\n{feedback[:500]}...")
                
                # In real implementation, would re-execute with feedback
                # For now, assume output stays same (user needs to fix)
                if self.interactive:
                    input("\n⏸️  Press Enter after fixing the issues...")
                    # Re-read output if file changed
                    output_file = self.project_path / ".bmad" / f"{phase}-output.txt"
                    if output_file.exists():
                        output = output_file.read_text(encoding='utf-8')
            else:
                # No more retries - user decision required
                break
        
        # Exhausted retries - user decision
        if self.interactive:
            return self._handle_user_decision(phase, result)
        else:
            print(f"❌ Audit failed after {max_retries} attempts. Non-interactive mode.")
            return False
    
    def _handle_user_decision(self, phase: str, result) -> bool:
        """Handle user decision when audit fails"""
        print(f"\n🚫 All retry attempts exhausted for {phase}")
        
        # Use decision interface
        choice = self.decision_interface.present_blocked_phase(
            phase, result, 3, ""  # 3 attempts exhausted
        )
        
        # Process decision via gateway
        gateway_result = self.gateway.user_decision(phase, choice)
        
        print(f"\n📋 Decision result: {gateway_result['message']}")
        
        if choice == "manual_fix":
            # Wait for user to fix
            input("\n⏸️  Fix the issues and press Enter to re-audit...")
            
            # Re-read and re-audit
            output_file = self.project_path / ".bmad" / f"{phase}-output.txt"
            if output_file.exists():
                output = output_file.read_text(encoding='utf-8')
                return self._audit_with_retry(phase, output)
            return False
        
        elif choice == "relax_constraint":
            print("📝 Creating relaxed constraints...")
            # Would create new auditor with relaxed constraints
            # For now, just retry once
            return self._audit_with_retry(phase, output)
        
        elif choice == "force_proceed":
            print("⚠️  Forcing proceed with acknowledged quality risk")
            return True
        
        elif choice == "abort":
            print("❌ Phase aborted")
            return False
        
        return False
    
    def _execute_phase(self, phase: str) -> Optional[str]:
        """Execute phase and return output"""
        handler = self.phase_handlers.get(phase)
        if handler:
            return handler()
        
        # Default: look for output file
        output_file = self.project_path / ".bmad" / f"{phase}-output.txt"
        if output_file.exists():
            return output_file.read_text(encoding='utf-8')
        
        print(f"⚠️  No handler for phase {phase} and no output file found")
        return None
    
    def _save_phase_output(self, phase: str, output: str) -> str:
        """Save phase output to file"""
        output_file = self.project_path / ".bmad" / f"{phase}-output.txt"
        output_file.write_text(output, encoding='utf-8')
        return str(output_file)
    
    # Phase-specific executors (placeholders for actual implementation)
    def _execute_analyst(self) -> Optional[str]:
        """Execute analyst phase"""
        # In real implementation, would spawn agent
        return self._read_or_prompt("analyst")
    
    def _execute_pm(self) -> Optional[str]:
        return self._read_or_prompt("pm")
    
    def _execute_architect(self) -> Optional[str]:
        return self._read_or_prompt("architect")
    
    def _execute_ux(self) -> Optional[str]:
        return self._read_or_prompt("ux")
    
    def _execute_development(self) -> Optional[str]:
        return self._read_or_prompt("development")
    
    def _execute_qa(self) -> Optional[str]:
        return self._read_or_prompt("qa")
    
    def _execute_deployment(self) -> Optional[str]:
        return self._read_or_prompt("deployment")
    
    def _read_or_prompt(self, phase: str) -> Optional[str]:
        """Read output file or prompt user"""
        output_file = self.project_path / ".bmad" / f"{phase}-output.txt"
        if output_file.exists():
            return output_file.read_text(encoding='utf-8')
        
        if self.interactive:
            print(f"\n⚠️  Please provide output for phase '{phase}'")
            print(f"   Option 1: Create file: {output_file}")
            print(f"   Option 2: Enter content below (Ctrl+D when done):")
            
            try:
                content = sys.stdin.read()
                if content.strip():
                    output_file.write_text(content, encoding='utf-8')
                    return content
            except EOFError:
                pass
        
        return None
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status"""
        return {
            "gateway": self.gateway.get_phase_status(),
            "decisions": len(self.decision_interface.get_decision_history(limit=100)),
            "audits": len(self.auditor.report_generator.get_audit_history(limit=100))
        }


def main():
    """CLI for workflow orchestrator"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="BMAD-EVO Workflow Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full workflow
  python workflow_orchestrator.py run --project ./my-project --strict
  
  # Run specific phases
  python workflow_orchestrator.py run --phases development qa
  
  # Non-interactive mode (CI/CD)
  python workflow_orchestrator.py run --project ./my-project --strict --no-interactive
  
  # Check status
  python workflow_orchestrator.py status --project ./my-project
        """
    )
    
    parser.add_argument("--project", default=".", help="Project path")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode (audit required)")
    parser.add_argument("--no-interactive", action="store_true", help="Non-interactive mode")
    parser.add_argument("--phases", nargs="+", help="Specific phases to run")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run workflow")
    
    # Status command
    subparsers.add_parser("status", help="Show workflow status")
    
    args = parser.parse_args()
    
    if args.command == "run" or args.command is None:
        orchestrator = WorkflowOrchestrator(
            args.project,
            interactive=not args.no_interactive
        )
        
        success = orchestrator.run_workflow(
            phases=args.phases,
            strict=args.strict
        )
        
        sys.exit(0 if success else 1)
    
    elif args.command == "status":
        orchestrator = WorkflowOrchestrator(args.project)
        status = orchestrator.get_workflow_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
