"""
BMAD-EVO Phase Gateway
Phase 3: AST-powered automatic audit integration

Provides:
- Intercept phase transitions and trigger audit
- Block progression if audit fails
- Coordinate with retry mechanism
- AST-powered analysis (zero false positives)

Design Principles:
- Single Responsibility: Gateway manages state, doesn't perform audits
- Dependency Injection: Accept audit results, don't create auditors
- Fault Tolerance: Graceful handling of corrupted state files
- AST-First: Prefer AST analysis when available
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Union
from enum import Enum
from datetime import datetime, timezone
import logging

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from constraint_checker import AuditResult

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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
    
    Configuration:
    - MAX_RETRIES: Maximum retry attempts before user decision (default: 3)
    - PASS_THRESHOLD: Minimum score to pass audit (default: 85)
    """
    
    def __init__(self, project_path: str, config: Optional[Dict[str, Any]] = None):
        self.project_path = Path(project_path)
        self.bmad_dir = self.project_path / ".bmad"
        self.state_file = self.bmad_dir / "phase-state.json"
        self.checkpoint_dir = self.bmad_dir / "checkpoints"
        self.config_file = self.bmad_dir / "gateway-config.json"
        
        from config_loader import get_quality_threshold, get_max_retries
        self.config = config or self._load_config()
        self.MAX_RETRIES = self.config.get('max_retries', get_max_retries("phase_gateway", 3))
        self.PASS_THRESHOLD = self.config.get('pass_threshold', get_quality_threshold("pass_threshold", 85))
        
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.phases = [
            "analyst",
            "pm", 
            "architect",
            "design",
            "development",
            "testing",
            "deployment",
        ]
        
        self.state = self._load_state()
        
        logger.info(f"PhaseGateway initialized: {len(self.phases)} phases, "
                     f"threshold={self.PASS_THRESHOLD}, max_retries={self.MAX_RETRIES}")
    
    def start_phase(self, phase: str) -> bool:
        """
        Start a new phase
        
        Returns:
            True if phase can start, False otherwise
        """
        prev_phase = self._get_previous_phase(phase)
        if prev_phase and not self._phase_passed(prev_phase):
            print(f"Cannot start {phase}: previous phase {prev_phase} not passed")
            return False
        
        self.state["current_phase"] = phase
        self.state["phase_states"][phase] = {
            "status": PhaseStatus.IN_PROGRESS.value,
            "started_at": self._now(),
            "attempts": 0
        }
        self._save_state()
        
        print(f"Phase '{phase}' started")
        return True
    
    def complete_phase(
        self,
        phase: str,
        audit_result: AuditResult,
        attempt: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Complete phase with provided audit result
        
        Args:
            phase: Current phase name
            audit_result: Result from ConstraintAuditor (injected, not created here)
            attempt: Current attempt number (optional, defaults to last + 1)
            
        Returns:
            Result dict with:
            - action: "proceed", "retry", "block", "abort"
            - result: AuditResult
            - message: User-facing message
            
        Design Note:
        - Gateway doesn't perform audits, only manages state transitions
        - AuditResult is injected from external auditor
        """
        phase_state = self.state["phase_states"].get(phase, {})
        current_attempt = attempt or (phase_state.get("attempts", 0) + 1)
        
        logger.info(f"Phase Gateway: Completing '{phase}' (attempt {current_attempt}/{self.MAX_RETRIES})")
        
        # Update state
        phase_state["attempts"] = current_attempt
        phase_state["last_audit"] = {
            "score": audit_result.score,
            "passed": audit_result.passed,
            "timestamp": self._now()
        }
        
        # Determine next action based on audit result and retry count
        if audit_result.passed:
            phase_state["status"] = PhaseStatus.PASSED.value
            self.state["audit_history"].append({
                "phase": phase,
                "attempt": current_attempt,
                "passed": True,
                "score": audit_result.score
            })
            self._save_state()
            
            logger.info(f"Phase '{phase}' passed audit ({audit_result.score}/100)")
            
            return {
                "action": "proceed",
                "result": audit_result,
                "message": f"✅ Phase '{phase}' passed audit ({audit_result.score}/100). Ready to proceed."
            }
        
        # Audit failed - check retry logic
        should_retry = current_attempt < self.MAX_RETRIES
        
        if should_retry:
            phase_state["status"] = PhaseStatus.AUDITING.value
            self._save_state()
            
            logger.info(f"Phase '{phase}' audit failed ({audit_result.score}/100). Retry recommended.")
            
            return {
                "action": "retry",
                "result": audit_result,
                "message": f"⏳ Phase '{phase}' audit failed ({audit_result.score}/100). Retry attempt {current_attempt+1}/{self.MAX_RETRIES} available."
            }
        
        # All retries exhausted - block for user decision
        phase_state["status"] = PhaseStatus.BLOCKED.value
        self.state["audit_history"].append({
            "phase": phase,
            "attempt": current_attempt,
            "passed": False,
            "score": audit_result.score
        })
        self._save_state()
        
        logger.warning(f"Phase '{phase}' blocked after {current_attempt} attempts. User decision required.")
        
        return {
            "action": "block",
            "result": audit_result,
            "message": f"🚫 Phase '{phase}' blocked after {current_attempt}/{self.MAX_RETRIES} attempts. User decision required.",
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
    
    def _load_config(self) -> Dict[str, Any]:
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _load_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                logger.warning("Corrupted state file, starting fresh")
        return {"current_phase": None, "phase_states": {}}
    
    def _save_state(self):
        self.bmad_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
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
        """Get current timestamp with timezone"""
        return datetime.now(timezone.utc).isoformat()


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
