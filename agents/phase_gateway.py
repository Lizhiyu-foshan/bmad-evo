"""
BMAD-EVO Phase Gateway
Phase 2: Automatic phase transition interception

Provides:
- Intercept phase transitions and trigger audit
- Block progression if audit fails
- Coordinate with retry mechanism
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from constraint_checker import AuditResult
from audit_report import AuditReportGenerator


class PhaseStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    AUDITING = "auditing"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"  # Waiting for user decision


class PhaseGateway:
    """
    Gatekeeper for phase transitions in BMAD-EVO workflow
    
    Ensures:
    1. Phase output is audited before transition
    2. Audit pass (>=85, no HIGH) required to proceed
    3. Retry logic with model fallback
    4. User decision when all retries exhausted
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.bmad_dir = self.project_path / ".bmad"
        self.state_file = self.bmad_dir / "phase-state.json"
        self.checkpoint_dir = self.bmad_dir / "checkpoints"
        
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Phase definitions
        self.phases = [
            "analyst",
            "pm", 
            "architect",
            "ux",
            "development",
            "qa",
            "deployment"
        ]
        
        self._load_state()
    
    def _load_state(self):
        """Load phase state from disk"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
        else:
            self.state = {
                "current_phase": None,
                "phase_states": {},
                "audit_history": []
            }
    
    def _save_state(self):
        """Save phase state to disk"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def start_phase(self, phase: str) -> bool:
        """
        Start a new phase
        
        Returns:
            True if phase can start, False otherwise
        """
        # Check if previous phase passed audit
        prev_phase = self._get_previous_phase(phase)
        if prev_phase and not self._phase_passed(prev_phase):
            print(f"❌ Cannot start {phase}: previous phase {prev_phase} not passed")
            return False
        
        self.state["current_phase"] = phase
        self.state["phase_states"][phase] = {
            "status": PhaseStatus.IN_PROGRESS.value,
            "started_at": self._now(),
            "attempts": 0
        }
        self._save_state()
        
        print(f"✅ Phase '{phase}' started")
        return True
    
    def complete_phase(self, phase: str, output: str, auditor) -> Dict[str, Any]:
        """
        Complete phase and trigger audit
        
        Args:
            phase: Current phase name
            output: Phase output (code, document, etc.)
            auditor: ConstraintAuditor instance
            
        Returns:
            Result dict with:
            - action: "proceed", "retry", "block", "abort"
            - result: AuditResult
            - message: User-facing message
        """
        phase_state = self.state["phase_states"].get(phase, {})
        attempt = phase_state.get("attempts", 0) + 1
        
        print(f"\n🔒 Phase Gateway: Completing '{phase}' (attempt {attempt})")
        
        # Run audit
        audit_result = auditor.audit(output, phase, attempt)
        
        # Update state
        phase_state["attempts"] = attempt
        phase_state["last_audit"] = {
            "score": audit_result.score,
            "passed": audit_result.passed,
            "timestamp": self._now()
        }
        
        # Determine next action
        if audit_result.passed:
            phase_state["status"] = PhaseStatus.PASSED.value
            self.state["audit_history"].append({
                "phase": phase,
                "attempt": attempt,
                "passed": True,
                "score": audit_result.score
            })
            self._save_state()
            
            return {
                "action": "proceed",
                "result": audit_result,
                "message": f"✅ Phase '{phase}' passed audit ({audit_result.score}/100). Ready to proceed."
            }
        
        # Audit failed - check retry logic
        should_retry, model_hint = auditor.should_retry(audit_result, attempt)
        
        if should_retry:
            phase_state["status"] = PhaseStatus.AUDITING.value
            self._save_state()
            
            feedback = auditor.get_retry_feedback(audit_result)
            
            return {
                "action": "retry",
                "result": audit_result,
                "model_hint": model_hint,
                "feedback": feedback,
                "message": f"⏳ Phase '{phase}' audit failed ({audit_result.score}/100). Retry attempt {attempt+1} recommended."
            }
        
        # All retries exhausted - block for user decision
        phase_state["status"] = PhaseStatus.BLOCKED.value
        self.state["audit_history"].append({
            "phase": phase,
            "attempt": attempt,
            "passed": False,
            "score": audit_result.score
        })
        self._save_state()
        
        return {
            "action": "block",
            "result": audit_result,
            "message": f"🚫 Phase '{phase}' blocked after {attempt} attempts. User decision required.",
            "options": [
                "manual_fix",
                "relax_constraint", 
                "force_proceed",
                "abort"
            ]
        }
    
    def user_decision(self, phase: str, decision: str, auditor=None) -> Dict[str, Any]:
        """
        Handle user decision when phase is blocked
        
        Args:
            phase: Blocked phase name
            decision: User choice (manual_fix, relax_constraint, force_proceed, abort)
            auditor: Optional new auditor with relaxed constraints
            
        Returns:
            Result dict with next action
        """
        phase_state = self.state["phase_states"].get(phase)
        if not phase_state:
            return {"action": "error", "message": f"Phase {phase} not found"}
        
        if decision == "manual_fix":
            # Reset to in_progress, allow user to resubmit
            phase_state["status"] = PhaseStatus.IN_PROGRESS.value
            phase_state["attempts"] = 0  # Reset attempts for fresh start
            self._save_state()
            
            return {
                "action": "retry",
                "message": "🔄 Phase reset for manual fix. Please update output and resubmit."
            }
        
        elif decision == "relax_constraint":
            # User wants to relax some constraints
            # This requires regenerating auditor with relaxed config
            if auditor:
                phase_state["status"] = PhaseStatus.IN_PROGRESS.value
                self._save_state()
                return {
                    "action": "retry_relaxed",
                    "message": "📝 Retrying with relaxed constraints..."
                }
            else:
                return {
                    "action": "error",
                    "message": "Cannot relax: no relaxed auditor provided"
                }
        
        elif decision == "force_proceed":
            # User accepts risk and wants to proceed
            phase_state["status"] = PhaseStatus.PASSED.value
            phase_state["forced"] = True
            self.state["audit_history"].append({
                "phase": phase,
                "attempt": phase_state.get("attempts", 0),
                "passed": False,
                "forced": True,
                "score": phase_state.get("last_audit", {}).get("score", 0)
            })
            self._save_state()
            
            return {
                "action": "proceed",
                "forced": True,
                "message": "⚠️ Phase forced to proceed. Quality risk accepted by user."
            }
        
        elif decision == "abort":
            phase_state["status"] = "aborted"
            self._save_state()
            
            return {
                "action": "abort",
                "message": "❌ Phase aborted by user decision."
            }
        
        else:
            return {"action": "error", "message": f"Unknown decision: {decision}"}
    
    def get_phase_status(self, phase: Optional[str] = None) -> Dict[str, Any]:
        """Get current phase status"""
        if phase:
            return self.state["phase_states"].get(phase, {})
        
        return {
            "current_phase": self.state.get("current_phase"),
            "phases": self.state.get("phase_states", {}),
            "can_proceed_to_next": self._can_proceed_to_next()
        }
    
    def _get_previous_phase(self, phase: str) -> Optional[str]:
        """Get the phase before current one"""
        try:
            idx = self.phases.index(phase)
            if idx > 0:
                return self.phases[idx - 1]
        except ValueError:
            pass
        return None
    
    def _phase_passed(self, phase: str) -> bool:
        """Check if a phase has passed"""
        phase_state = self.state["phase_states"].get(phase, {})
        return phase_state.get("status") == PhaseStatus.PASSED.value
    
    def _can_proceed_to_next(self) -> bool:
        """Check if can proceed to next phase"""
        current = self.state.get("current_phase")
        if not current:
            return True  # No phase started yet
        return self._phase_passed(current)
    
    def _now(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()


def main():
    """CLI for phase gateway"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BMAD-EVO Phase Gateway")
    parser.add_argument("--project", default=".", help="Project path")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Start phase
    start_parser = subparsers.add_parser("start", help="Start a phase")
    start_parser.add_argument("phase", help="Phase name")
    
    # Status
    subparsers.add_parser("status", help="Get phase status")
    
    # Decision
    decision_parser = subparsers.add_parser("decision", help="Make user decision")
    decision_parser.add_argument("phase", help="Phase name")
    decision_parser.add_argument("choice", choices=["manual_fix", "relax_constraint", "force_proceed", "abort"])
    
    args = parser.parse_args()
    
    gateway = PhaseGateway(args.project)
    
    if args.command == "start":
        success = gateway.start_phase(args.phase)
        sys.exit(0 if success else 1)
    
    elif args.command == "status":
        status = gateway.get_phase_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
    
    elif args.command == "decision":
        result = gateway.user_decision(args.phase, args.choice)
        print(result["message"])
        sys.exit(0 if result["action"] != "error" else 1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
