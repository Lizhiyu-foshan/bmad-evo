"""
BMAD-EVO Constraint Checker Engine
Phase 1: Core audit functionality

Provides:
- Constraint validation against outputs
- Scoring mechanism (0-100)
- Violation detection with evidence
- Pass/fail threshold (85)
"""

import re
import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

class Severity(Enum):
    HIGH = "high"      # Must fix, blocks progression
    MEDIUM = "medium"  # Should fix, impacts quality
    LOW = "low"        # Nice to have, suggestive

class ConstraintType(Enum):
    BOUNDARY_CHECK = "边界检查"
    EXCEPTION_HANDLING = "异常处理"
    CODE_STRUCTURE = "代码结构"
    READABILITY = "可读性"
    SECURITY = "安全性"
    PERFORMANCE = "性能"
    TEST_COVERAGE = "测试覆盖"
    DOCUMENTATION = "文档"
    CUSTOM = "自定义"

@dataclass
class Violation:
    constraint_type: ConstraintType
    severity: Severity
    description: str
    evidence: str
    suggestion: str
    line_number: Optional[int] = None
    
@dataclass
class AuditResult:
    passed: bool
    score: int
    violations: List[Violation]
    must_fix: List[str]  # List of constraint types that must be fixed
    summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "violations": [
                {
                    "type": v.constraint_type.value,
                    "severity": v.severity.value,
                    "description": v.description,
                    "evidence": v.evidence,
                    "suggestion": v.suggestion,
                    "line": v.line_number
                }
                for v in self.violations
            ],
            "must_fix": self.must_fix,
            "summary": self.summary
        }

