"""
BMAD-EVO Constraint Auditor Agent
Phase 1: Main entry point for constraint auditing

Usage:
    python constraint_auditor.py audit --phase development --file code.py
    python constraint_auditor.py history
    python constraint_auditor.py report --phase development
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

from constraint_checker import ConstraintChecker, AuditResult, check_constraints
from audit_report import AuditReportGenerator, QuickReport, load_constraints_from_project


class ConstraintAuditor:
    """
    Main constraint auditor for BMAD-EVO
    
    Provides:
    - Single command audit: bmad-evo audit
    - Phase integration: Automatic audit in development phase
    - Retry logic: Up to 3 attempts with model fallback
    - History tracking: Audit logs for analysis
    """
    
    def __init__(self, project_path: str):
        from config_loader import get_quality_threshold, get_max_retries
        self.pass_threshold = get_quality_threshold("pass_threshold", 85)
        self.max_retries = get_max_retries("constraint_audit", 3)
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.bmad_dir = self.project_path / ".bmad"
        self.checkpoints_dir = self.bmad_dir / "checkpoints"
        
        # Ensure directories exist
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        
        # Load constraints
        constraints = load_constraints_from_project(project_path)
        if constraints:
            self.checker = ConstraintChecker({"constraints": constraints})
        else:
            self.checker = None
        
        self.report_generator = AuditReportGenerator(project_path)
    
    def audit(
        self, 
        output: str, 
        phase: str, 
        attempt: int = 1,
        output_file: Optional[str] = None
    ) -> AuditResult:
        """
        Main audit entry point
        
        Args:
            output: Content to audit (code, document, etc.)
            phase: Current phase name
            attempt: Retry attempt number
            output_file: Optional file path for the output being audited
            
        Returns:
            AuditResult with pass/fail status
        """
        print(f"\n🔍 开始约束审计 (阶段: {phase}, 尝试: {attempt}/{self.max_retries})")
        print("-" * 60)
        
        # Use checker or default
        if self.checker:
            result = self.checker.audit(output)
        else:
            result = check_constraints(output)
        
        # Generate reports
        report_path = self.report_generator.generate_markdown_report(
            result, phase, attempt
        )
        json_path = self.report_generator.save_json_log(
            result, phase, attempt,
            metadata={"output_file": output_file}
        )
        
        # Console output
        QuickReport.print_summary(result)
        print(f"📄 详细报告: {report_path}")
        print(f"📝 JSON日志: {json_path}")
        
        # Save checkpoint
        self._save_checkpoint(phase, result, attempt)
        
        return result
    
    def should_retry(self, result: AuditResult, attempt: int) -> tuple[bool, str]:
        """
        Determine if we should retry and with which model
        
        Returns:
            (should_retry, model_hint)
            model_hint: "same", "glm5", or "stop"
        """
        if result.passed:
            return False, "stop"
        
        if attempt >= self.max_retries:
            return False, "stop"
        
        # Attempt 1-2: Same model (K2.5)
        if attempt <= 2:
            return True, "same"
        
        # Attempt 3: Switch to GLM-5 (fallback)
        if attempt == 3:
            # Check if there are code quality issues that GLM-5 might handle better
            code_issues = ["代码结构", "边界检查", "防御性编程", "可读性"]
            has_code_issues = any(
                any(issue in v.description for issue in code_issues)
                for v in result.violations
            )
            
            if has_code_issues:
                return True, "glm5"
        
        return False, "stop"
    
    def get_retry_feedback(self, result: AuditResult) -> str:
        """Get feedback for retry attempt"""
        return self.report_generator.generate_retry_feedback(result)
    
    def _save_checkpoint(self, phase: str, result: AuditResult, attempt: int):
        """Save audit checkpoint for phase progression"""
        checkpoint = {
            "phase": phase,
            "attempt": attempt,
            "passed": result.passed,
            "score": result.score,
            "timestamp": self.report_generator.logs_dir.name
        }
        
        checkpoint_file = self.checkpoints_dir / f"{phase}-checkpoint.json"
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
    
    def can_proceed_to_next_phase(self, phase: str) -> tuple[bool, str]:
        """
        Check if we can proceed to next phase
        
        Returns:
            (can_proceed, reason)
        """
        checkpoint_file = self.checkpoints_dir / f"{phase}-checkpoint.json"
        
        if not checkpoint_file.exists():
            return False, f"阶段 {phase} 尚未完成审计"
        
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)
        
        if not checkpoint.get("passed"):
            return False, f"阶段 {phase} 审计未通过 (得分: {checkpoint.get('score', 0)})"
        
        return True, f"阶段 {phase} 审计通过，可以继续"
    
    def get_audit_history(self, phase: Optional[str] = None, limit: int = 10):
        """Get audit history for analysis"""
        history = self.report_generator.get_audit_history(limit)
        
        if phase:
            history = [h for h in history if h.get("phase") == phase]
        
        return history


def main():
    parser = argparse.ArgumentParser(
        description="BMAD-EVO Constraint Auditor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Audit a code file
  python constraint_auditor.py audit --phase development --file src/main.py
  
  # Audit from stdin
  cat code.py | python constraint_auditor.py audit --phase development
  
  # View audit history
  python constraint_auditor.py history --limit 5
  
  # Check if can proceed to next phase
  python constraint_auditor.py check --phase development
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Audit command
    audit_parser = subparsers.add_parser("audit", help="Run constraint audit")
    audit_parser.add_argument("--phase", required=True, help="Phase name (e.g., development)")
    audit_parser.add_argument("--file", help="File to audit (default: stdin)")
    audit_parser.add_argument("--project", default=".", help="Project path")
    audit_parser.add_argument("--attempt", type=int, default=1, help="Retry attempt number")
    
    # History command
    history_parser = subparsers.add_parser("history", help="View audit history")
    history_parser.add_argument("--project", default=".", help="Project path")
    history_parser.add_argument("--phase", help="Filter by phase")
    history_parser.add_argument("--limit", type=int, default=10, help="Number of entries")
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Check if can proceed to next phase")
    check_parser.add_argument("--phase", required=True, help="Phase to check")
    check_parser.add_argument("--project", default=".", help="Project path")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == "audit":
        # Read input
        if args.file:
            content = Path(args.file).read_text(encoding='utf-8')
        else:
            content = sys.stdin.read()
        
        # Run audit
        auditor = ConstraintAuditor(args.project)
        result = auditor.audit(content, args.phase, args.attempt, args.file)
        
        # Return exit code based on result
        return 0 if result.passed else 1
    
    elif args.command == "history":
        auditor = ConstraintAuditor(args.project)
        history = auditor.get_audit_history(args.phase, args.limit)
        
        print(f"\n审计历史 (最近 {len(history)} 条):")
        print("-" * 80)
        
        for entry in history:
            ts = entry.get("timestamp", "unknown")
            phase = entry.get("phase", "unknown")
            result = entry.get("result", {})
            passed = "✅" if result.get("passed") else "❌"
            score = result.get("score", 0)
            
            print(f"{ts} | {phase:15} | {passed} {score:3}/100")
        
        print()
        return 0
    
    elif args.command == "check":
        auditor = ConstraintAuditor(args.project)
        can_proceed, reason = auditor.can_proceed_to_next_phase(args.phase)
        
        print(f"\n{reason}")
        return 0 if can_proceed else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
