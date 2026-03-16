"""
BMAD-EVO Decision Interface
Phase 2: Interactive user decision interface

Provides:
- Interactive menu when phase is blocked
- Display audit results in user-friendly format
- Handle user choices (retry, relax, force, abort)
- Generate decision records
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from constraint_checker import AuditResult, Severity


@dataclass
class DecisionRecord:
    """Record of a user decision"""
    phase: str
    decision: str
    reason: str
    timestamp: str
    audit_score: int
    risk_accepted: bool = False


class DecisionInterface:
    """
    Interactive interface for user decisions when phase is blocked
    
    Presents:
    - Clear audit summary
    - Actionable options
    - Risk warnings for dangerous choices
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.bmad_dir = self.project_path / ".bmad"
        self.decisions_dir = self.bmad_dir / "decisions"
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
    
    def present_blocked_phase(
        self,
        phase: str,
        audit_result: AuditResult,
        attempt: int,
        report_path: str
    ) -> str:
        """
        Present blocked phase to user and get decision
        
        Returns:
            User decision choice (manual_fix, relax_constraint, force_proceed, abort)
        """
        self._print_header(phase, audit_result, attempt)
        self._print_violations(audit_result)
        self._print_options(audit_result)
        
        choice = self._get_user_choice(audit_result)
        
        # Record decision
        reason = self._get_reason(choice)
        self._record_decision(phase, choice, reason, audit_result)
        
        return choice
    
    def _print_header(self, phase: str, audit_result: AuditResult, attempt: int):
        """Print phase blocked header"""
        print("\n" + "="*70)
        print("🚫 PHASE BLOCKED - USER DECISION REQUIRED")
        print("="*70)
        print(f"\nPhase: {phase}")
        print(f"Attempt: {attempt}/3 (all retries exhausted)")
        print(f"Audit Score: {audit_result.score}/100 (threshold: 85)")
        print(f"Status: {'✅ PASSED' if audit_result.passed else '❌ FAILED'}")
        
        if audit_result.must_fix:
            print(f"\n⚠️  Must Fix Items: {', '.join(audit_result.must_fix)}")
        print()
    
    def _print_violations(self, audit_result: AuditResult):
        """Print violations in categorized format"""
        if not audit_result.violations:
            print("No violations found (this shouldn't happen if blocked)")
            return
        
        # Group by severity
        high = [v for v in audit_result.violations if v.severity == Severity.HIGH]
        medium = [v for v in audit_result.violations if v.severity == Severity.MEDIUM]
        low = [v for v in audit_result.violations if v.severity == Severity.LOW]
        
        if high:
            print("🔴 HIGH PRIORITY VIOLATIONS (Must Fix):")
            for i, v in enumerate(high, 1):
                print(f"  {i}. [{v.constraint_type.value}] {v.description}")
                print(f"     Evidence: {v.evidence[:60]}...")
                print(f"     Suggestion: {v.suggestion}")
            print()
        
        if medium:
            print("🟡 MEDIUM PRIORITY VIOLATIONS:")
            for i, v in enumerate(medium, 1):
                print(f"  {i}. [{v.constraint_type.value}] {v.description}")
            print()
        
        if low:
            print("🟢 LOW PRIORITY SUGGESTIONS:")
            for i, v in enumerate(low, 1):
                print(f"  {i}. [{v.constraint_type.value}] {v.description}")
            print()
    
    def _print_options(self, audit_result: AuditResult):
        """Print available options"""
        print("-"*70)
        print("AVAILABLE OPTIONS:")
        print("-"*70)
        
        print("\n1. 🔧 MANUAL FIX (Recommended)")
        print("   - Edit your code/output to fix violations")
        print("   - Resubmit for fresh audit")
        print("   - Risk: None")
        
        print("\n2. 📝 RELAX CONSTRAINTS")
        print("   - Temporarily relax some constraints")
        print("   - Retry with less strict requirements")
        print("   - Risk: Lower quality bar for this phase")
        
        if audit_result.score >= 70:
            print("\n3. ⚠️  FORCE PROCEED")
            print(f"   - Accept current quality ({audit_result.score}/100)")
            print("   - Proceed to next phase anyway")
            print("   - Risk: Technical debt, potential bugs")
        else:
            print("\n3. ⛔ FORCE PROCEED (Not Recommended)")
            print(f"   - Score too low ({audit_result.score}/100 < 70)")
            print("   - Strongly discouraged")
            print("   - Risk: HIGH - Likely to cause serious issues")
        
        print("\n4. ❌ ABORT")
        print("   - Cancel this phase")
        print("   - Return to previous phase or exit")
        print("   - Risk: Lost progress")
        
        print()
    
    def _get_user_choice(self, audit_result: AuditResult) -> str:
        """Get and validate user choice"""
        valid_choices = {
            "1": "manual_fix",
            "2": "relax_constraint",
            "3": "force_proceed",
            "4": "abort",
            "manual": "manual_fix",
            "relax": "relax_constraint",
            "force": "force_proceed",
            "abort": "abort"
        }
        
        while True:
            try:
                choice = input("Enter your choice (1-4 or name): ").strip().lower()
                
                if choice in valid_choices:
                    final_choice = valid_choices[choice]
                    
                    # Extra warning for force_proceed with low score
                    if final_choice == "force_proceed" and audit_result.score < 70:
                        confirm = input("⚠️  Score is below 70. Are you sure? (yes/no): ").strip().lower()
                        if confirm not in ["yes", "y"]:
                            continue
                    
                    return final_choice
                else:
                    print("Invalid choice. Please enter 1, 2, 3, 4 or the option name.")
            
            except (EOFError, KeyboardInterrupt):
                print("\n\nInterrupted. Defaulting to 'manual_fix'.")
                return "manual_fix"
    
    def _get_reason(self, choice: str) -> str:
        """Get optional reason for decision"""
        reasons = {
            "manual_fix": "User chose to manually fix violations",
            "relax_constraint": "User chose to relax constraints",
            "force_proceed": "User accepted quality risk and forced proceed",
            "abort": "User chose to abort phase"
        }
        
        print(f"\nYou chose: {choice}")
        
        try:
            custom_reason = input("Optional: Add a reason for this decision (press Enter to skip): ").strip()
            if custom_reason:
                return custom_reason
        except (EOFError, KeyboardInterrupt):
            pass
        
        return reasons.get(choice, "No reason provided")
    
    def _record_decision(
        self,
        phase: str,
        decision: str,
        reason: str,
        audit_result: AuditResult
    ):
        """Record decision to file"""
        from datetime import datetime
        
        record = DecisionRecord(
            phase=phase,
            decision=decision,
            reason=reason,
            timestamp=datetime.now().isoformat(),
            audit_score=audit_result.score,
            risk_accepted=(decision == "force_proceed")
        )
        
        # Save to JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        decision_file = self.decisions_dir / f"decision-{phase}-{timestamp}.json"
        
        with open(decision_file, 'w', encoding='utf-8') as f:
            json.dump({
                "phase": record.phase,
                "decision": record.decision,
                "reason": record.reason,
                "timestamp": record.timestamp,
                "audit_score": record.audit_score,
                "risk_accepted": record.risk_accepted,
                "violations_count": len(audit_result.violations),
                "must_fix_items": audit_result.must_fix
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📝 Decision recorded: {decision_file}")
    
    def get_decision_history(self, phase: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get decision history"""
        decisions = []
        
        for f in sorted(self.decisions_dir.glob("decision-*.json"), reverse=True):
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                if phase is None or data.get("phase") == phase:
                    decisions.append(data)
            
            if len(decisions) >= limit:
                break
        
        return decisions
    
    def generate_summary(self) -> str:
        """Generate summary of all decisions"""
        decisions = self.get_decision_history(limit=100)
        
        if not decisions:
            return "No decisions recorded yet."
        
        summary = ["\n" + "="*70, "DECISION HISTORY SUMMARY", "="*70, ""]
        
        total = len(decisions)
        forced = sum(1 for d in decisions if d.get("risk_accepted"))
        manual_fix = sum(1 for d in decisions if d.get("decision") == "manual_fix")
        relaxed = sum(1 for d in decisions if d.get("decision") == "relax_constraint")
        aborted = sum(1 for d in decisions if d.get("decision") == "abort")
        
        summary.append(f"Total Decisions: {total}")
        summary.append(f"  - Manual Fix: {manual_fix} ({manual_fix/total*100:.1f}%)")
        summary.append(f"  - Relaxed Constraints: {relaxed} ({relaxed/total*100:.1f}%)")
        summary.append(f"  - Forced Proceed: {forced} ({forced/total*100:.1f}%)")
        summary.append(f"  - Aborted: {aborted} ({aborted/total*100:.1f}%)")
        
        if forced > 0:
            summary.append(f"\n⚠️  Warning: {forced} phases were forced with quality risk accepted")
        
        avg_score = sum(d.get("audit_score", 0) for d in decisions) / total
        summary.append(f"\nAverage Audit Score: {avg_score:.1f}/100")
        
        summary.append("="*70)
        
        return "\n".join(summary)


def main():
    """CLI for decision interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BMAD-EVO Decision Interface")
    parser.add_argument("--project", default=".", help="Project path")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # History
    history_parser = subparsers.add_parser("history", help="Show decision history")
    history_parser.add_argument("--phase", help="Filter by phase")
    history_parser.add_argument("--limit", type=int, default=10)
    
    # Summary
    subparsers.add_parser("summary", help="Show decision summary")
    
    args = parser.parse_args()
    
    interface = DecisionInterface(args.project)
    
    if args.command == "history":
        decisions = interface.get_decision_history(args.phase, args.limit)
        for d in decisions:
            print(f"[{d['timestamp']}] {d['phase']}: {d['decision']} (score: {d['audit_score']})")
            print(f"  Reason: {d['reason']}")
            print()
    
    elif args.command == "summary":
        print(interface.generate_summary())
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