class ConstraintChecker:
    """Core constraint validation engine"""
    
    PASS_THRESHOLD = 85
    
    def __init__(self, constraints_yaml: Dict[str, Any]):
        self.constraints = self._parse_constraints(constraints_yaml)
        self.checkers = self._register_checkers()
    
    def _parse_constraints(self, yaml_data: Dict) -> Dict[ConstraintType, List[Dict]]:
        """Parse constraints from YAML structure"""
        parsed = {}
        
        # Map YAML keys to ConstraintType
        type_mapping = {
            "boundary_check": ConstraintType.BOUNDARY_CHECK,
            "exception_handling": ConstraintType.EXCEPTION_HANDLING,
            "code_structure": ConstraintType.CODE_STRUCTURE,
            "readability": ConstraintType.READABILITY,
            "security": ConstraintType.SECURITY,
            "performance": ConstraintType.PERFORMANCE,
            "test_coverage": ConstraintType.TEST_COVERAGE,
            "documentation": ConstraintType.DOCUMENTATION,
            "custom": ConstraintType.CUSTOM
        }
        
        constraints_data = yaml_data.get("constraints", {})
        
        for key, constraint_type in type_mapping.items():
            if key in constraints_data:
                parsed[constraint_type] = constraints_data[key]
                
        return parsed
    
    def _register_checkers(self) -> Dict[ConstraintType, callable]:
        """Register checker functions for each constraint type"""
        return {
            ConstraintType.BOUNDARY_CHECK: self._check_boundary,
            ConstraintType.EXCEPTION_HANDLING: self._check_exception_handling,
            ConstraintType.CODE_STRUCTURE: self._check_code_structure,
            ConstraintType.READABILITY: self._check_readability,
            ConstraintType.SECURITY: self._check_security,
            ConstraintType.CUSTOM: self._check_custom
        }
    
    def audit(self, output: str, output_type: str = "code") -> AuditResult:
        """
        Main audit entry point
        
        Args:
            output: The content to audit (code, document, etc.)
            output_type: Type of output (code, prd, architecture, etc.)
            
        Returns:
            AuditResult with pass/fail status and detailed violations
        """
        violations = []
        
        # Run all applicable checkers
        for constraint_type, checker_fn in self.checkers.items():
            if constraint_type in self.constraints:
                type_violations = checker_fn(output, self.constraints[constraint_type])
                violations.extend(type_violations)
        
        # Calculate score
        score = self._calculate_score(violations)
        
        # Determine must-fix items (HIGH severity)
        must_fix = list(set([
            v.constraint_type.value 
            for v in violations 
            if v.severity == Severity.HIGH
        ]))
        
        passed = score >= self.PASS_THRESHOLD and not must_fix
        
        summary = self._generate_summary(passed, score, violations)
        
        return AuditResult(
            passed=passed,
            score=score,
            violations=violations,
            must_fix=must_fix,
            summary=summary
        )
    
    def _calculate_score(self, violations: List[Violation]) -> int:
        """Calculate score based on violations"""
        # Start with 100
        score = 100
        
        # Deduct points based on severity
        for v in violations:
            if v.severity == Severity.HIGH:
                score -= 15
            elif v.severity == Severity.MEDIUM:
                score -= 8
            elif v.severity == Severity.LOW:
                score -= 3
        
        return max(0, score)
    
    def _generate_summary(self, passed: bool, score: int, violations: List[Violation]) -> str:
        """Generate human-readable summary"""
        if passed:
            return f"审计通过 (得分: {score}/100)。所有约束项满足要求。"
        
        high_count = sum(1 for v in violations if v.severity == Severity.HIGH)
        med_count = sum(1 for v in violations if v.severity == Severity.MEDIUM)
        low_count = sum(1 for v in violations if v.severity == Severity.LOW)
        
        return (
            f"审计未通过 (得分: {score}/100，阈值: {self.PASS_THRESHOLD})。"
            f"发现问题: {high_count}个高优先级, {med_count}个中优先级, {low_count}个低优先级。"
            f"请修复高优先级问题后重试。"
        )
    
    # ============ Checker Implementations ============
    
    def _check_boundary(self, output: str, constraints: List[Dict]) -> List[Violation]:
        """Check boundary conditions (None checks, range validation, etc.)"""
        violations = []
        
        # Check for None handling
        if any(c.get("check_null", True) for c in constraints):
            # Look for function definitions without null checks
            func_pattern = r'def\s+\w+\s*\([^)]*\):'
            for match in re.finditer(func_pattern, output):
                func_start = match.start()
                # Get function body (simplified)
                func_body = output[func_start:func_start+500]
                
                # Check if function has parameters but no null check
                if '(' in match.group() and '):' in match.group():
                    if 'is None' not in func_body and 'if ' not in func_body[:200]:
                        violations.append(Violation(
                            constraint_type=ConstraintType.BOUNDARY_CHECK,
                            severity=Severity.HIGH,
                            description="函数缺少输入参数为空值的检查",
                            evidence=f"函数定义: {match.group()[:50]}...",
                            suggestion="添加 if param is None: raise ValueError(...) 或提供默认值"
                        ))
        
        # Check for empty collection handling
        if 'for ' in output and 'if ' not in output[:output.find('for ') + 100]:
            violations.append(Violation(
                constraint_type=ConstraintType.BOUNDARY_CHECK,
                severity=Severity.MEDIUM,
                description="循环缺少对空集合的检查",
                evidence="发现for循环但没有前置的空值检查",
                suggestion="在循环前检查: if not items: return/handle"
            ))
        
        return violations
    
    def _check_exception_handling(self, output: str, constraints: List[Dict]) -> List[Violation]:
        """Check exception handling (try-except blocks, specific exceptions)"""
        violations = []
        
        # Check for network/IO operations without try-except
        io_patterns = [
            (r'requests\.(get|post|put|delete)', "网络请求缺少异常处理"),
            (r'open\s*\(', "文件操作缺少异常处理"),
            (r'json\.loads?\s*\(', "JSON解析缺少异常处理"),
        ]
        
        for pattern, msg in io_patterns:
            match = re.search(pattern, output)
            if match:
                start_pos = max(0, match.start() - 200)
                context = output[start_pos:match.start()]
                if 'try:' not in context:
                    violations.append(Violation(
                        constraint_type=ConstraintType.EXCEPTION_HANDLING,
                        severity=Severity.HIGH,
                        description=msg,
                        evidence=f"发现模式: {pattern[:30]}...",
                        suggestion="添加try-except块捕获具体异常(如requests.Timeout, FileNotFoundError)"
                    ))
        
        # Check for bare except clauses
        if 'except:' in output and 'except Exception' not in output:
            violations.append(Violation(
                constraint_type=ConstraintType.EXCEPTION_HANDLING,
                severity=Severity.MEDIUM,
                description="使用了裸except:子句",
                evidence="发现 'except:' 没有指定异常类型",
                suggestion="使用 'except SpecificException:' 或至少 'except Exception:'"
            ))
        
        return violations
    
    def _check_code_structure(self, output: str, constraints: List[Dict]) -> List[Violation]:
        """Check code structure and organization"""
        violations = []
        
        # Check function length
        func_starts = list(re.finditer(r'def\s+\w+', output))
        for i, match in enumerate(func_starts):
            start = match.end()
            end = func_starts[i+1].start() if i+1 < len(func_starts) else len(output)
            func_length = output[start:end].count('\n')
            
            max_lines = next((c.get("max_function_lines", 50) for c in constraints), 50)
            if func_length > max_lines:
                violations.append(Violation(
                    constraint_type=ConstraintType.CODE_STRUCTURE,
                    severity=Severity.MEDIUM,
                    description=f"函数过长({func_length}行)",
                    evidence=f"函数超过{max_lines}行",
                    suggestion="将函数拆分为多个小函数，每个只做一件事"
                ))
        
        return violations
    
    def _check_readability(self, output: str, constraints: List[Dict]) -> List[Violation]:
        """Check code readability (naming, comments, etc.)"""
        violations = []
        
        # Check for single letter variables (excluding common ones)
        single_letter = re.findall(r'\b([a-zA-Z])\b', output)
        common_single = {'i', 'j', 'k', 'x', 'y', 'n'}
        bad_vars = set(single_letter) - common_single
        
        if bad_vars:
            violations.append(Violation(
                constraint_type=ConstraintType.READABILITY,
                severity=Severity.LOW,
                description="使用单字母变量名",
                evidence=f"发现变量: {', '.join(list(bad_vars)[:3])}",
                suggestion="使用描述性变量名，如 'index' 而不是 'i'（循环除外）"
            ))
        
        return violations
    
    def _check_security(self, output: str, constraints: List[Dict]) -> List[Violation]:
        """Check security issues"""
        violations = []
        
        # Check for hardcoded secrets
        secret_patterns = [
            (r'(password|secret|key|token)\s*=\s*["\'][^"\']+["\']', "可能的硬编码密钥"),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "硬编码API密钥"),
        ]
        
        for pattern, msg in secret_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                violations.append(Violation(
                    constraint_type=ConstraintType.SECURITY,
                    severity=Severity.HIGH,
                    description=msg,
                    evidence="发现可能的硬编码敏感信息",
                    suggestion="使用环境变量或密钥管理服务，不要硬编码"
                ))
        
        return violations
    
    def _check_custom(self, output: str, constraints: List[Dict]) -> List[Violation]:
        """Check custom user-defined constraints"""
        violations = []
        
        for constraint in constraints:
            pattern = constraint.get("pattern", "")
            must_exist = constraint.get("must_exist", True)
            
            exists = bool(re.search(pattern, output)) if pattern else False
            
            if must_exist and not exists:
                violations.append(Violation(
                    constraint_type=ConstraintType.CUSTOM,
                    severity=Severity(constraint.get("severity", "medium")),
                    description=constraint.get("description", "自定义约束未满足"),
                    evidence=f"未找到模式: {pattern[:50]}...",
                    suggestion=constraint.get("suggestion", "请检查实现")
                ))
            elif not must_exist and exists:
                violations.append(Violation(
                    constraint_type=ConstraintType.CUSTOM,
                    severity=Severity(constraint.get("severity", "medium")),
                    description=constraint.get("description", "禁止的模式被发现"),
                    evidence=f"发现不应存在的模式: {pattern[:50]}...",
                    suggestion=constraint.get("suggestion", "请移除")
                ))
        
        return violations


# Convenience function for direct usage
def check_constraints(output: str, constraints_yaml_path: Optional[str] = None) -> AuditResult:
    """
    Quick check with default or custom constraints
    
    Usage:
        result = check_constraints(code_string)
        if not result.passed:
            print(result.summary)
    """
    # Default constraints for code
    default_constraints = {
        "constraints": {
            "boundary_check": [{"check_null": True}],
            "exception_handling": [{"check_io": True}],
            "code_structure": [{"max_function_lines": 50}],
            "readability": [{}],
            "security": [{}]
        }
    }
    
    if constraints_yaml_path:
        with open(constraints_yaml_path, 'r', encoding='utf-8') as f:
            constraints = yaml.safe_load(f)
    else:
        constraints = default_constraints
    
    checker = ConstraintChecker(constraints)
    return checker.audit(output)


if __name__ == "__main__":
    # Test
    test_code = '''
def process_data(data):
    result = requests.get(data['url'])
    for item in result.json():
        print(item)
    return result
'''
    
    result = check_constraints(test_code)
    print(f"Passed: {result.passed}, Score: {result.score}")
    for v in result.violations:
        print(f"- [{v.severity.value}] {v.description}: {v.suggestion}")
