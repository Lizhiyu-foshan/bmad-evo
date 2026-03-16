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
    
    def __init__(self, project_path: str, interactive: bool = True, config: Optional[Dict[str, Any]] = None):
        self.project_path = Path(project_path)
        self.interactive = interactive
        
        # Initialize components
        self.gateway = PhaseGateway(project_path, config)
        self.auditor = ConstraintAuditor(project_path)
        self.decision_interface = DecisionInterface(project_path, interactive)
        
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
        
        # Configuration
        self.config = config or {}
        self.max_retries = self.config.get('max_retries', 3)
    
    def run_workflow(self, phases: Optional[List[str]] = None, strict: bool = True, resume: bool = False) -> bool:
        """
        Run complete workflow
        
        Args:
            phases: List of phases to run (default: all)
            strict: If False, don't block on audit failure
            resume: If True, resume from last checkpoint
            
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
        if resume:
            print(f"Resume: Yes (from last checkpoint)")
        print("="*70 + "\n")
        
        # If resuming, find where to restart
        start_index = 0
        if resume:
            start_index = self._find_resume_point(phases)
            if start_index > 0:
                print(f"⏩ Resuming from phase: {phases[start_index]}")
        
        for i, phase in enumerate(phases):
            if i < start_index:
                print(f"⏭️  Skipping completed phase: {phase}")
                continue
                
            success = self._run_phase(phase, strict)
            if not success:
                print(f"\n❌ Workflow halted at phase: {phase}")
                return False
            
            # Save checkpoint after each successful phase
            self._save_checkpoint(phase)
        
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
        """
        Audit with automatic retry coordinated with PhaseGateway
        
        Delegates retry logic to PhaseGateway to avoid duplication.
        PhaseGateway tracks attempts and determines when to block for user decision.
        
        Returns:
            True if audit passed or user forced proceed, False otherwise
        """
        attempt = 0
        
        while True:
            attempt += 1
            print(f"\n🔍 Audit attempt {attempt}/{self.max_retries}")
            
            # Run audit
            result = self.auditor.audit(output, phase, attempt)
            
            # Complete phase via gateway (gateway determines next action)
            gateway_result = self.gateway.complete_phase(phase, result, attempt)
            
            action = gateway_result['action']
            
            if action == "proceed":
                print(f"✅ {gateway_result['message']}")
                return True
            
            elif action == "retry":
                # Gateway says retry - get feedback and continue
                if attempt < self.max_retries:
                    feedback = self.auditor.get_retry_feedback(result)
                    print(f"\n⏳ {gateway_result['message']}")
                    print(f"\n💡 Feedback for retry:\n{feedback[:500]}...")
                    
                    # In interactive mode, wait for user to fix
                    if self.interactive:
                        input("\n⏸️  Press Enter after fixing the issues (or Ctrl+C to abort)...")
                        # Re-read output if file changed
                        output_file = self.project_path / ".bmad" / f"{phase}-output.txt"
                        if output_file.exists():
                            output = output_file.read_text(encoding='utf-8')
                    # In non-interactive mode, retry with same output (will fail again unless externally fixed)
                else:
                    # Shouldn't reach here - gateway should have returned "block"
                    break
            
            elif action == "block":
                # All retries exhausted - user decision required
                print(f"\n🚫 {gateway_result['message']}")
                if self.interactive:
                    return self._handle_user_decision(phase, result)
                else:
                    print(f"❌ Non-interactive mode: audit failed after {attempt} attempts")
                    return False
            
            elif action == "error":
                print(f"❌ Gateway error: {gateway_result.get('message', 'Unknown error')}")
                return False
        
        return False
    
    def _handle_user_decision(self, phase: str, result) -> bool:
        """Handle user decision when audit fails"""
        print(f"\n🚫 All retry attempts exhausted for {phase}")
        
        # Get max attempts from gateway config
        max_attempts = self.gateway.MAX_RETRIES
        
        # Use decision interface
        choice = self.decision_interface.present_blocked_phase(
            phase, result, max_attempts, max_attempts, ""  # report_path can be added later
        )
        
        # Process decision via gateway
        gateway_result = self.gateway.user_decision(phase, choice)
        
        print(f"\n📋 Decision result: {gateway_result['message']}")
        
        if choice == "manual_fix":
            # Wait for user to fix
            if self.interactive:
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
            # For now, just retry once with same output
            output_file = self.project_path / ".bmad" / f"{phase}-output.txt"
            if output_file.exists():
                output = output_file.read_text(encoding='utf-8')
                return self._audit_with_retry(phase, output)
            return False
        
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
    
    def _save_checkpoint(self, phase: str):
        """Save checkpoint after phase completion"""
        checkpoint_file = self.gateway.checkpoint_dir / f"{phase}.json"
        checkpoint_data = {
            "phase": phase,
            "completed_at": self.gateway._now(),
            "status": "completed",
            "gateway_state": self.gateway.state.copy()
        }
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Checkpoint saved: {checkpoint_file}")
    
    def _find_resume_point(self, phases: List[str]) -> int:
        """Find the phase to resume from based on checkpoints"""
        if not self.gateway.checkpoint_dir.exists():
            return 0
        
        # Find the last completed phase
        last_completed = None
        for phase in phases:
            checkpoint_file = self.gateway.checkpoint_dir / f"{phase}.json"
            if checkpoint_file.exists():
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('status') == 'completed':
                            last_completed = phase
                except (json.JSONDecodeError, IOError):
                    continue
        
        if last_completed:
            idx = phases.index(last_completed) if last_completed in phases else -1
            return idx + 1  # Start from next phase
        
        return 0


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
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    
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
            strict=args.strict,
            resume=args.resume
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
