# Phase 3: Coding - Implementation Blueprint

**Document Version:** 1.0
**Based on:** SKILL_TREE_MASTER.md
**Theme:** Ship It (Results-Focused)
**Prerequisites:** Phase 0 (Foundation) completed

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Prerequisites & Dependencies](#2-prerequisites--dependencies)
3. [Task 3.1: Update Skill Definitions](#3-task-31-update-skill-definitions)
4. [Task 3.2: Update TOOL_TO_SKILL_MAPPING](#4-task-32-update-tool_to_skill_mapping)
5. [Task 3.3: Implement Waitress XP System](#5-task-33-implement-waitress-xp-system)
6. [Task 3.4: Implement AST Fingerprinting](#6-task-34-implement-ast-fingerprinting)
7. [Task 3.5: Implement Code Execution Environment](#7-task-35-implement-code-execution-environment)
8. [Task 3.6: Implement Sun Tool - develop_code](#8-task-36-implement-sun-tool---develop_code)
9. [Task 3.7: Implement Testing Planet](#9-task-37-implement-testing-planet)
10. [Task 3.8: Implement Debugging Planet](#10-task-38-implement-debugging-planet)
11. [Task 3.9: Implement Algorithms Planet](#11-task-39-implement-algorithms-planet)
12. [Task 3.10: Implement Hacking Planet](#12-task-310-implement-hacking-planet)
13. [Task 3.11: Implement Code Review Planet](#13-task-311-implement-code-review-planet)
14. [Task 3.12: Register All Tools](#14-task-312-register-all-tools)
15. [Task 3.13: Frontend Synchronization](#15-task-313-frontend-synchronization)
16. [Task 3.14: LEARNING Block Integration](#16-task-314-learning-block-integration)
17. [Task 3.15: Testing & Validation](#17-task-315-testing--validation)
18. [Appendix A: Tool Summary Table](#appendix-a-tool-summary-table)
19. [Appendix B: File Reference](#appendix-b-file-reference)
20. [Appendix C: Waitress XP Tip Calculation](#appendix-c-waitress-xp-tip-calculation)

---

## 1. Executive Summary

### Purpose

Phase 3 implements the Coding category - a results-focused skill tree that enables Qubes to write, test, debug, optimize, secure, and review code. Unlike other categories that use standard XP (5/2.5/0), Coding uses the **Waitress XP Model** (base 1 + tips 0-9) with **AST fingerprinting** to prevent gaming.

### Theme: Ship It (Results-Focused)

The Coding category is about delivering working code:
- **Testing**: Verify code works correctly
- **Debugging**: Find and fix problems
- **Algorithms**: Optimize for performance
- **Hacking**: Secure against attacks
- **Code Review**: Maintain quality standards

### Tool Count

| Type | Count | Tools |
|------|-------|-------|
| Sun | 1 | `develop_code` |
| Planets | 5 | `run_tests`, `debug_code`, `benchmark_code`, `security_scan`, `review_code` |
| Moons | 12 | `write_unit_test`, `measure_coverage`, `analyze_error`, `find_root_cause`, `analyze_complexity`, `tune_performance`, `find_exploit`, `reverse_engineer`, `pen_test`, `refactor_code`, `git_operation`, `generate_docs` |
| **Total** | **18** | |

### XP Model: Waitress (Base + Tips)

Unlike standard XP (5/2.5/0), Coding uses:

```
XP = base (1) + tips (0-9)
```

| Component | Value | Description |
|-----------|-------|-------------|
| Base | 1 | Always awarded for completing task |
| Tips | 0-9 | Based on code quality milestones |

**Tip Calculation Example:**
| Milestone | Tip Value |
|-----------|-----------|
| Code executes without error | +1 |
| All tests pass | +2 |
| Coverage > 80% | +1 |
| No security vulnerabilities | +1 |
| Performance < threshold | +1 |
| Clean code (no linting errors) | +1 |
| Follows best practices | +1 |
| Novel approach (not duplicate) | +1 |

**Maximum XP per tool call:** 10 (1 base + 9 tips)

### Anti-Gaming: AST Fingerprinting

To prevent XP farming through trivial variations:

```python
# These are considered SAME fingerprint (no XP):
def add(a, b): return a + b
def add(x, y): return x + y      # Variable rename only
def add(a, b):
    return a + b                  # Formatting only

# This is DIFFERENT fingerprint (XP awarded):
def add(a, b): return sum([a, b]) # Different algorithm
```

### Execution Environment

| Environment | Use Case | Limitations |
|-------------|----------|-------------|
| Pyodide (Browser) | Quick Python execution | No filesystem, limited libraries |
| Docker (Server) | Full execution, multiple languages | Requires server, resource limits |

### Current Codebase State (as of Jan 2026)

#### Existing Category (`qubes-gui/src/data/skillDefinitions.ts`)
- **Current ID**: `technical_expertise`
- **Current Name**: "Technical Expertise"
- **Target ID**: `coding` (rename)
- **Target Name**: "Coding"
- **Action**: Rename category ID and display name

#### Existing Skills
- **Current Sun tool**: `web_search` (WRONG - this is an intelligent routing tool)
- **Current Planets**: programming, devops, system_architecture, debugging, api_integration
- **Current Moons**: 10 moons across planets
- **Action**: Replace entire skill tree with new results-focused structure

#### Tool Mappings (`ai/skill_scanner.py:62-64`)
- **Current mappings** (to be replaced):
  ```python
  "debug_systematically": "debugging"
  "research_with_synthesis": "science"  # Wrong category
  "validate_solution": "debugging"
  ```
- **Target mappings** (new tools with Waitress XP):
  ```python
  "develop_code": "coding"  # Sun
  "run_tests": "testing"
  "debug_code": "debugging"
  # ... 15 more new tool mappings
  ```
- **Action**: Replace old mappings, implement Waitress XP system

#### New Infrastructure Needed
- **AST Fingerprinting**: `ai/tools/ast_fingerprint.py` (NEW)
- **Code Execution**: `ai/tools/code_execution.py` (NEW)
- **Waitress XP Logic**: Extension to `ai/skill_scanner.py`

### Files Modified

| File | Changes |
|------|---------|
| `utils/skill_definitions.py` | Add Coding skills (18 total) |
| `ai/skill_scanner.py` | Add 18 tool mappings, add waitress XP logic |
| `ai/tools/handlers.py` | Add 18 handler functions |
| `ai/tools/registry.py` | Register 18 tools |
| `ai/tools/code_execution.py` | NEW: Code execution infrastructure |
| `ai/tools/ast_fingerprint.py` | NEW: AST fingerprinting system |
| `qubes-gui/src/data/skillDefinitions.ts` | Add Coding skill definitions |

---

## 2. Prerequisites & Dependencies

### Phase 0 Requirements

These Phase 0 items MUST be completed before Phase 3:

- [x] XP values updated (standard 5/2.5/0 for other categories)
- [x] LEARNING block type added to `core/block.py`
- [x] Float XP support confirmed

### New Infrastructure Required

Phase 3 requires NEW infrastructure not in Phase 0:

#### 1. Waitress XP System

**New file needed:** Extend `ai/skill_scanner.py`

```python
def calculate_waitress_xp(execution_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate XP using Waitress model for Coding tools.
    Returns base (1) + tips (0-9) based on milestones.
    """
    base = 1
    tips = 0
    milestones = []

    # Milestone: Code executed successfully
    if execution_result.get("success"):
        tips += 1
        milestones.append("executed_successfully")

    # Milestone: Tests passed
    if execution_result.get("tests_passed"):
        tips += 2
        milestones.append("tests_passed")

    # ... more milestones

    return {
        "base": base,
        "tips": min(tips, 9),  # Cap at 9
        "total": base + min(tips, 9),
        "milestones": milestones
    }
```

#### 2. AST Fingerprinting System

**New file:** `ai/tools/ast_fingerprint.py`

```python
import ast
import hashlib
from typing import Dict, Any, Optional

class ASTFingerprinter:
    """
    Generate structural fingerprints from code to detect duplicates.
    Ignores variable names, comments, and formatting.
    """

    def fingerprint(self, code: str, language: str = "python") -> str:
        """Generate AST fingerprint for code."""
        if language == "python":
            return self._fingerprint_python(code)
        elif language == "javascript":
            return self._fingerprint_javascript(code)
        else:
            # Fallback: normalize and hash
            return self._fingerprint_generic(code)

    def _fingerprint_python(self, code: str) -> str:
        """Generate fingerprint for Python code."""
        try:
            tree = ast.parse(code)
            # Normalize the AST (remove names, just keep structure)
            normalized = self._normalize_python_ast(tree)
            return hashlib.sha256(normalized.encode()).hexdigest()[:16]
        except SyntaxError:
            return self._fingerprint_generic(code)

    def _normalize_python_ast(self, tree: ast.AST) -> str:
        """Convert AST to normalized string representation."""
        # ... implementation
```

#### 3. Code Execution Environment

**New file:** `ai/tools/code_execution.py`

```python
class CodeExecutor:
    """
    Safe code execution environment.
    Supports Pyodide (browser) and Docker (server).
    """

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout_ms: int = 5000,
        memory_limit_mb: int = 128
    ) -> Dict[str, Any]:
        """Execute code safely and return results."""
        # ... implementation
```

### Existing Systems Leveraged

#### 1. LLM Integration

**File:** `ai/tools/handlers.py`
**Function:** `call_model_directly(qube, system_prompt, user_prompt)`

Used by code generation, analysis, and explanation tools.

#### 2. Block Creation

**File:** `core/block.py`
**Class:** `Block`

Creates LEARNING blocks to store coding insights.

---

## 3. Task 3.1: Update Skill Definitions

### Python Backend

**File:** `utils/skill_definitions.py`
**Location:** Add after existing categories

#### New Coding Skills

```python
# ===== CODING (18 skills) =====
# Theme: Ship It - results-focused coding with Waitress XP model

# Sun
skills.append(_create_skill(
    "coding",
    "Coding",
    "Master the art of writing and shipping working code",
    "coding",
    "sun",
    tool_reward="develop_code",
    icon="💻"
))

# Planet 1: Testing
skills.append(_create_skill(
    "testing",
    "Testing",
    "Write and run tests to verify code works correctly",
    "coding",
    "planet",
    "coding",
    tool_reward="run_tests",
    icon="🧪"
))

# Moon 1.1: Unit Tests
skills.append(_create_skill(
    "unit_tests",
    "Unit Tests",
    "Write focused tests for individual functions",
    "coding",
    "moon",
    "testing",
    tool_reward="write_unit_test",
    icon="🔬"
))

# Moon 1.2: Test Coverage
skills.append(_create_skill(
    "test_coverage",
    "Test Coverage",
    "Measure and improve test coverage",
    "coding",
    "moon",
    "testing",
    tool_reward="measure_coverage",
    icon="📊"
))

# Planet 2: Debugging
skills.append(_create_skill(
    "debugging",
    "Debugging",
    "Find and fix bugs systematically",
    "coding",
    "planet",
    "coding",
    tool_reward="debug_code",
    icon="🐛"
))

# Moon 2.1: Error Analysis
skills.append(_create_skill(
    "error_analysis",
    "Error Analysis",
    "Understand WHAT went wrong from error messages",
    "coding",
    "moon",
    "debugging",
    tool_reward="analyze_error",
    icon="🔍"
))

# Moon 2.2: Root Cause
skills.append(_create_skill(
    "root_cause",
    "Root Cause",
    "Understand WHY the error happened",
    "coding",
    "moon",
    "debugging",
    tool_reward="find_root_cause",
    icon="🎯"
))

# Planet 3: Algorithms
skills.append(_create_skill(
    "algorithms",
    "Algorithms",
    "Optimize code performance and efficiency",
    "coding",
    "planet",
    "coding",
    tool_reward="benchmark_code",
    icon="⚡"
))

# Moon 3.1: Complexity Analysis
skills.append(_create_skill(
    "complexity_analysis",
    "Complexity Analysis",
    "Understand Big O time and space complexity",
    "coding",
    "moon",
    "algorithms",
    tool_reward="analyze_complexity",
    icon="📈"
))

# Moon 3.2: Performance Tuning
skills.append(_create_skill(
    "performance_tuning",
    "Performance Tuning",
    "Make code faster through optimization",
    "coding",
    "moon",
    "algorithms",
    tool_reward="tune_performance",
    icon="🚀"
))

# Planet 4: Hacking
skills.append(_create_skill(
    "hacking",
    "Hacking",
    "Find and exploit security vulnerabilities",
    "coding",
    "planet",
    "coding",
    tool_reward="security_scan",
    icon="🔓"
))

# Moon 4.1: Exploits
skills.append(_create_skill(
    "exploits",
    "Exploits",
    "Discover exploitable vulnerabilities",
    "coding",
    "moon",
    "hacking",
    tool_reward="find_exploit",
    icon="💉"
))

# Moon 4.2: Reverse Engineering
skills.append(_create_skill(
    "reverse_engineering",
    "Reverse Engineering",
    "Understand systems by taking them apart",
    "coding",
    "moon",
    "hacking",
    tool_reward="reverse_engineer",
    icon="🔧"
))

# Moon 4.3: Penetration Testing
skills.append(_create_skill(
    "penetration_testing",
    "Penetration Testing",
    "Systematic security testing methodology",
    "coding",
    "moon",
    "hacking",
    tool_reward="pen_test",
    icon="🛡️"
))

# Planet 5: Code Review
skills.append(_create_skill(
    "code_review",
    "Code Review",
    "Critique and improve code quality",
    "coding",
    "planet",
    "coding",
    tool_reward="review_code",
    icon="👀"
))

# Moon 5.1: Refactoring
skills.append(_create_skill(
    "refactoring",
    "Refactoring",
    "Improve code structure without changing behavior",
    "coding",
    "moon",
    "code_review",
    tool_reward="refactor_code",
    icon="♻️"
))

# Moon 5.2: Version Control
skills.append(_create_skill(
    "version_control",
    "Version Control",
    "Manage code changes with git",
    "coding",
    "moon",
    "code_review",
    tool_reward="git_operation",
    icon="📚"
))

# Moon 5.3: Documentation
skills.append(_create_skill(
    "documentation",
    "Documentation",
    "Write clear documentation for code",
    "coding",
    "moon",
    "code_review",
    tool_reward="generate_docs",
    icon="📝"
))
```

### Verification

After adding, verify count:

```python
coding_skills = [s for s in skills if s["category"] == "coding"]
assert len(coding_skills) == 18, f"Expected 18, got {len(coding_skills)}"

# Verify hierarchy
sun = [s for s in coding_skills if s["tier"] == "sun"]
planets = [s for s in coding_skills if s["tier"] == "planet"]
moons = [s for s in coding_skills if s["tier"] == "moon"]

assert len(sun) == 1, "Should have 1 Sun"
assert len(planets) == 5, "Should have 5 Planets"
assert len(moons) == 12, "Should have 12 Moons"
```

---

## 4. Task 3.2: Update TOOL_TO_SKILL_MAPPING

### File: `ai/skill_scanner.py`

**Location:** Lines 44-85 (TOOL_TO_SKILL_MAPPING dictionary)

#### Add Coding Tool Mappings

```python
TOOL_TO_SKILL_MAPPING = {
    # ... existing mappings ...

    # ===== CODING (18 tools) =====
    # Sun
    "develop_code": "coding",

    # Planet 1: Testing
    "run_tests": "testing",
    "write_unit_test": "unit_tests",
    "measure_coverage": "test_coverage",

    # Planet 2: Debugging
    "debug_code": "debugging",
    "analyze_error": "error_analysis",
    "find_root_cause": "root_cause",

    # Planet 3: Algorithms
    "benchmark_code": "algorithms",
    "analyze_complexity": "complexity_analysis",
    "tune_performance": "performance_tuning",

    # Planet 4: Hacking
    "security_scan": "hacking",
    "find_exploit": "exploits",
    "reverse_engineer": "reverse_engineering",
    "pen_test": "penetration_testing",

    # Planet 5: Code Review
    "review_code": "code_review",
    "refactor_code": "refactoring",
    "git_operation": "version_control",
    "generate_docs": "documentation",
}
```

### Add Coding Category to XP Logic

**File:** `ai/skill_scanner.py`
**Location:** Lines 290-296 (XP calculation)

#### Current State

```python
def calculate_xp(tool_name: str, success: bool, completed: bool) -> float:
    """Calculate XP for tool usage."""
    if success:
        return 5.0
    elif completed:
        return 2.5
    else:
        return 0.0
```

#### Target State

```python
# Set of tools that use Waitress XP model
WAITRESS_XP_TOOLS = {
    "develop_code", "run_tests", "write_unit_test", "measure_coverage",
    "debug_code", "analyze_error", "find_root_cause",
    "benchmark_code", "analyze_complexity", "tune_performance",
    "security_scan", "find_exploit", "reverse_engineer", "pen_test",
    "review_code", "refactor_code", "git_operation", "generate_docs"
}

def calculate_xp(
    tool_name: str,
    success: bool,
    completed: bool,
    execution_result: Optional[Dict[str, Any]] = None
) -> float:
    """
    Calculate XP for tool usage.

    Standard model: 5/2.5/0
    Waitress model (Coding): 1 base + 0-9 tips
    """
    if tool_name in WAITRESS_XP_TOOLS:
        return calculate_waitress_xp(execution_result or {})["total"]

    # Standard XP model
    if success:
        return 5.0
    elif completed:
        return 2.5
    else:
        return 0.0


def calculate_waitress_xp(execution_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate XP using Waitress model for Coding tools.

    Base: 1 XP (always awarded for completing task)
    Tips: 0-9 XP based on quality milestones

    Returns dict with base, tips, total, and milestones achieved.
    """
    base = 1
    tips = 0
    milestones = []

    # Milestone 1: Code executed without error (+1)
    if execution_result.get("executed", False):
        tips += 1
        milestones.append("executed_successfully")

    # Milestone 2: All tests pass (+2)
    test_results = execution_result.get("test_results", {})
    if test_results.get("all_passed", False):
        tips += 2
        milestones.append("all_tests_passed")

    # Milestone 3: Coverage > 80% (+1)
    coverage = execution_result.get("coverage_percent", 0)
    if coverage >= 80:
        tips += 1
        milestones.append("high_coverage")

    # Milestone 4: No security vulnerabilities (+1)
    vulns = execution_result.get("vulnerabilities", [])
    if len(vulns) == 0:
        tips += 1
        milestones.append("no_vulnerabilities")

    # Milestone 5: Performance within threshold (+1)
    perf = execution_result.get("performance", {})
    if perf.get("within_threshold", False):
        tips += 1
        milestones.append("good_performance")

    # Milestone 6: No linting errors (+1)
    lint_errors = execution_result.get("lint_errors", [])
    if len(lint_errors) == 0:
        tips += 1
        milestones.append("clean_code")

    # Milestone 7: Novel code (not duplicate fingerprint) (+1)
    if execution_result.get("is_novel", True):
        tips += 1
        milestones.append("novel_approach")

    # Cap tips at 9
    tips = min(tips, 9)

    return {
        "base": base,
        "tips": tips,
        "total": base + tips,
        "milestones": milestones,
        "model": "waitress"
    }
```

---

## 5. Task 3.3: Implement Waitress XP System

### Overview

The Waitress XP system rewards quality over quantity. Like a waitress earning tips based on service quality, the Qube earns XP based on code quality milestones.

### Full Implementation

**File:** `ai/tools/waitress_xp.py` (NEW FILE)

```python
"""
Waitress XP System for Coding Tools

The Waitress model awards:
- Base: 1 XP (always, for completing the task)
- Tips: 0-9 XP (based on quality milestones)

This prevents XP farming through trivial code submissions while
rewarding genuine effort and quality.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class Milestone(Enum):
    """Quality milestones that earn tip XP."""
    EXECUTED = "executed_successfully"
    TESTS_PASSED = "all_tests_passed"
    HIGH_COVERAGE = "high_coverage"
    NO_VULNERABILITIES = "no_vulnerabilities"
    GOOD_PERFORMANCE = "good_performance"
    CLEAN_CODE = "clean_code"
    NOVEL_APPROACH = "novel_approach"
    WELL_DOCUMENTED = "well_documented"
    FOLLOWS_PATTERNS = "follows_patterns"


# Milestone tip values
MILESTONE_TIPS = {
    Milestone.EXECUTED: 1,
    Milestone.TESTS_PASSED: 2,
    Milestone.HIGH_COVERAGE: 1,
    Milestone.NO_VULNERABILITIES: 1,
    Milestone.GOOD_PERFORMANCE: 1,
    Milestone.CLEAN_CODE: 1,
    Milestone.NOVEL_APPROACH: 1,
    Milestone.WELL_DOCUMENTED: 0.5,
    Milestone.FOLLOWS_PATTERNS: 0.5,
}


@dataclass
class WaitressXPResult:
    """Result of Waitress XP calculation."""
    base: float
    tips: float
    total: float
    milestones: List[str]
    details: Dict[str, Any]


class WaitressXPCalculator:
    """
    Calculate XP using the Waitress model.

    Usage:
        calculator = WaitressXPCalculator()
        result = calculator.calculate(execution_result)
        xp = result.total  # 1-10 XP
    """

    def __init__(self, base_xp: float = 1.0, max_tips: float = 9.0):
        self.base_xp = base_xp
        self.max_tips = max_tips

    def calculate(self, execution_result: Dict[str, Any]) -> WaitressXPResult:
        """
        Calculate Waitress XP from execution result.

        Args:
            execution_result: Dict containing execution metrics:
                - executed: bool - Did code run without crashing?
                - test_results: Dict with all_passed, passed, failed
                - coverage_percent: float - Test coverage percentage
                - vulnerabilities: List - Security issues found
                - performance: Dict with within_threshold, time_ms
                - lint_errors: List - Linting issues
                - is_novel: bool - Is this a new fingerprint?
                - has_docs: bool - Does code have documentation?
                - follows_patterns: bool - Does code follow project patterns?

        Returns:
            WaitressXPResult with base, tips, total, and milestones
        """
        tips = 0.0
        milestones = []
        details = {}

        # Check each milestone
        if execution_result.get("executed", False):
            tips += MILESTONE_TIPS[Milestone.EXECUTED]
            milestones.append(Milestone.EXECUTED.value)
            details["executed"] = True

        test_results = execution_result.get("test_results", {})
        if test_results.get("all_passed", False):
            tips += MILESTONE_TIPS[Milestone.TESTS_PASSED]
            milestones.append(Milestone.TESTS_PASSED.value)
            details["tests"] = {
                "passed": test_results.get("passed", 0),
                "total": test_results.get("total", 0)
            }

        coverage = execution_result.get("coverage_percent", 0)
        if coverage >= 80:
            tips += MILESTONE_TIPS[Milestone.HIGH_COVERAGE]
            milestones.append(Milestone.HIGH_COVERAGE.value)
            details["coverage"] = coverage

        vulns = execution_result.get("vulnerabilities", [])
        if len(vulns) == 0:
            tips += MILESTONE_TIPS[Milestone.NO_VULNERABILITIES]
            milestones.append(Milestone.NO_VULNERABILITIES.value)
        else:
            details["vulnerabilities_found"] = len(vulns)

        perf = execution_result.get("performance", {})
        if perf.get("within_threshold", False):
            tips += MILESTONE_TIPS[Milestone.GOOD_PERFORMANCE]
            milestones.append(Milestone.GOOD_PERFORMANCE.value)
            details["execution_time_ms"] = perf.get("time_ms")

        lint_errors = execution_result.get("lint_errors", [])
        if len(lint_errors) == 0:
            tips += MILESTONE_TIPS[Milestone.CLEAN_CODE]
            milestones.append(Milestone.CLEAN_CODE.value)
        else:
            details["lint_errors"] = len(lint_errors)

        if execution_result.get("is_novel", True):
            tips += MILESTONE_TIPS[Milestone.NOVEL_APPROACH]
            milestones.append(Milestone.NOVEL_APPROACH.value)
        else:
            details["duplicate_fingerprint"] = True

        if execution_result.get("has_docs", False):
            tips += MILESTONE_TIPS[Milestone.WELL_DOCUMENTED]
            milestones.append(Milestone.WELL_DOCUMENTED.value)

        if execution_result.get("follows_patterns", False):
            tips += MILESTONE_TIPS[Milestone.FOLLOWS_PATTERNS]
            milestones.append(Milestone.FOLLOWS_PATTERNS.value)

        # Cap tips
        tips = min(tips, self.max_tips)

        return WaitressXPResult(
            base=self.base_xp,
            tips=tips,
            total=self.base_xp + tips,
            milestones=milestones,
            details=details
        )

    def calculate_for_tool(
        self,
        tool_name: str,
        execution_result: Dict[str, Any]
    ) -> WaitressXPResult:
        """
        Calculate XP with tool-specific milestone weights.

        Different tools emphasize different milestones:
        - run_tests: Heavier weight on test passing
        - security_scan: Heavier weight on finding vulns
        - benchmark_code: Heavier weight on performance
        """
        # For now, use same calculation for all tools
        # Can be extended with tool-specific logic
        return self.calculate(execution_result)


# Singleton instance
_calculator = WaitressXPCalculator()


def calculate_waitress_xp(execution_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to calculate Waitress XP.

    Returns dict compatible with existing XP system.
    """
    result = _calculator.calculate(execution_result)
    return {
        "base": result.base,
        "tips": result.tips,
        "total": result.total,
        "milestones": result.milestones,
        "details": result.details,
        "model": "waitress"
    }
```

---

## 6. Task 3.4: Implement AST Fingerprinting

### Overview

AST (Abstract Syntax Tree) fingerprinting creates a structural hash of code that ignores superficial changes like variable names, comments, and formatting. This prevents XP farming through trivial variations.

### Full Implementation

**File:** `ai/tools/ast_fingerprint.py` (NEW FILE)

```python
"""
AST Fingerprinting System for Anti-Gaming

Generates structural fingerprints from code to detect duplicates.
Two pieces of code with the same fingerprint are structurally identical,
even if they have different variable names, comments, or formatting.

Example - Same fingerprint:
    def add(a, b): return a + b
    def add(x, y): return x + y

Example - Different fingerprint:
    def add(a, b): return a + b
    def add(a, b): return sum([a, b])
"""

import ast
import hashlib
import re
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass


@dataclass
class FingerprintResult:
    """Result of fingerprinting operation."""
    fingerprint: str
    language: str
    node_count: int
    structure_summary: str
    is_duplicate: bool = False
    original_fingerprint: Optional[str] = None


class ASTFingerprinter:
    """
    Generate structural fingerprints from code.

    Usage:
        fp = ASTFingerprinter()
        result = fp.fingerprint("def add(a, b): return a + b", "python")
        print(result.fingerprint)  # "a1b2c3d4..."
    """

    def __init__(self):
        # Store seen fingerprints for duplicate detection
        self._seen_fingerprints: Set[str] = set()

    def fingerprint(
        self,
        code: str,
        language: str = "python",
        check_duplicate: bool = True
    ) -> FingerprintResult:
        """
        Generate fingerprint for code.

        Args:
            code: Source code to fingerprint
            language: Programming language (python, javascript, etc.)
            check_duplicate: Whether to check against seen fingerprints

        Returns:
            FingerprintResult with fingerprint and metadata
        """
        if language == "python":
            return self._fingerprint_python(code, check_duplicate)
        elif language in ["javascript", "js", "typescript", "ts"]:
            return self._fingerprint_javascript(code, check_duplicate)
        else:
            return self._fingerprint_generic(code, language, check_duplicate)

    def _fingerprint_python(
        self,
        code: str,
        check_duplicate: bool
    ) -> FingerprintResult:
        """Generate fingerprint for Python code using AST."""
        try:
            tree = ast.parse(code)
            normalized = self._normalize_python_ast(tree)
            fp = hashlib.sha256(normalized.encode()).hexdigest()[:16]

            is_dup = fp in self._seen_fingerprints if check_duplicate else False
            if check_duplicate and not is_dup:
                self._seen_fingerprints.add(fp)

            return FingerprintResult(
                fingerprint=fp,
                language="python",
                node_count=self._count_nodes(tree),
                structure_summary=self._summarize_structure(tree),
                is_duplicate=is_dup
            )
        except SyntaxError as e:
            # Fall back to generic fingerprinting
            return self._fingerprint_generic(code, "python", check_duplicate)

    def _normalize_python_ast(self, tree: ast.AST) -> str:
        """
        Convert Python AST to normalized string.

        Removes:
        - Variable names (replaced with positional markers)
        - String literal values (replaced with placeholder)
        - Number literal values (replaced with type marker)
        - Comments (not in AST anyway)

        Preserves:
        - Structure (functions, classes, loops, conditionals)
        - Operation types (add, sub, call, etc.)
        - Control flow
        """
        return self._ast_to_normalized_string(tree)

    def _ast_to_normalized_string(self, node: ast.AST, depth: int = 0) -> str:
        """Recursively convert AST node to normalized string."""
        parts = []

        # Node type is the primary structural element
        node_type = type(node).__name__
        parts.append(f"{node_type}")

        # Handle specific node types
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Keep function structure, not name
            parts.append(f"(args={len(node.args.args)})")

        elif isinstance(node, ast.ClassDef):
            # Keep class structure, not name
            parts.append(f"(bases={len(node.bases)})")

        elif isinstance(node, ast.Call):
            # Keep call structure
            parts.append(f"(args={len(node.args)},kw={len(node.keywords)})")

        elif isinstance(node, ast.BinOp):
            # Keep operator type
            parts.append(f"({type(node.op).__name__})")

        elif isinstance(node, ast.Compare):
            # Keep comparison operators
            ops = [type(op).__name__ for op in node.ops]
            parts.append(f"({','.join(ops)})")

        elif isinstance(node, ast.For) or isinstance(node, ast.While):
            parts.append("(loop)")

        elif isinstance(node, ast.If):
            parts.append("(cond)")

        elif isinstance(node, ast.Return):
            parts.append("(ret)")

        elif isinstance(node, ast.Constant):
            # Replace literal with type marker
            parts.append(f"({type(node.value).__name__})")

        # Recursively process children
        for child in ast.iter_child_nodes(node):
            child_str = self._ast_to_normalized_string(child, depth + 1)
            parts.append(child_str)

        return f"[{'.'.join(parts)}]"

    def _count_nodes(self, tree: ast.AST) -> int:
        """Count total nodes in AST."""
        count = 1
        for child in ast.iter_child_nodes(tree):
            count += self._count_nodes(child)
        return count

    def _summarize_structure(self, tree: ast.AST) -> str:
        """Create human-readable structure summary."""
        funcs = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
        classes = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])
        loops = len([n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))])
        conds = len([n for n in ast.walk(tree) if isinstance(n, ast.If)])

        parts = []
        if funcs: parts.append(f"{funcs} func")
        if classes: parts.append(f"{classes} class")
        if loops: parts.append(f"{loops} loop")
        if conds: parts.append(f"{conds} cond")

        return ", ".join(parts) if parts else "simple"

    def _fingerprint_javascript(
        self,
        code: str,
        check_duplicate: bool
    ) -> FingerprintResult:
        """
        Generate fingerprint for JavaScript code.

        Since we don't have a JS AST parser in Python, use regex-based
        structural extraction.
        """
        # Extract structural elements
        normalized = self._normalize_javascript(code)
        fp = hashlib.sha256(normalized.encode()).hexdigest()[:16]

        is_dup = fp in self._seen_fingerprints if check_duplicate else False
        if check_duplicate and not is_dup:
            self._seen_fingerprints.add(fp)

        return FingerprintResult(
            fingerprint=fp,
            language="javascript",
            node_count=len(normalized.split()),
            structure_summary="js-normalized",
            is_duplicate=is_dup
        )

    def _normalize_javascript(self, code: str) -> str:
        """Normalize JavaScript code for fingerprinting."""
        # Remove comments
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

        # Remove string literals (replace with placeholder)
        code = re.sub(r'"[^"]*"', '"STR"', code)
        code = re.sub(r"'[^']*'", "'STR'", code)
        code = re.sub(r'`[^`]*`', '`STR`', code)

        # Remove number literals (replace with placeholder)
        code = re.sub(r'\b\d+\.?\d*\b', 'NUM', code)

        # Normalize variable names (this is approximate)
        # Replace identifiers with positional markers
        code = re.sub(r'\b(let|const|var)\s+(\w+)', r'\1 VAR', code)
        code = re.sub(r'function\s+(\w+)', r'function FUNC', code)

        # Remove whitespace variations
        code = re.sub(r'\s+', ' ', code)

        return code.strip()

    def _fingerprint_generic(
        self,
        code: str,
        language: str,
        check_duplicate: bool
    ) -> FingerprintResult:
        """
        Generic fingerprinting for unsupported languages.

        Uses text normalization rather than AST parsing.
        """
        # Remove comments (common patterns)
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)  # Python/Shell
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)  # C-style
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)  # Block comments

        # Normalize whitespace
        code = re.sub(r'\s+', ' ', code)

        # Remove string literals
        code = re.sub(r'"[^"]*"', '"S"', code)
        code = re.sub(r"'[^']*'", "'S'", code)

        fp = hashlib.sha256(code.encode()).hexdigest()[:16]

        is_dup = fp in self._seen_fingerprints if check_duplicate else False
        if check_duplicate and not is_dup:
            self._seen_fingerprints.add(fp)

        return FingerprintResult(
            fingerprint=fp,
            language=language,
            node_count=len(code.split()),
            structure_summary="generic-normalized",
            is_duplicate=is_dup
        )

    def clear_seen(self):
        """Clear the set of seen fingerprints."""
        self._seen_fingerprints.clear()

    def load_seen(self, fingerprints: Set[str]):
        """Load previously seen fingerprints (e.g., from database)."""
        self._seen_fingerprints.update(fingerprints)


# Singleton instance
_fingerprinter = ASTFingerprinter()


def fingerprint_code(
    code: str,
    language: str = "python",
    check_duplicate: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to fingerprint code.

    Returns dict with fingerprint and metadata.
    """
    result = _fingerprinter.fingerprint(code, language, check_duplicate)
    return {
        "fingerprint": result.fingerprint,
        "language": result.language,
        "node_count": result.node_count,
        "structure_summary": result.structure_summary,
        "is_duplicate": result.is_duplicate
    }


def is_duplicate_code(code: str, language: str = "python") -> bool:
    """Check if code is a duplicate of previously seen code."""
    result = _fingerprinter.fingerprint(code, language, check_duplicate=True)
    return result.is_duplicate
```

---

## 7. Task 3.5: Implement Code Execution Environment

### Overview

The code execution environment provides safe, sandboxed execution for code generated by Coding tools. Two environments are supported:

| Environment | Use Case | Pros | Cons |
|-------------|----------|------|------|
| Pyodide | Browser-based Python | No server needed, instant | Limited libraries, no filesystem |
| Docker | Server-side multi-language | Full capabilities | Requires server, slower startup |

### Full Implementation

**File:** `ai/tools/code_execution.py` (NEW FILE)

```python
"""
Safe Code Execution Environment

Provides sandboxed execution for generated code.
Supports multiple languages through different backends.
"""

import asyncio
import time
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import json


class ExecutionBackend(Enum):
    """Available execution backends."""
    PYODIDE = "pyodide"      # Browser-based Python (via API)
    DOCKER = "docker"        # Containerized execution
    SUBPROCESS = "subprocess" # Local subprocess (dev only)


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: str
    errors: Optional[str]
    execution_time_ms: float
    memory_used_kb: Optional[int]
    return_value: Any
    backend: str


class CodeExecutor:
    """
    Safe code execution environment.

    Usage:
        executor = CodeExecutor()
        result = await executor.execute(
            code="print('Hello')",
            language="python",
            timeout_ms=5000
        )
    """

    def __init__(
        self,
        default_backend: ExecutionBackend = ExecutionBackend.SUBPROCESS,
        docker_image: str = "python:3.11-slim"
    ):
        self.default_backend = default_backend
        self.docker_image = docker_image
        self._docker_available = self._check_docker()

    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout_ms: int = 5000,
        memory_limit_mb: int = 128,
        backend: Optional[ExecutionBackend] = None,
        input_data: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute code safely and return results.

        Args:
            code: Source code to execute
            language: Programming language
            timeout_ms: Maximum execution time in milliseconds
            memory_limit_mb: Maximum memory usage
            backend: Execution backend (auto-select if None)
            input_data: Optional stdin input

        Returns:
            ExecutionResult with output, errors, and metrics
        """
        backend = backend or self._select_backend(language)

        if backend == ExecutionBackend.DOCKER:
            return await self._execute_docker(
                code, language, timeout_ms, memory_limit_mb, input_data
            )
        elif backend == ExecutionBackend.SUBPROCESS:
            return await self._execute_subprocess(
                code, language, timeout_ms, input_data
            )
        else:
            return ExecutionResult(
                success=False,
                output="",
                errors=f"Backend {backend} not implemented",
                execution_time_ms=0,
                memory_used_kb=None,
                return_value=None,
                backend=backend.value
            )

    def _select_backend(self, language: str) -> ExecutionBackend:
        """Select best backend for language."""
        if self._docker_available:
            return ExecutionBackend.DOCKER
        elif language == "python":
            return ExecutionBackend.SUBPROCESS
        else:
            return ExecutionBackend.DOCKER

    async def _execute_subprocess(
        self,
        code: str,
        language: str,
        timeout_ms: int,
        input_data: Optional[str]
    ) -> ExecutionResult:
        """Execute code via subprocess (Python only for safety)."""
        if language != "python":
            return ExecutionResult(
                success=False,
                output="",
                errors=f"Subprocess backend only supports Python, got {language}",
                execution_time_ms=0,
                memory_used_kb=None,
                return_value=None,
                backend="subprocess"
            )

        # Write code to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            start_time = time.perf_counter()

            # Run with restricted permissions
            process = await asyncio.create_subprocess_exec(
                "python",
                temp_path,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(
                        input=input_data.encode() if input_data else None
                    ),
                    timeout=timeout_ms / 1000
                )
            except asyncio.TimeoutError:
                process.kill()
                return ExecutionResult(
                    success=False,
                    output="",
                    errors=f"Execution timed out after {timeout_ms}ms",
                    execution_time_ms=timeout_ms,
                    memory_used_kb=None,
                    return_value=None,
                    backend="subprocess"
                )

            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000

            return ExecutionResult(
                success=process.returncode == 0,
                output=stdout.decode('utf-8', errors='replace'),
                errors=stderr.decode('utf-8', errors='replace') if stderr else None,
                execution_time_ms=execution_time,
                memory_used_kb=None,
                return_value=None,
                backend="subprocess"
            )

        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass

    async def _execute_docker(
        self,
        code: str,
        language: str,
        timeout_ms: int,
        memory_limit_mb: int,
        input_data: Optional[str]
    ) -> ExecutionResult:
        """Execute code in Docker container."""
        # Select image based on language
        image = self._get_docker_image(language)

        # Write code to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=self._get_file_extension(language),
            delete=False
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            start_time = time.perf_counter()

            # Build Docker command
            cmd = [
                "docker", "run",
                "--rm",                              # Remove container after
                "--network", "none",                 # No network access
                f"--memory={memory_limit_mb}m",      # Memory limit
                "--cpus=0.5",                        # CPU limit
                "-v", f"{temp_path}:/code/main{self._get_file_extension(language)}:ro",
                image,
                *self._get_run_command(language)
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(
                        input=input_data.encode() if input_data else None
                    ),
                    timeout=timeout_ms / 1000 + 5  # Extra time for container startup
                )
            except asyncio.TimeoutError:
                # Kill the container
                subprocess.run(["docker", "kill", process.pid], capture_output=True)
                return ExecutionResult(
                    success=False,
                    output="",
                    errors=f"Execution timed out after {timeout_ms}ms",
                    execution_time_ms=timeout_ms,
                    memory_used_kb=None,
                    return_value=None,
                    backend="docker"
                )

            end_time = time.perf_counter()
            execution_time = (end_time - start_time) * 1000

            return ExecutionResult(
                success=process.returncode == 0,
                output=stdout.decode('utf-8', errors='replace'),
                errors=stderr.decode('utf-8', errors='replace') if stderr else None,
                execution_time_ms=execution_time,
                memory_used_kb=None,  # Could parse from docker stats
                return_value=None,
                backend="docker"
            )

        finally:
            try:
                os.unlink(temp_path)
            except:
                pass

    def _get_docker_image(self, language: str) -> str:
        """Get Docker image for language."""
        images = {
            "python": "python:3.11-slim",
            "javascript": "node:20-slim",
            "typescript": "node:20-slim",
            "go": "golang:1.21-alpine",
            "rust": "rust:1.74-slim",
            "java": "openjdk:17-slim",
        }
        return images.get(language, self.docker_image)

    def _get_file_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "go": ".go",
            "rust": ".rs",
            "java": ".java",
        }
        return extensions.get(language, ".txt")

    def _get_run_command(self, language: str) -> List[str]:
        """Get command to run code for language."""
        commands = {
            "python": ["python", "/code/main.py"],
            "javascript": ["node", "/code/main.js"],
            "typescript": ["npx", "ts-node", "/code/main.ts"],
            "go": ["go", "run", "/code/main.go"],
            "rust": ["rustc", "/code/main.rs", "-o", "/tmp/main", "&&", "/tmp/main"],
            "java": ["java", "/code/main.java"],
        }
        return commands.get(language, ["cat", "/code/main.txt"])


class TestRunner:
    """
    Test execution environment.

    Runs test code against implementation code.
    """

    def __init__(self, executor: Optional[CodeExecutor] = None):
        self.executor = executor or CodeExecutor()

    async def run_tests(
        self,
        code: str,
        test_code: str,
        language: str = "python",
        framework: str = "pytest"
    ) -> Dict[str, Any]:
        """
        Run tests against code.

        Args:
            code: Implementation code
            test_code: Test code
            language: Programming language
            framework: Test framework (pytest, unittest, jest, etc.)

        Returns:
            Dict with test results
        """
        if language == "python":
            return await self._run_python_tests(code, test_code, framework)
        elif language in ["javascript", "typescript"]:
            return await self._run_js_tests(code, test_code, framework)
        else:
            return {
                "success": False,
                "error": f"Test framework not supported for {language}",
                "all_passed": False,
                "total": 0,
                "passed": 0,
                "failed": 0
            }

    async def _run_python_tests(
        self,
        code: str,
        test_code: str,
        framework: str
    ) -> Dict[str, Any]:
        """Run Python tests."""
        # Combine code and tests
        combined = f'''
{code}

# --- Tests ---
{test_code}

if __name__ == "__main__":
    import sys
    if "{framework}" == "pytest":
        import pytest
        sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
    else:
        import unittest
        unittest.main()
'''

        result = await self.executor.execute(
            code=combined,
            language="python",
            timeout_ms=30000  # Tests may take longer
        )

        # Parse test results from output
        return self._parse_python_test_output(result)

    def _parse_python_test_output(
        self,
        result: ExecutionResult
    ) -> Dict[str, Any]:
        """Parse pytest/unittest output."""
        output = result.output + (result.errors or "")

        # Try to extract test counts
        passed = 0
        failed = 0

        # Pytest format: "X passed, Y failed"
        import re
        match = re.search(r'(\d+) passed', output)
        if match:
            passed = int(match.group(1))
        match = re.search(r'(\d+) failed', output)
        if match:
            failed = int(match.group(1))

        # Unittest format: "Ran X tests"
        match = re.search(r'Ran (\d+) test', output)
        if match and passed == 0 and failed == 0:
            total = int(match.group(1))
            if "OK" in output:
                passed = total
            else:
                # Try to count failures
                failures = output.count("FAIL:")
                errors = output.count("ERROR:")
                failed = failures + errors
                passed = total - failed

        total = passed + failed

        return {
            "success": result.success and failed == 0,
            "all_passed": failed == 0 and passed > 0,
            "total": total,
            "passed": passed,
            "failed": failed,
            "output": result.output,
            "errors": result.errors,
            "execution_time_ms": result.execution_time_ms
        }

    async def _run_js_tests(
        self,
        code: str,
        test_code: str,
        framework: str
    ) -> Dict[str, Any]:
        """Run JavaScript tests."""
        # Combine code and tests for Jest/Mocha
        combined = f'''
{code}

// --- Tests ---
{test_code}
'''
        result = await self.executor.execute(
            code=combined,
            language="javascript",
            timeout_ms=30000
        )

        return {
            "success": result.success,
            "all_passed": result.success,
            "total": 0,  # Would need to parse jest output
            "passed": 0,
            "failed": 0 if result.success else 1,
            "output": result.output,
            "errors": result.errors
        }


# Singleton instances
_executor = CodeExecutor()
_test_runner = TestRunner(_executor)


async def execute_code(
    code: str,
    language: str = "python",
    timeout_ms: int = 5000
) -> Dict[str, Any]:
    """Convenience function to execute code."""
    result = await _executor.execute(code, language, timeout_ms)
    return {
        "success": result.success,
        "output": result.output,
        "errors": result.errors,
        "execution_time_ms": result.execution_time_ms,
        "backend": result.backend
    }


async def run_tests(
    code: str,
    test_code: str,
    language: str = "python",
    framework: str = "pytest"
) -> Dict[str, Any]:
    """Convenience function to run tests."""
    return await _test_runner.run_tests(code, test_code, language, framework)
```

---

## 8. Task 3.6: Implement Sun Tool - develop_code

### Tool Specification

| Property | Value |
|----------|-------|
| Tool Name | `develop_code` |
| Skill | `coding` (Sun) |
| Purpose | Write and execute code in one workflow |
| XP Model | Waitress (1 base + 0-9 tips) |

### Full Implementation

**File:** `ai/tools/handlers.py`
**Location:** Add to tool handlers section

```python
# ============================================================================
# CODING TOOLS (Phase 3)
# Theme: Ship It (Results-Focused)
# XP Model: Waitress (base 1 + tips 0-9)
# ============================================================================

from ai.tools.code_execution import execute_code, run_tests, CodeExecutor
from ai.tools.ast_fingerprint import fingerprint_code, is_duplicate_code
from ai.tools.waitress_xp import calculate_waitress_xp


async def develop_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sun Tool: develop_code

    The fundamental coding tool. Writes code based on task description,
    then executes it to verify it works.

    Parameters:
        task: str - Description of what to build
        language: str - Programming language (default: python)
        submit: bool - Whether to submit for XP (default: True)
        test: bool - Whether to include basic tests (default: True)

    Returns:
        success: bool
        code: str - Generated code
        output: str - Execution output
        errors: str | None - Any errors
        xp: dict - XP awarded (Waitress model)
        fingerprint: str - Code fingerprint for anti-gaming

    XP Milestones:
        +1: Code executed without error
        +2: Tests pass (if included)
        +1: No security vulnerabilities detected
        +1: Clean code (no linting issues)
        +1: Novel approach (new fingerprint)
    """
    task = params.get("task")
    language = params.get("language", "python")
    submit = params.get("submit", True)
    include_tests = params.get("test", True)

    if not task:
        return {
            "success": False,
            "error": "Missing required parameter: task"
        }

    # Step 1: Generate code using LLM
    system_prompt = f"""You are an expert {language} programmer.
Write clean, working code that accomplishes the given task.
Include comments explaining the approach.
{"Include basic test cases at the end." if include_tests else ""}
Output ONLY the code, no explanations."""

    user_prompt = f"Task: {task}"

    code_response = await call_model_directly(qube, system_prompt, user_prompt)
    code = extract_code_from_response(code_response, language)

    # Step 2: Fingerprint the code
    fp_result = fingerprint_code(code, language)
    is_novel = not fp_result["is_duplicate"]

    # Step 3: Execute the code
    execution_result = await execute_code(code, language, timeout_ms=10000)

    # Step 4: Run basic security scan
    security_issues = await quick_security_check(code, language)

    # Step 5: Check code quality (linting)
    lint_errors = await quick_lint_check(code, language)

    # Step 6: Run tests if included
    test_results = {"all_passed": False, "total": 0}
    if include_tests and execution_result["success"]:
        # Extract tests from the code
        tests = extract_tests_from_code(code, language)
        if tests:
            test_results = await run_tests(code, tests, language)

    # Step 7: Calculate XP (Waitress model)
    xp_result = {"total": 0, "milestones": [], "model": "waitress"}
    if submit:
        xp_input = {
            "executed": execution_result["success"],
            "test_results": test_results,
            "vulnerabilities": security_issues,
            "lint_errors": lint_errors,
            "is_novel": is_novel
        }
        xp_result = calculate_waitress_xp(xp_input)

        # Award XP to the skill
        await award_xp_to_skill(qube, "coding", xp_result["total"])

    # Step 8: Create LEARNING block if successful
    if execution_result["success"]:
        await create_coding_learning_block(
            qube=qube,
            task=task,
            code=code,
            language=language,
            fingerprint=fp_result["fingerprint"],
            xp_result=xp_result
        )

    return {
        "success": execution_result["success"],
        "code": code,
        "output": execution_result["output"],
        "errors": execution_result.get("errors"),
        "execution_time_ms": execution_result["execution_time_ms"],
        "fingerprint": fp_result["fingerprint"],
        "is_novel": is_novel,
        "test_results": test_results if include_tests else None,
        "security_issues": security_issues,
        "lint_errors": lint_errors,
        "xp": xp_result
    }


def extract_code_from_response(response: str, language: str) -> str:
    """Extract code from LLM response, handling markdown code blocks."""
    import re

    # Try to find code block with language tag
    pattern = rf'```{language}\n(.*?)```'
    match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try generic code block
    pattern = r'```\n(.*?)```'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # No code block, return as-is (might be raw code)
    return response.strip()


def extract_tests_from_code(code: str, language: str) -> Optional[str]:
    """Extract test section from code."""
    if language == "python":
        # Look for test functions
        import re
        tests = re.findall(r'(def test_\w+.*?)(?=\ndef |\Z)', code, re.DOTALL)
        if tests:
            return "\n\n".join(tests)

        # Look for unittest class
        match = re.search(r'(class Test\w+.*)', code, re.DOTALL)
        if match:
            return match.group(1)

    return None


async def quick_security_check(code: str, language: str) -> List[str]:
    """Quick security check for obvious vulnerabilities."""
    issues = []

    # Python-specific checks
    if language == "python":
        dangerous_patterns = [
            (r'eval\s*\(', "Use of eval() - potential code injection"),
            (r'exec\s*\(', "Use of exec() - potential code injection"),
            (r'os\.system\s*\(', "Use of os.system() - potential command injection"),
            (r'subprocess\.call\s*\(.*shell\s*=\s*True', "Shell=True in subprocess - command injection risk"),
            (r'pickle\.loads?\s*\(', "Use of pickle - potential arbitrary code execution"),
            (r'__import__\s*\(', "Dynamic import - potential security risk"),
        ]

        import re
        for pattern, message in dangerous_patterns:
            if re.search(pattern, code):
                issues.append(message)

    # JavaScript-specific checks
    elif language in ["javascript", "typescript"]:
        dangerous_patterns = [
            (r'eval\s*\(', "Use of eval() - potential code injection"),
            (r'innerHTML\s*=', "Direct innerHTML assignment - potential XSS"),
            (r'document\.write\s*\(', "Use of document.write - potential XSS"),
        ]

        import re
        for pattern, message in dangerous_patterns:
            if re.search(pattern, code):
                issues.append(message)

    return issues


async def quick_lint_check(code: str, language: str) -> List[str]:
    """Quick lint check for code quality issues."""
    issues = []

    if language == "python":
        # Basic Python style checks
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(f"Line {i} exceeds 120 characters")
            if '\t' in line and '    ' in line:
                issues.append(f"Line {i} has mixed tabs and spaces")

        # Check for missing docstrings on functions
        import re
        functions = re.findall(r'def (\w+)\([^)]*\):', code)
        for func in functions:
            if func.startswith('_'):
                continue  # Skip private functions
            pattern = rf'def {func}\([^)]*\):\s*\n\s*"""'
            if not re.search(pattern, code):
                # Not critical, just a note
                pass

    return issues


async def create_coding_learning_block(
    qube,
    task: str,
    code: str,
    language: str,
    fingerprint: str,
    xp_result: Dict[str, Any]
) -> None:
    """Create LEARNING block for successful code development."""
    from core.block import Block, BlockType

    learning_data = {
        "learning_type": "procedure",
        "domain": "coding",
        "task": task,
        "language": language,
        "fingerprint": fingerprint,
        "code_summary": summarize_code(code, language),
        "milestones_achieved": xp_result.get("milestones", []),
        "xp_earned": xp_result.get("total", 0),
        "source": "develop_code",
        "confidence": calculate_confidence(xp_result)
    }

    block = Block(
        block_type=BlockType.LEARNING,
        data=learning_data
    )

    await qube.chain_state.add_block(block)


def summarize_code(code: str, language: str) -> str:
    """Create a brief summary of what the code does."""
    # Extract first docstring or comment
    import re

    if language == "python":
        # Look for module docstring
        match = re.search(r'^"""(.*?)"""', code, re.DOTALL)
        if match:
            return match.group(1).strip()[:200]

        # Look for first function/class docstring
        match = re.search(r'def \w+.*?:\s*"""(.*?)"""', code, re.DOTALL)
        if match:
            return match.group(1).strip()[:200]

    # Fallback: first comment
    match = re.search(r'#\s*(.+)', code)
    if match:
        return match.group(1).strip()[:200]

    return f"{language} code ({len(code)} chars)"


def calculate_confidence(xp_result: Dict[str, Any]) -> float:
    """Calculate confidence score based on XP milestones."""
    milestones = xp_result.get("milestones", [])
    total_possible = 7  # Total possible milestones

    return min(1.0, len(milestones) / total_possible)


async def award_xp_to_skill(qube, skill_id: str, xp_amount: float) -> None:
    """Award XP to a skill."""
    # This integrates with the existing XP system
    current_xp = qube.chain_state.get_skill_xp(skill_id)
    new_xp = current_xp + xp_amount
    qube.chain_state.set_skill_xp(skill_id, new_xp)

    # Check for level up / unlocks
    await check_skill_unlocks(qube, skill_id, new_xp)
```

---

## 9. Task 3.7: Implement Testing Planet

### Planet Tool: run_tests

```python
async def run_tests_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: run_tests

    Execute a test suite against code.
    Returns detailed results including pass/fail and coverage.

    Parameters:
        code: str - Code to test
        test_code: str - Test suite
        framework: str - Test framework (default: pytest)
        coverage: bool - Measure coverage (default: True)

    Returns:
        success: bool
        all_passed: bool
        total_tests: int
        passed: int
        failed: int
        coverage_percent: float | None
        failures: list - Details of failed tests
        xp: dict - Waitress XP result
    """
    code = params.get("code")
    test_code = params.get("test_code")
    framework = params.get("framework", "pytest")
    measure_coverage = params.get("coverage", True)

    if not code or not test_code:
        return {
            "success": False,
            "error": "Missing required parameters: code and test_code"
        }

    # Run tests
    result = await run_tests(code, test_code, "python", framework)

    # Measure coverage if requested
    coverage_percent = None
    if measure_coverage and result["all_passed"]:
        coverage_result = await measure_code_coverage(code, test_code)
        coverage_percent = coverage_result.get("percent", 0)

    # Calculate XP
    xp_input = {
        "executed": True,
        "test_results": result,
        "coverage_percent": coverage_percent or 0,
        "is_novel": True  # Tests are always novel
    }
    xp_result = calculate_waitress_xp(xp_input)

    await award_xp_to_skill(qube, "testing", xp_result["total"])

    return {
        "success": result["success"],
        "all_passed": result["all_passed"],
        "total_tests": result["total"],
        "passed": result["passed"],
        "failed": result["failed"],
        "coverage_percent": coverage_percent,
        "failures": result.get("failure_details", []),
        "output": result["output"],
        "xp": xp_result
    }


async def measure_code_coverage(code: str, test_code: str) -> Dict[str, Any]:
    """Measure test coverage using coverage.py"""
    combined = f'''
import coverage
cov = coverage.Coverage()
cov.start()

{code}

cov.stop()
cov.save()

# Run tests
{test_code}

# Report
print(f"COVERAGE:{{cov.report()}}")
'''

    result = await execute_code(combined, "python", timeout_ms=30000)

    # Parse coverage from output
    import re
    match = re.search(r'COVERAGE:(\d+)', result["output"])
    if match:
        return {"percent": int(match.group(1))}

    return {"percent": 0}
```

### Moon Tool: write_unit_test

```python
async def write_unit_test(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: write_unit_test

    Generate unit tests for a function or class.
    Uses LLM to analyze code and create appropriate test cases.

    Parameters:
        code: str - Code to test
        focus: str - Specific function/class to test (optional)
        framework: str - Test framework (default: pytest)

    Returns:
        success: bool
        test_code: str - Generated test code
        functions_covered: list - Functions that have tests
        test_count: int - Number of test cases generated
        xp: dict
    """
    code = params.get("code")
    focus = params.get("focus")
    framework = params.get("framework", "pytest")

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    # Analyze code structure
    functions = extract_functions_from_code(code)
    if focus:
        functions = [f for f in functions if f["name"] == focus]

    if not functions:
        return {
            "success": False,
            "error": f"No functions found{' matching ' + focus if focus else ''}"
        }

    # Generate tests using LLM
    system_prompt = f"""You are an expert at writing {framework} tests.
Generate comprehensive unit tests for the given code.
Include edge cases, error cases, and typical use cases.
Output ONLY the test code, no explanations."""

    user_prompt = f"""Code to test:
```python
{code}
```

{"Focus on: " + focus if focus else "Generate tests for all functions."}
Framework: {framework}"""

    test_code = await call_model_directly(qube, system_prompt, user_prompt)
    test_code = extract_code_from_response(test_code, "python")

    # Count tests generated
    test_count = test_code.count("def test_")

    # Calculate XP
    xp_input = {
        "executed": True,
        "is_novel": True
    }
    xp_result = calculate_waitress_xp(xp_input)

    await award_xp_to_skill(qube, "unit_tests", xp_result["total"])

    return {
        "success": True,
        "test_code": test_code,
        "functions_covered": [f["name"] for f in functions],
        "test_count": test_count,
        "framework": framework,
        "xp": xp_result
    }


def extract_functions_from_code(code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from Python code."""
    import ast

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append({
                "name": node.name,
                "args": [arg.arg for arg in node.args.args],
                "has_docstring": (
                    isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Constant) and
                    isinstance(node.body[0].value.value, str)
                ) if node.body else False
            })

    return functions
```

### Moon Tool: measure_coverage

```python
async def measure_coverage_handler(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: measure_coverage

    Measure test coverage and identify untested areas.
    Returns detailed coverage report with suggestions.

    Parameters:
        code: str - Code to analyze
        test_code: str - Test suite

    Returns:
        success: bool
        coverage_percent: float
        lines_covered: int
        lines_total: int
        uncovered_lines: list
        suggestions: list - Suggestions for improving coverage
        xp: dict
    """
    code = params.get("code")
    test_code = params.get("test_code")

    if not code or not test_code:
        return {"success": False, "error": "Missing code or test_code"}

    # Run with coverage measurement
    coverage_code = f'''
import coverage
import sys
from io import StringIO

# Capture coverage
cov = coverage.Coverage(source=["."])
cov.start()

# The code under test
{code}

# Run tests
{test_code}

cov.stop()

# Generate report
output = StringIO()
percent = cov.report(file=output)
report = output.getvalue()

# Get uncovered lines
analysis = cov.analysis2(".")
uncovered = analysis[3] if len(analysis) > 3 else []

print(f"COVERAGE_PERCENT:{percent}")
print(f"UNCOVERED_LINES:{uncovered}")
print(f"REPORT:{report}")
'''

    result = await execute_code(coverage_code, "python", timeout_ms=30000)

    # Parse results
    import re

    coverage_percent = 0
    match = re.search(r'COVERAGE_PERCENT:(\d+\.?\d*)', result["output"])
    if match:
        coverage_percent = float(match.group(1))

    uncovered_lines = []
    match = re.search(r'UNCOVERED_LINES:\[(.*?)\]', result["output"])
    if match:
        uncovered_lines = [int(x) for x in match.group(1).split(",") if x.strip().isdigit()]

    # Generate suggestions
    suggestions = generate_coverage_suggestions(code, uncovered_lines)

    # Calculate XP
    xp_input = {
        "executed": True,
        "coverage_percent": coverage_percent,
        "is_novel": True
    }
    xp_result = calculate_waitress_xp(xp_input)

    await award_xp_to_skill(qube, "test_coverage", xp_result["total"])

    return {
        "success": True,
        "coverage_percent": coverage_percent,
        "lines_covered": int(coverage_percent),  # Simplified
        "lines_total": len(code.split('\n')),
        "uncovered_lines": uncovered_lines,
        "suggestions": suggestions,
        "xp": xp_result
    }


def generate_coverage_suggestions(code: str, uncovered_lines: List[int]) -> List[str]:
    """Generate suggestions for improving coverage."""
    suggestions = []

    lines = code.split('\n')
    for line_num in uncovered_lines[:5]:  # Top 5 suggestions
        if 0 < line_num <= len(lines):
            line = lines[line_num - 1].strip()
            if line.startswith('if '):
                suggestions.append(f"Line {line_num}: Add test for conditional branch: {line[:50]}")
            elif line.startswith('except'):
                suggestions.append(f"Line {line_num}: Add test that triggers exception handler")
            elif line.startswith('return'):
                suggestions.append(f"Line {line_num}: Add test that reaches this return statement")
            else:
                suggestions.append(f"Line {line_num}: Add test covering: {line[:50]}")

    return suggestions
```

---

## 10. Task 3.8: Implement Debugging Planet

### Planet Tool: debug_code

```python
async def debug_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: debug_code

    Systematic debugging workflow.
    Analyzes error, traces cause, suggests fix.

    Parameters:
        code: str - Code with bug
        error: str - Error message or description
        context: str - Additional context (optional)

    Returns:
        success: bool
        error_type: str
        location: dict - Where the error occurs
        diagnosis: str - What's wrong
        suggested_fix: str - How to fix it
        fixed_code: str - Code with fix applied
        xp: dict
    """
    code = params.get("code")
    error = params.get("error")
    context = params.get("context", "")

    if not code or not error:
        return {"success": False, "error": "Missing code or error"}

    # Parse the error
    error_info = parse_error_message(error)

    # Locate the problem in code
    problem_location = locate_error_in_code(code, error_info)

    # Generate diagnosis using LLM
    system_prompt = """You are an expert debugger.
Analyze the code and error to:
1. Identify exactly what's wrong
2. Explain why it's happening
3. Provide a specific fix

Be precise and actionable."""

    user_prompt = f"""Code:
```python
{code}
```

Error: {error}

{f"Context: {context}" if context else ""}

Diagnose the issue and provide a fix."""

    diagnosis_response = await call_model_directly(qube, system_prompt, user_prompt)

    # Generate fixed code
    fix_prompt = """Based on your diagnosis, output ONLY the corrected code.
No explanations, just the fixed code."""

    fixed_code_response = await call_model_directly(qube, fix_prompt, diagnosis_response)
    fixed_code = extract_code_from_response(fixed_code_response, "python")

    # Verify the fix works
    verification = await execute_code(fixed_code, "python", timeout_ms=5000)

    # Calculate XP
    xp_input = {
        "executed": verification["success"],
        "is_novel": True
    }
    xp_result = calculate_waitress_xp(xp_input)

    await award_xp_to_skill(qube, "debugging", xp_result["total"])

    return {
        "success": True,
        "error_type": error_info.get("type", "unknown"),
        "location": problem_location,
        "diagnosis": diagnosis_response,
        "suggested_fix": extract_fix_from_diagnosis(diagnosis_response),
        "fixed_code": fixed_code,
        "fix_verified": verification["success"],
        "xp": xp_result
    }


def parse_error_message(error: str) -> Dict[str, Any]:
    """Parse error message to extract type, message, location."""
    import re

    result = {
        "type": "unknown",
        "message": error,
        "file": None,
        "line": None,
        "traceback": []
    }

    # Python error patterns
    # TypeError: unsupported operand...
    type_match = re.search(r'^(\w+Error):\s*(.+)$', error, re.MULTILINE)
    if type_match:
        result["type"] = type_match.group(1)
        result["message"] = type_match.group(2)

    # File "foo.py", line 42
    location_match = re.search(r'File "([^"]+)", line (\d+)', error)
    if location_match:
        result["file"] = location_match.group(1)
        result["line"] = int(location_match.group(2))

    # Extract traceback lines
    traceback_lines = re.findall(r'^\s+File "([^"]+)", line (\d+)', error, re.MULTILINE)
    result["traceback"] = [{"file": f, "line": int(l)} for f, l in traceback_lines]

    return result


def locate_error_in_code(code: str, error_info: Dict[str, Any]) -> Dict[str, Any]:
    """Locate where in the code the error occurs."""
    location = {
        "line": error_info.get("line"),
        "column": None,
        "context_lines": []
    }

    if location["line"]:
        lines = code.split('\n')
        line_idx = location["line"] - 1

        # Get surrounding context
        start = max(0, line_idx - 2)
        end = min(len(lines), line_idx + 3)
        location["context_lines"] = [
            {"num": i + 1, "text": lines[i], "is_error": i == line_idx}
            for i in range(start, end)
        ]

    return location


def extract_fix_from_diagnosis(diagnosis: str) -> str:
    """Extract the fix suggestion from diagnosis text."""
    import re

    # Look for "fix:", "solution:", "change X to Y" patterns
    patterns = [
        r'fix[:\s]+(.+?)(?:\n\n|\Z)',
        r'solution[:\s]+(.+?)(?:\n\n|\Z)',
        r'change\s+(.+?)\s+to\s+(.+?)(?:\n|\Z)',
    ]

    for pattern in patterns:
        match = re.search(pattern, diagnosis, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(0).strip()

    # Fallback: return last paragraph
    paragraphs = diagnosis.strip().split('\n\n')
    return paragraphs[-1] if paragraphs else ""
```

### Moon Tool: analyze_error

```python
async def analyze_error(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: analyze_error

    Parse and explain error messages.
    Makes cryptic errors human-readable.

    Parameters:
        error: str - Error message/stack trace

    Returns:
        success: bool
        error_type: str
        error_message: str
        file: str | None
        line: int | None
        explanation: str - Human-readable explanation
        common_causes: list
        search_terms: list - Terms to search for help
        xp: dict
    """
    error = params.get("error")

    if not error:
        return {"success": False, "error": "Missing error parameter"}

    # Parse error structure
    parsed = parse_error_message(error)

    # Look up common causes
    common_causes = get_common_error_causes(parsed["type"])

    # Generate explanation using LLM
    system_prompt = """You are an expert at explaining error messages.
Given an error, explain:
1. What it means in plain English
2. Why it typically occurs
3. How to fix it

Be concise and helpful."""

    explanation = await call_model_directly(
        qube,
        system_prompt,
        f"Explain this error:\n{error}"
    )

    # Generate search terms
    search_terms = generate_search_terms(parsed)

    # Calculate XP
    xp_result = calculate_waitress_xp({"executed": True, "is_novel": True})
    await award_xp_to_skill(qube, "error_analysis", xp_result["total"])

    return {
        "success": True,
        "error_type": parsed["type"],
        "error_message": parsed["message"],
        "file": parsed.get("file"),
        "line": parsed.get("line"),
        "explanation": explanation,
        "common_causes": common_causes,
        "search_terms": search_terms,
        "xp": xp_result
    }


def get_common_error_causes(error_type: str) -> List[str]:
    """Get common causes for an error type."""
    causes = {
        "TypeError": [
            "Passing wrong type to function",
            "Calling method on None",
            "Mixing incompatible types in operation"
        ],
        "ValueError": [
            "Invalid value for function parameter",
            "Unpacking wrong number of values",
            "Converting invalid string to number"
        ],
        "KeyError": [
            "Accessing dict key that doesn't exist",
            "Typo in key name",
            "Key not set before access"
        ],
        "IndexError": [
            "List index out of range",
            "Empty list access",
            "Off-by-one error"
        ],
        "AttributeError": [
            "Calling method that doesn't exist",
            "Accessing attribute on None",
            "Typo in attribute name"
        ],
        "NameError": [
            "Variable not defined",
            "Typo in variable name",
            "Variable used before assignment"
        ],
        "SyntaxError": [
            "Missing colon after if/for/def",
            "Unclosed parenthesis/bracket",
            "Invalid indentation"
        ],
        "ImportError": [
            "Module not installed",
            "Typo in module name",
            "Circular import"
        ]
    }
    return causes.get(error_type, ["Unknown error type"])


def generate_search_terms(parsed: Dict[str, Any]) -> List[str]:
    """Generate search terms to find help for error."""
    terms = []

    if parsed["type"] != "unknown":
        terms.append(f"python {parsed['type']}")

    # Extract key parts of error message
    message = parsed["message"]
    if "'" in message:
        # Extract quoted terms
        import re
        quoted = re.findall(r"'([^']+)'", message)
        for q in quoted[:2]:
            terms.append(f"python {parsed['type']} {q}")

    terms.append(f"how to fix {parsed['type']} python")

    return terms[:5]
```

### Moon Tool: find_root_cause

```python
async def find_root_cause(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: find_root_cause

    Trace an error back to its root cause.
    Goes beyond symptoms to find the actual problem.

    Parameters:
        code: str - Code with the error
        error: str - Error message
        execution_trace: list - Optional execution trace

    Returns:
        success: bool
        root_cause: dict - The fundamental cause
        trace_path: list - How we got to the error
        explanation: str
        contributing_factors: list
        prevention_tips: list
        xp: dict
    """
    code = params.get("code")
    error = params.get("error")
    execution_trace = params.get("execution_trace", [])

    if not code or not error:
        return {"success": False, "error": "Missing code or error"}

    # Build execution flow analysis
    system_prompt = """You are an expert at root cause analysis.
Given code and an error, trace backwards to find:
1. The ROOT cause (not just the symptom)
2. The chain of events that led to it
3. Contributing factors
4. How to prevent it in the future

Think step by step."""

    user_prompt = f"""Code:
```python
{code}
```

Error: {error}

{f"Execution trace: {execution_trace}" if execution_trace else ""}

Find the root cause."""

    analysis = await call_model_directly(qube, system_prompt, user_prompt)

    # Parse the analysis
    root_cause = extract_root_cause(analysis)
    trace_path = extract_trace_path(analysis)
    contributing_factors = extract_contributing_factors(analysis)
    prevention_tips = extract_prevention_tips(analysis)

    # Calculate XP
    xp_result = calculate_waitress_xp({"executed": True, "is_novel": True})
    await award_xp_to_skill(qube, "root_cause", xp_result["total"])

    return {
        "success": True,
        "root_cause": root_cause,
        "trace_path": trace_path,
        "explanation": analysis,
        "contributing_factors": contributing_factors,
        "prevention_tips": prevention_tips,
        "xp": xp_result
    }


def extract_root_cause(analysis: str) -> Dict[str, Any]:
    """Extract root cause from analysis."""
    import re

    # Look for "root cause:" section
    match = re.search(r'root cause[:\s]+(.+?)(?:\n\n|\n[A-Z]|\Z)', analysis, re.IGNORECASE | re.DOTALL)
    if match:
        return {
            "description": match.group(1).strip(),
            "confidence": 0.8
        }

    # Fallback: first paragraph
    return {
        "description": analysis.split('\n\n')[0],
        "confidence": 0.5
    }


def extract_trace_path(analysis: str) -> List[str]:
    """Extract the trace path from analysis."""
    import re

    # Look for numbered steps
    steps = re.findall(r'\d+\.\s+(.+?)(?:\n|$)', analysis)
    if steps:
        return steps[:5]

    # Look for "then" transitions
    steps = re.split(r'\s+then\s+', analysis, flags=re.IGNORECASE)
    if len(steps) > 1:
        return [s.strip()[:100] for s in steps[:5]]

    return []


def extract_contributing_factors(analysis: str) -> List[str]:
    """Extract contributing factors from analysis."""
    import re

    # Look for "contributing" or "factors" section
    match = re.search(r'contributing.+?:\s*(.+?)(?:\n\n|\Z)', analysis, re.IGNORECASE | re.DOTALL)
    if match:
        factors = re.findall(r'[-•]\s*(.+?)(?:\n|$)', match.group(1))
        if factors:
            return factors[:5]

    return []


def extract_prevention_tips(analysis: str) -> List[str]:
    """Extract prevention tips from analysis."""
    import re

    # Look for "prevent" or "avoid" section
    match = re.search(r'prevent.+?:\s*(.+?)(?:\n\n|\Z)', analysis, re.IGNORECASE | re.DOTALL)
    if match:
        tips = re.findall(r'[-•]\s*(.+?)(?:\n|$)', match.group(1))
        if tips:
            return tips[:5]

    return ["Add input validation", "Write tests for edge cases", "Use type hints"]
```

---

## 11. Task 3.9: Implement Algorithms Planet

### Planet Tool: benchmark_code

```python
async def benchmark_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: benchmark_code

    Benchmark code performance with varying input sizes.
    Measures time and memory usage.

    Parameters:
        code: str - Code to benchmark
        inputs: list - Test inputs of varying sizes (optional)
        iterations: int - Runs per input (default: 3)

    Returns:
        success: bool
        benchmarks: list - Results for each input size
        avg_time_ms: float
        scaling: dict - How performance scales
        estimated_complexity: str - Big O estimate
        xp: dict
    """
    code = params.get("code")
    inputs = params.get("inputs")
    iterations = params.get("iterations", 3)

    if not code:
        return {"success": False, "error": "Missing code"}

    # Generate default inputs if not provided
    if not inputs:
        inputs = generate_benchmark_inputs(code)

    # Run benchmarks
    benchmark_code_str = f'''
import time
import sys

# The code to benchmark
{code}

# Benchmark function (assumes main function exists)
inputs = {inputs}
results = []

for input_data in inputs:
    times = []
    for _ in range({iterations}):
        start = time.perf_counter()
        try:
            # Call the main function
            result = main(input_data) if callable(main) else eval(input_data)
            success = True
        except Exception as e:
            success = False
        end = time.perf_counter()
        times.append((end - start) * 1000)

    results.append({{
        "input_size": len(str(input_data)) if input_data else 0,
        "avg_time_ms": sum(times) / len(times),
        "min_time_ms": min(times),
        "max_time_ms": max(times),
        "success": success
    }})

import json
print("BENCHMARK_RESULTS:" + json.dumps(results))
'''

    result = await execute_code(benchmark_code_str, "python", timeout_ms=60000)

    # Parse results
    benchmarks = []
    import re
    import json
    match = re.search(r'BENCHMARK_RESULTS:(.+?)$', result["output"], re.MULTILINE)
    if match:
        try:
            benchmarks = json.loads(match.group(1))
        except:
            pass

    # Analyze scaling
    scaling = analyze_scaling(benchmarks)
    complexity = estimate_complexity(benchmarks)

    # Calculate XP
    xp_input = {
        "executed": result["success"],
        "performance": {"within_threshold": scaling.get("is_efficient", True)},
        "is_novel": True
    }
    xp_result = calculate_waitress_xp(xp_input)

    await award_xp_to_skill(qube, "algorithms", xp_result["total"])

    return {
        "success": True,
        "benchmarks": benchmarks,
        "avg_time_ms": sum(b["avg_time_ms"] for b in benchmarks) / len(benchmarks) if benchmarks else 0,
        "scaling": scaling,
        "estimated_complexity": complexity,
        "xp": xp_result
    }


def generate_benchmark_inputs(code: str) -> List[Any]:
    """Generate default benchmark inputs based on code."""
    # Default: increasing sizes for common patterns
    return [
        list(range(10)),
        list(range(100)),
        list(range(1000)),
        list(range(5000)),
    ]


def analyze_scaling(benchmarks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze how performance scales with input size."""
    if len(benchmarks) < 2:
        return {"pattern": "insufficient_data", "is_efficient": True}

    # Calculate growth rates
    sizes = [b["input_size"] for b in benchmarks]
    times = [b["avg_time_ms"] for b in benchmarks]

    # Simple ratio analysis
    ratios = []
    for i in range(1, len(times)):
        if times[i-1] > 0:
            ratios.append(times[i] / times[i-1])

    avg_ratio = sum(ratios) / len(ratios) if ratios else 1

    # Determine pattern
    if avg_ratio < 1.5:
        pattern = "constant_or_logarithmic"
        is_efficient = True
    elif avg_ratio < 2.5:
        pattern = "linear"
        is_efficient = True
    elif avg_ratio < 5:
        pattern = "linearithmic"
        is_efficient = True
    elif avg_ratio < 10:
        pattern = "quadratic"
        is_efficient = False
    else:
        pattern = "exponential_or_worse"
        is_efficient = False

    return {
        "pattern": pattern,
        "growth_ratio": avg_ratio,
        "is_efficient": is_efficient
    }


def estimate_complexity(benchmarks: List[Dict[str, Any]]) -> str:
    """Estimate Big O complexity from benchmarks."""
    scaling = analyze_scaling(benchmarks)
    pattern = scaling.get("pattern", "unknown")

    complexity_map = {
        "constant_or_logarithmic": "O(1) or O(log n)",
        "linear": "O(n)",
        "linearithmic": "O(n log n)",
        "quadratic": "O(n²)",
        "exponential_or_worse": "O(2^n) or worse"
    }

    return complexity_map.get(pattern, "Unknown")
```

### Moon Tool: analyze_complexity

```python
async def analyze_complexity(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: analyze_complexity

    Analyze code to determine Big O complexity.
    Static analysis + empirical verification.

    Parameters:
        code: str - Code to analyze

    Returns:
        success: bool
        time_complexity: str - Big O time
        space_complexity: str - Big O space
        loops_found: int
        is_recursive: bool
        explanation: str
        optimization_potential: str
        xp: dict
    """
    code = params.get("code")

    if not code:
        return {"success": False, "error": "Missing code"}

    # Static analysis using LLM
    system_prompt = """You are an expert at algorithm analysis.
Analyze the given code and determine:
1. Time complexity (Big O)
2. Space complexity (Big O)
3. Number of nested loops
4. Whether it uses recursion
5. Explanation of your analysis
6. Potential for optimization

Be precise and use standard Big O notation."""

    analysis = await call_model_directly(
        qube,
        system_prompt,
        f"Analyze this code:\n```python\n{code}\n```"
    )

    # Parse the analysis
    time_complexity = extract_complexity(analysis, "time")
    space_complexity = extract_complexity(analysis, "space")

    # Count loops and check recursion (simple heuristics)
    loops_found = code.count("for ") + code.count("while ")
    is_recursive = bool(re.search(r'def (\w+)\(.*\).*\1\(', code, re.DOTALL))

    # Assess optimization potential
    optimization_potential = assess_optimization_potential(time_complexity)

    # Calculate XP
    xp_result = calculate_waitress_xp({"executed": True, "is_novel": True})
    await award_xp_to_skill(qube, "complexity_analysis", xp_result["total"])

    return {
        "success": True,
        "time_complexity": time_complexity,
        "space_complexity": space_complexity,
        "loops_found": loops_found,
        "is_recursive": is_recursive,
        "explanation": analysis,
        "optimization_potential": optimization_potential,
        "xp": xp_result
    }


def extract_complexity(analysis: str, complexity_type: str) -> str:
    """Extract complexity notation from analysis."""
    import re

    # Look for O(...) notation near the type
    pattern = rf'{complexity_type}[^O]*O\(([^)]+)\)'
    match = re.search(pattern, analysis, re.IGNORECASE)
    if match:
        return f"O({match.group(1)})"

    # Fallback: any O(...) notation
    match = re.search(r'O\(([^)]+)\)', analysis)
    if match:
        return f"O({match.group(1)})"

    return "Unknown"


def assess_optimization_potential(time_complexity: str) -> str:
    """Assess potential for optimization based on complexity."""
    if "n²" in time_complexity or "n^2" in time_complexity:
        return "High - quadratic algorithms can often be improved"
    elif "2^n" in time_complexity or "n!" in time_complexity:
        return "Critical - exponential complexity needs redesign"
    elif "n log n" in time_complexity:
        return "Low - already at optimal comparison-based complexity"
    elif "n" in time_complexity and "log" not in time_complexity:
        return "Medium - linear is good but check for redundant passes"
    elif "log" in time_complexity or "1" in time_complexity:
        return "Minimal - already very efficient"
    else:
        return "Unknown - manual analysis recommended"
```

### Moon Tool: tune_performance

```python
async def tune_performance(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: tune_performance

    Suggest and apply performance optimizations.
    Uses benchmark data if available.

    Parameters:
        code: str - Code to optimize
        benchmark_results: dict - Previous benchmark results (optional)

    Returns:
        success: bool
        original_code: str
        optimized_code: str
        optimizations_applied: list
        expected_improvement: str
        xp: dict
    """
    code = params.get("code")
    benchmarks = params.get("benchmark_results")

    if not code:
        return {"success": False, "error": "Missing code"}

    # Generate optimizations using LLM
    system_prompt = """You are an expert at code optimization.
Given code (and optionally benchmark data), suggest optimizations:

1. Identify bottlenecks
2. Suggest specific optimizations
3. Provide the optimized code

Focus on:
- Algorithm improvements (better Big O)
- Data structure choices
- Eliminating redundant operations
- Caching/memoization where appropriate

Output the optimized code with comments explaining changes."""

    user_prompt = f"""Original code:
```python
{code}
```

{f"Benchmark results: {benchmarks}" if benchmarks else ""}

Optimize this code for better performance."""

    optimized_response = await call_model_directly(qube, system_prompt, user_prompt)
    optimized_code = extract_code_from_response(optimized_response, "python")

    # Extract optimization descriptions
    optimizations = extract_optimizations(optimized_response)

    # Estimate improvement
    expected_improvement = estimate_improvement(optimizations)

    # Calculate XP
    xp_input = {
        "executed": True,
        "is_novel": True,
        "performance": {"within_threshold": True}
    }
    xp_result = calculate_waitress_xp(xp_input)

    await award_xp_to_skill(qube, "performance_tuning", xp_result["total"])

    return {
        "success": True,
        "original_code": code,
        "optimized_code": optimized_code,
        "optimizations_applied": optimizations,
        "expected_improvement": expected_improvement,
        "xp": xp_result
    }


def extract_optimizations(response: str) -> List[str]:
    """Extract optimization descriptions from response."""
    import re

    optimizations = []

    # Look for numbered optimizations
    numbered = re.findall(r'\d+\.\s*\*\*([^*]+)\*\*', response)
    if numbered:
        optimizations.extend(numbered)

    # Look for bullet points
    bullets = re.findall(r'[-•]\s+(.+?)(?:\n|$)', response)
    if bullets:
        optimizations.extend(bullets[:5])

    # Look for "optimization:" or "improvement:" labels
    labeled = re.findall(r'(?:optimization|improvement)[:\s]+(.+?)(?:\n|$)', response, re.IGNORECASE)
    if labeled:
        optimizations.extend(labeled)

    return list(set(optimizations))[:5]  # Dedupe and limit


def estimate_improvement(optimizations: List[str]) -> str:
    """Estimate expected improvement from optimizations."""
    if not optimizations:
        return "No optimizations identified"

    # Check for complexity improvements
    complexity_keywords = ["O(n)", "O(log", "O(1)", "linear", "logarithmic", "constant"]
    has_complexity_improvement = any(
        any(kw in opt.lower() for kw in complexity_keywords)
        for opt in optimizations
    )

    if has_complexity_improvement:
        return "Significant - complexity reduction"

    # Check for caching/memoization
    if any("cache" in opt.lower() or "memo" in opt.lower() for opt in optimizations):
        return "Moderate to significant - caching benefits depend on usage pattern"

    return f"Moderate - {len(optimizations)} optimizations suggested"
```

---

## 12. Task 3.10: Implement Hacking Planet

### Planet Tool: security_scan

```python
async def security_scan(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: security_scan

    Scan code for security vulnerabilities.
    Checks for OWASP Top 10 and common issues.

    Parameters:
        code: str - Code to scan
        scan_type: str - "quick" or "thorough" (default: thorough)
        language: str - Programming language (default: python)

    Returns:
        success: bool
        vulnerabilities_found: int
        critical: list - Critical severity vulnerabilities
        high: list - High severity
        medium: list - Medium severity
        low: list - Low severity
        recommendations: list
        xp: dict
    """
    code = params.get("code")
    scan_type = params.get("scan_type", "thorough")
    language = params.get("language", "python")

    if not code:
        return {"success": False, "error": "Missing code"}

    vulnerabilities = []

    # Static analysis checks
    if language == "python":
        vulnerabilities.extend(check_python_vulnerabilities(code))
    elif language in ["javascript", "typescript"]:
        vulnerabilities.extend(check_javascript_vulnerabilities(code))

    # LLM-based deep scan for thorough mode
    if scan_type == "thorough":
        llm_vulns = await llm_security_scan(qube, code, language)
        vulnerabilities.extend(llm_vulns)

    # Deduplicate
    seen = set()
    unique_vulns = []
    for v in vulnerabilities:
        key = f"{v['type']}:{v.get('line', 0)}"
        if key not in seen:
            seen.add(key)
            unique_vulns.append(v)
    vulnerabilities = unique_vulns

    # Calculate CVSS scores and categorize
    for vuln in vulnerabilities:
        vuln["severity"] = calculate_cvss_score(vuln)

    critical = [v for v in vulnerabilities if v["severity"] >= 9]
    high = [v for v in vulnerabilities if 7 <= v["severity"] < 9]
    medium = [v for v in vulnerabilities if 4 <= v["severity"] < 7]
    low = [v for v in vulnerabilities if v["severity"] < 4]

    # Generate recommendations
    recommendations = generate_security_recommendations(vulnerabilities)

    # Calculate XP - finding vulnerabilities is valuable
    xp_input = {
        "executed": True,
        "vulnerabilities": [],  # Empty = good for the scanned code
        "is_novel": True
    }
    xp_result = calculate_waitress_xp(xp_input)

    await award_xp_to_skill(qube, "hacking", xp_result["total"])

    return {
        "success": True,
        "vulnerabilities_found": len(vulnerabilities),
        "critical": critical,
        "high": high,
        "medium": medium,
        "low": low,
        "all_vulnerabilities": vulnerabilities,
        "recommendations": recommendations,
        "xp": xp_result
    }


def check_python_vulnerabilities(code: str) -> List[Dict[str, Any]]:
    """Check Python code for common vulnerabilities."""
    import re
    vulns = []

    patterns = [
        # Injection vulnerabilities
        {
            "pattern": r'eval\s*\([^)]*\+',
            "type": "code_injection",
            "description": "eval() with string concatenation - potential code injection",
            "cwe": "CWE-94"
        },
        {
            "pattern": r'exec\s*\(',
            "type": "code_injection",
            "description": "exec() usage - potential arbitrary code execution",
            "cwe": "CWE-94"
        },
        {
            "pattern": r'os\.system\s*\([^)]*\+',
            "type": "command_injection",
            "description": "os.system() with string concatenation - command injection risk",
            "cwe": "CWE-78"
        },
        {
            "pattern": r'subprocess\.\w+\s*\([^)]*shell\s*=\s*True',
            "type": "command_injection",
            "description": "subprocess with shell=True - command injection risk",
            "cwe": "CWE-78"
        },
        # SQL Injection
        {
            "pattern": r'execute\s*\(\s*["\'][^"\']*%s',
            "type": "sql_injection",
            "description": "SQL query with string formatting - use parameterized queries",
            "cwe": "CWE-89"
        },
        {
            "pattern": r'execute\s*\([^)]*\+[^)]*\)',
            "type": "sql_injection",
            "description": "SQL query with string concatenation - SQL injection risk",
            "cwe": "CWE-89"
        },
        # Deserialization
        {
            "pattern": r'pickle\.loads?\s*\(',
            "type": "insecure_deserialization",
            "description": "pickle.load() - arbitrary code execution via deserialization",
            "cwe": "CWE-502"
        },
        {
            "pattern": r'yaml\.load\s*\([^)]*\)(?!\s*,\s*Loader)',
            "type": "insecure_deserialization",
            "description": "yaml.load() without safe Loader - use yaml.safe_load()",
            "cwe": "CWE-502"
        },
        # Path traversal
        {
            "pattern": r'open\s*\([^)]*\+',
            "type": "path_traversal",
            "description": "File open with concatenation - potential path traversal",
            "cwe": "CWE-22"
        },
        # Hardcoded secrets
        {
            "pattern": r'(?:password|api_key|secret|token)\s*=\s*["\'][^"\']+["\']',
            "type": "hardcoded_secret",
            "description": "Potential hardcoded secret or credential",
            "cwe": "CWE-798"
        },
        # Weak crypto
        {
            "pattern": r'hashlib\.md5\s*\(',
            "type": "weak_crypto",
            "description": "MD5 is cryptographically weak - use SHA-256 or better",
            "cwe": "CWE-328"
        },
        {
            "pattern": r'hashlib\.sha1\s*\(',
            "type": "weak_crypto",
            "description": "SHA1 is deprecated - use SHA-256 or better",
            "cwe": "CWE-328"
        },
    ]

    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        for p in patterns:
            if re.search(p["pattern"], line, re.IGNORECASE):
                vulns.append({
                    "type": p["type"],
                    "description": p["description"],
                    "cwe": p["cwe"],
                    "line": i,
                    "code": line.strip()[:100]
                })

    return vulns


def check_javascript_vulnerabilities(code: str) -> List[Dict[str, Any]]:
    """Check JavaScript code for common vulnerabilities."""
    import re
    vulns = []

    patterns = [
        # XSS
        {
            "pattern": r'innerHTML\s*=',
            "type": "xss",
            "description": "Direct innerHTML assignment - potential XSS",
            "cwe": "CWE-79"
        },
        {
            "pattern": r'document\.write\s*\(',
            "type": "xss",
            "description": "document.write() - potential XSS",
            "cwe": "CWE-79"
        },
        {
            "pattern": r'\.html\s*\([^)]*\$',
            "type": "xss",
            "description": "jQuery .html() with variable - potential XSS",
            "cwe": "CWE-79"
        },
        # Code injection
        {
            "pattern": r'eval\s*\(',
            "type": "code_injection",
            "description": "eval() usage - potential code injection",
            "cwe": "CWE-94"
        },
        {
            "pattern": r'new\s+Function\s*\(',
            "type": "code_injection",
            "description": "new Function() - dynamic code execution",
            "cwe": "CWE-94"
        },
        # Prototype pollution
        {
            "pattern": r'\[.*\]\s*=.*__proto__',
            "type": "prototype_pollution",
            "description": "Potential prototype pollution vulnerability",
            "cwe": "CWE-1321"
        },
    ]

    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        for p in patterns:
            if re.search(p["pattern"], line, re.IGNORECASE):
                vulns.append({
                    "type": p["type"],
                    "description": p["description"],
                    "cwe": p["cwe"],
                    "line": i,
                    "code": line.strip()[:100]
                })

    return vulns


async def llm_security_scan(qube, code: str, language: str) -> List[Dict[str, Any]]:
    """Use LLM for deeper security analysis."""
    system_prompt = """You are a security expert performing code review.
Analyze the code for security vulnerabilities including:
- OWASP Top 10 issues
- Language-specific security pitfalls
- Business logic flaws
- Authentication/authorization issues
- Data exposure risks

For each vulnerability found, provide:
1. Type (e.g., SQL Injection, XSS)
2. CWE ID if applicable
3. Line number(s)
4. Description
5. Severity (1-10)

Output as JSON array."""

    response = await call_model_directly(
        qube,
        system_prompt,
        f"```{language}\n{code}\n```"
    )

    # Parse JSON from response
    import re
    import json

    try:
        # Find JSON array in response
        match = re.search(r'\[[\s\S]*\]', response)
        if match:
            vulns = json.loads(match.group(0))
            return vulns
    except:
        pass

    return []


def calculate_cvss_score(vuln: Dict[str, Any]) -> float:
    """Calculate simplified CVSS score for vulnerability."""
    base_scores = {
        "code_injection": 9.8,
        "command_injection": 9.8,
        "sql_injection": 9.1,
        "xss": 6.1,
        "insecure_deserialization": 8.1,
        "path_traversal": 7.5,
        "hardcoded_secret": 7.5,
        "weak_crypto": 5.3,
        "prototype_pollution": 6.1,
    }
    return base_scores.get(vuln.get("type", ""), 5.0)


def generate_security_recommendations(vulnerabilities: List[Dict[str, Any]]) -> List[str]:
    """Generate security recommendations based on found vulnerabilities."""
    recommendations = []
    seen_types = set()

    for vuln in vulnerabilities:
        vtype = vuln.get("type")
        if vtype in seen_types:
            continue
        seen_types.add(vtype)

        recs = {
            "code_injection": "Never use eval() or exec() with untrusted input. Use ast.literal_eval() for safe evaluation of literals.",
            "command_injection": "Use subprocess with shell=False and pass arguments as a list. Never concatenate user input into commands.",
            "sql_injection": "Always use parameterized queries or an ORM. Never concatenate user input into SQL.",
            "xss": "Sanitize all user input before rendering. Use framework escaping functions.",
            "insecure_deserialization": "Never deserialize untrusted data. Use JSON instead of pickle.",
            "path_traversal": "Validate and sanitize file paths. Use os.path.abspath() and check against allowed directories.",
            "hardcoded_secret": "Store secrets in environment variables or a secure vault. Never commit secrets to code.",
            "weak_crypto": "Use modern cryptographic algorithms: SHA-256+, AES-256, RSA-2048+.",
            "prototype_pollution": "Freeze prototypes or use Object.create(null) for dictionaries."
        }

        if vtype in recs:
            recommendations.append(recs[vtype])

    return recommendations
```

### Moon Tool: find_exploit

```python
async def find_exploit(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: find_exploit

    Find specific exploits and generate proof of concept.
    For authorized security testing only.

    Parameters:
        code: str - Code to analyze
        vuln_type: str - Type of vulnerability to look for (optional)

    Returns:
        success: bool
        exploits_found: int
        exploits: list - Each with vulnerability, PoC, impact, remediation
        disclaimer: str
        xp: dict
    """
    code = params.get("code")
    vuln_type = params.get("vuln_type")

    if not code:
        return {"success": False, "error": "Missing code"}

    # Find vulnerabilities
    if vuln_type:
        vulnerabilities = find_specific_vulnerabilities(code, vuln_type)
    else:
        vulnerabilities = check_python_vulnerabilities(code)

    exploits = []
    for vuln in vulnerabilities[:5]:  # Limit to 5 exploits
        poc = await generate_proof_of_concept(qube, code, vuln)
        exploits.append({
            "vulnerability": vuln,
            "proof_of_concept": poc,
            "impact": assess_exploit_impact(vuln),
            "remediation": generate_remediation(vuln)
        })

    # Calculate XP
    xp_result = calculate_waitress_xp({"executed": True, "is_novel": True})
    await award_xp_to_skill(qube, "exploits", xp_result["total"])

    return {
        "success": True,
        "exploits_found": len(exploits),
        "exploits": exploits,
        "disclaimer": "For authorized security testing only. Do not use against systems without permission.",
        "xp": xp_result
    }


def find_specific_vulnerabilities(code: str, vuln_type: str) -> List[Dict[str, Any]]:
    """Find vulnerabilities of a specific type."""
    all_vulns = check_python_vulnerabilities(code)
    return [v for v in all_vulns if v["type"] == vuln_type]


async def generate_proof_of_concept(qube, code: str, vuln: Dict[str, Any]) -> str:
    """Generate a safe proof of concept for the vulnerability."""
    system_prompt = """You are a security researcher creating educational PoCs.
Generate a SAFE proof of concept that demonstrates the vulnerability.
The PoC should:
1. Show how the vulnerability could be exploited
2. Be non-destructive (no actual damage)
3. Include comments explaining each step
4. Be educational in nature

Keep it simple and clear."""

    user_prompt = f"""Vulnerability: {vuln['type']}
Description: {vuln['description']}
Affected line: {vuln.get('line', 'unknown')}
Code context: {vuln.get('code', '')}

Generate a safe PoC demonstrating this vulnerability."""

    return await call_model_directly(qube, system_prompt, user_prompt)


def assess_exploit_impact(vuln: Dict[str, Any]) -> str:
    """Assess the potential impact of exploiting a vulnerability."""
    impacts = {
        "code_injection": "Critical - Full code execution, complete system compromise possible",
        "command_injection": "Critical - Shell access, data theft, system takeover",
        "sql_injection": "High - Data breach, authentication bypass, data manipulation",
        "xss": "Medium - Session hijacking, defacement, phishing",
        "insecure_deserialization": "High - Remote code execution possible",
        "path_traversal": "Medium - Unauthorized file access, information disclosure",
        "hardcoded_secret": "High - Credential theft, unauthorized access",
        "weak_crypto": "Medium - Data decryption possible with sufficient resources"
    }
    return impacts.get(vuln.get("type", ""), "Unknown impact")


def generate_remediation(vuln: Dict[str, Any]) -> str:
    """Generate remediation advice for a vulnerability."""
    remediations = {
        "code_injection": "Replace eval/exec with safe alternatives. Use ast.literal_eval() for literals.",
        "command_injection": "Use subprocess with list arguments and shell=False. Validate all inputs.",
        "sql_injection": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))",
        "xss": "Escape output using framework functions. Use Content-Security-Policy headers.",
        "insecure_deserialization": "Use JSON instead of pickle. If pickle required, verify data source.",
        "path_traversal": "Validate paths with os.path.realpath() and ensure within allowed directory.",
        "hardcoded_secret": "Move to environment variables: os.environ.get('API_KEY')",
        "weak_crypto": "Replace MD5/SHA1 with hashlib.sha256() or bcrypt for passwords."
    }
    return remediations.get(vuln.get("type", ""), "Review and fix the vulnerability")
```

### Moon Tool: reverse_engineer

```python
async def reverse_engineer(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: reverse_engineer

    Analyze and deobfuscate code or understand unknown systems.

    Parameters:
        target: str - Code to analyze (minified, obfuscated, etc.)
        target_type: str - Type hint (optional: minified_js, obfuscated, binary_hex)

    Returns:
        success: bool
        target_type: str
        deobfuscated: str | None
        structure: dict
        functions_found: list
        strings_found: list
        control_flow: str
        insights: list
        xp: dict
    """
    target = params.get("target")
    target_type = params.get("target_type")

    if not target:
        return {"success": False, "error": "Missing target"}

    # Auto-detect target type if not specified
    if not target_type:
        target_type = detect_target_type(target)

    result = {
        "target_type": target_type,
        "deobfuscated": None,
        "structure": {},
        "functions_found": [],
        "strings_found": [],
        "control_flow": "",
        "insights": []
    }

    if target_type == "minified_js":
        result.update(await analyze_minified_js(qube, target))
    elif target_type == "obfuscated":
        result.update(await analyze_obfuscated(qube, target))
    elif target_type == "binary_hex":
        result.update(await analyze_binary_hex(qube, target))
    else:
        result.update(await analyze_generic_code(qube, target))

    # Calculate XP
    xp_result = calculate_waitress_xp({"executed": True, "is_novel": True})
    await award_xp_to_skill(qube, "reverse_engineering", xp_result["total"])

    return {
        "success": True,
        **result,
        "xp": xp_result
    }


def detect_target_type(target: str) -> str:
    """Detect the type of target code."""
    # Check for minified JS patterns
    if len(target.split('\n')) < 5 and len(target) > 500:
        if any(c in target for c in ['function', 'var ', 'const ', '=>']):
            return "minified_js"

    # Check for common obfuscation patterns
    if target.count('\\x') > 10 or target.count('\\u') > 10:
        return "obfuscated"

    # Check for hex dump (binary)
    import re
    if re.match(r'^[0-9a-fA-F\s]+$', target[:100]):
        return "binary_hex"

    return "unknown"


async def analyze_minified_js(qube, target: str) -> Dict[str, Any]:
    """Analyze and beautify minified JavaScript."""
    import re

    # Basic beautification
    beautified = target
    # Add newlines after semicolons and braces
    beautified = re.sub(r';', ';\n', beautified)
    beautified = re.sub(r'\{', '{\n', beautified)
    beautified = re.sub(r'\}', '\n}\n', beautified)

    # Use LLM for deeper analysis
    system_prompt = """You are an expert at reverse engineering JavaScript.
Analyze this minified code and:
1. Identify all functions and their purposes
2. Extract significant strings
3. Describe the control flow
4. Provide insights about what the code does

Be thorough but concise."""

    analysis = await call_model_directly(qube, system_prompt, f"```javascript\n{target[:5000]}\n```")

    # Extract strings
    strings = re.findall(r'"([^"]+)"', target) + re.findall(r"'([^']+)'", target)
    strings = list(set(s for s in strings if len(s) > 3))[:20]

    return {
        "deobfuscated": beautified,
        "strings_found": strings,
        "insights": [analysis],
        "control_flow": "See insights for detailed analysis"
    }


async def analyze_obfuscated(qube, target: str) -> Dict[str, Any]:
    """Analyze and deobfuscate code."""
    import re

    # Decode common obfuscation
    deobfuscated = target

    # Decode hex escapes
    def hex_decode(match):
        return chr(int(match.group(1), 16))
    deobfuscated = re.sub(r'\\x([0-9a-fA-F]{2})', hex_decode, deobfuscated)

    # Decode unicode escapes
    def unicode_decode(match):
        return chr(int(match.group(1), 16))
    deobfuscated = re.sub(r'\\u([0-9a-fA-F]{4})', unicode_decode, deobfuscated)

    # Use LLM for analysis
    system_prompt = """Analyze this deobfuscated code and explain:
1. What it does
2. Any suspicious or malicious behavior
3. Key functions and their purposes"""

    analysis = await call_model_directly(qube, system_prompt, deobfuscated[:5000])

    return {
        "deobfuscated": deobfuscated,
        "insights": [analysis]
    }


async def analyze_binary_hex(qube, target: str) -> Dict[str, Any]:
    """Analyze hex dump of binary data."""
    import re

    # Clean hex string
    hex_clean = re.sub(r'[^0-9a-fA-F]', '', target)

    # Convert to bytes and extract strings
    try:
        data = bytes.fromhex(hex_clean)
        # Extract printable strings
        strings = re.findall(rb'[\x20-\x7e]{4,}', data)
        strings = [s.decode('ascii', errors='ignore') for s in strings]
    except:
        strings = []

    return {
        "strings_found": strings[:30],
        "structure": {
            "size_bytes": len(hex_clean) // 2,
            "printable_strings": len(strings)
        },
        "insights": ["Binary data analyzed", f"Found {len(strings)} printable strings"]
    }


async def analyze_generic_code(qube, target: str) -> Dict[str, Any]:
    """Generic code analysis."""
    system_prompt = """Analyze this code and provide:
1. Language identification
2. Main purpose/functionality
3. Key functions and their roles
4. Any notable patterns or concerns"""

    analysis = await call_model_directly(qube, system_prompt, target[:5000])

    return {
        "insights": [analysis]
    }
```

### Moon Tool: pen_test

```python
async def pen_test(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: pen_test

    Conduct a systematic penetration test.
    Follows industry-standard methodology.

    Parameters:
        target: str - Target code, endpoint, or system description
        scope: str - "full" or "limited" (default: limited)

    Returns:
        success: bool
        target: str
        scope: str
        findings: list - Results from each phase
        vulnerabilities_found: int
        risk_rating: str
        report: str
        disclaimer: str
        xp: dict
    """
    target = params.get("target")
    scope = params.get("scope", "limited")

    if not target:
        return {"success": False, "error": "Missing target"}

    findings = []

    # Phase 1: Reconnaissance
    recon_result = await perform_reconnaissance(qube, target)
    findings.append({"phase": "reconnaissance", "data": recon_result})

    # Phase 2: Vulnerability Assessment
    vuln_result = await assess_vulnerabilities_pentest(qube, target, recon_result)
    findings.append({"phase": "vulnerability_assessment", "data": vuln_result})

    # Phase 3: Exploitation Analysis (simulated)
    if scope == "full":
        exploit_result = await analyze_exploitation(qube, vuln_result)
        findings.append({"phase": "exploitation_analysis", "data": exploit_result})

    # Calculate overall risk
    vuln_count = len(vuln_result.get("vulnerabilities", []))
    risk_rating = calculate_risk_rating(vuln_result)

    # Generate report
    report = generate_pentest_report(target, scope, findings, risk_rating)

    # Calculate XP
    xp_result = calculate_waitress_xp({"executed": True, "is_novel": True})
    await award_xp_to_skill(qube, "penetration_testing", xp_result["total"])

    return {
        "success": True,
        "target": target[:100],
        "scope": scope,
        "findings": findings,
        "vulnerabilities_found": vuln_count,
        "risk_rating": risk_rating,
        "report": report,
        "disclaimer": "For authorized security testing only",
        "xp": xp_result
    }


async def perform_reconnaissance(qube, target: str) -> Dict[str, Any]:
    """Phase 1: Gather information about the target."""
    system_prompt = """You are conducting reconnaissance for a penetration test.
Analyze the target and identify:
1. Attack surface (entry points)
2. Technologies used
3. Potential weak points
4. Information that could aid exploitation

Be systematic and thorough."""

    analysis = await call_model_directly(qube, system_prompt, f"Target:\n{target}")

    return {
        "analysis": analysis,
        "attack_surface": extract_attack_surface(analysis),
        "technologies": extract_technologies(analysis)
    }


async def assess_vulnerabilities_pentest(qube, target: str, recon: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 2: Systematic vulnerability assessment."""
    # Combine with security scan
    if "```" in target:  # Looks like code
        import re
        code_match = re.search(r'```\w*\n(.*?)```', target, re.DOTALL)
        if code_match:
            code = code_match.group(1)
            vulns = check_python_vulnerabilities(code)
            return {"vulnerabilities": vulns}

    # LLM-based assessment for non-code targets
    system_prompt = """Assess vulnerabilities based on recon data.
For each vulnerability:
1. Name and description
2. Severity (Critical/High/Medium/Low)
3. Evidence from recon
4. Potential impact"""

    analysis = await call_model_directly(
        qube,
        system_prompt,
        f"Recon findings:\n{recon['analysis']}"
    )

    return {
        "analysis": analysis,
        "vulnerabilities": []  # Would parse from analysis
    }


async def analyze_exploitation(qube, vuln_result: Dict[str, Any]) -> Dict[str, Any]:
    """Phase 3: Analyze exploitation potential (no actual exploitation)."""
    system_prompt = """Analyze exploitation potential for found vulnerabilities.
For each:
1. Exploitability (Easy/Medium/Hard)
2. Required conditions
3. Potential impact if exploited
4. Detection likelihood

This is for defensive planning only."""

    analysis = await call_model_directly(
        qube,
        system_prompt,
        f"Vulnerabilities:\n{vuln_result.get('analysis', str(vuln_result.get('vulnerabilities', [])))}"
    )

    return {"analysis": analysis}


def extract_attack_surface(analysis: str) -> List[str]:
    """Extract attack surface from analysis."""
    import re
    surfaces = re.findall(r'(?:entry point|attack surface|endpoint)[:\s]+([^\n.]+)', analysis, re.IGNORECASE)
    return surfaces[:10]


def extract_technologies(analysis: str) -> List[str]:
    """Extract technologies from analysis."""
    import re
    techs = re.findall(r'(?:using|technology|framework|library)[:\s]+([^\n,]+)', analysis, re.IGNORECASE)
    return list(set(techs))[:10]


def calculate_risk_rating(vuln_result: Dict[str, Any]) -> str:
    """Calculate overall risk rating."""
    vulns = vuln_result.get("vulnerabilities", [])
    if not vulns:
        return "Low"

    severities = [v.get("severity", 5) for v in vulns]
    max_sev = max(severities) if severities else 0

    if max_sev >= 9:
        return "Critical"
    elif max_sev >= 7:
        return "High"
    elif max_sev >= 4:
        return "Medium"
    else:
        return "Low"


def generate_pentest_report(target: str, scope: str, findings: list, risk_rating: str) -> str:
    """Generate a penetration test report."""
    report = f"""# Penetration Test Report

## Executive Summary
- **Target:** {target[:50]}...
- **Scope:** {scope}
- **Overall Risk Rating:** {risk_rating}

## Findings by Phase
"""

    for finding in findings:
        report += f"\n### {finding['phase'].replace('_', ' ').title()}\n"
        if isinstance(finding['data'], dict):
            if 'analysis' in finding['data']:
                report += finding['data']['analysis'][:500] + "\n"
            if 'vulnerabilities' in finding['data']:
                report += f"\nVulnerabilities found: {len(finding['data']['vulnerabilities'])}\n"

    report += """
## Recommendations
1. Address all Critical and High severity findings immediately
2. Implement security testing in CI/CD pipeline
3. Conduct regular security assessments
4. Train developers on secure coding practices

## Disclaimer
This assessment was conducted for authorized security testing purposes only.
"""

    return report
```

---

## 13. Task 3.11: Implement Code Review Planet

### Planet Tool: review_code

```python
async def review_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: review_code

    Comprehensive code review.
    Checks style, logic, performance, and security.

    Parameters:
        code: str - Code to review
        review_focus: str - "all", "style", "logic", "performance", "security" (default: all)
        language: str - Programming language (default: python)

    Returns:
        success: bool
        total_comments: int
        comments: list - All review comments
        by_severity: dict - Comments grouped by severity
        summary: str
        approval_status: str - "approved" or "changes_requested"
        xp: dict
    """
    code = params.get("code")
    focus = params.get("review_focus", "all")
    language = params.get("language", "python")

    if not code:
        return {"success": False, "error": "Missing code"}

    comments = []

    # Style review
    if focus in ["all", "style"]:
        style_issues = check_code_style(code, language)
        comments.extend([{"type": "style", "severity": "info", **s} for s in style_issues])

    # Logic review (LLM-based)
    if focus in ["all", "logic"]:
        logic_issues = await review_code_logic(qube, code, language)
        comments.extend([{"type": "logic", **l} for l in logic_issues])

    # Performance review
    if focus in ["all", "performance"]:
        perf_issues = check_performance_issues(code, language)
        comments.extend([{"type": "performance", "severity": "warning", **p} for p in perf_issues])

    # Security review
    if focus in ["all", "security"]:
        security_issues = check_python_vulnerabilities(code) if language == "python" else []
        comments.extend([{"type": "security", "severity": "error", **s} for s in security_issues])

    # Group by severity
    by_severity = {
        "error": [c for c in comments if c.get("severity") == "error"],
        "warning": [c for c in comments if c.get("severity") == "warning"],
        "info": [c for c in comments if c.get("severity") == "info"]
    }

    # Generate summary
    summary = generate_review_summary(comments)

    # Determine approval status
    has_blockers = len(by_severity["error"]) > 0
    approval_status = "changes_requested" if has_blockers else "approved"

    # Calculate XP
    xp_result = calculate_waitress_xp({"executed": True, "is_novel": True})
    await award_xp_to_skill(qube, "code_review", xp_result["total"])

    return {
        "success": True,
        "total_comments": len(comments),
        "comments": comments,
        "by_severity": by_severity,
        "summary": summary,
        "approval_status": approval_status,
        "xp": xp_result
    }


def check_code_style(code: str, language: str) -> List[Dict[str, Any]]:
    """Check code style issues."""
    issues = []
    lines = code.split('\n')

    for i, line in enumerate(lines, 1):
        # Line length
        if len(line) > 100:
            issues.append({
                "line": i,
                "description": f"Line exceeds 100 characters ({len(line)} chars)",
                "suggestion": "Break into multiple lines"
            })

        # Trailing whitespace
        if line.rstrip() != line:
            issues.append({
                "line": i,
                "description": "Trailing whitespace",
                "suggestion": "Remove trailing spaces"
            })

        # Python-specific
        if language == "python":
            # Check indentation (should be 4 spaces)
            stripped = line.lstrip()
            if stripped and line != stripped:
                indent = len(line) - len(stripped)
                if indent % 4 != 0 and '\t' not in line:
                    issues.append({
                        "line": i,
                        "description": f"Inconsistent indentation ({indent} spaces)",
                        "suggestion": "Use 4 spaces per indentation level"
                    })

    return issues


async def review_code_logic(qube, code: str, language: str) -> List[Dict[str, Any]]:
    """Use LLM to review code logic."""
    system_prompt = """You are an expert code reviewer.
Review the code for logic issues:
1. Bugs or potential bugs
2. Edge cases not handled
3. Error handling gaps
4. Unclear or confusing logic

For each issue provide:
- Line number (approximate)
- Description
- Severity (error, warning, info)
- Suggestion

Output as JSON array."""

    response = await call_model_directly(qube, system_prompt, f"```{language}\n{code}\n```")

    # Parse JSON
    import re
    import json

    try:
        match = re.search(r'\[[\s\S]*\]', response)
        if match:
            return json.loads(match.group(0))
    except:
        pass

    return []


def check_performance_issues(code: str, language: str) -> List[Dict[str, Any]]:
    """Check for common performance issues."""
    import re
    issues = []

    if language == "python":
        patterns = [
            {
                "pattern": r'for.*in.*range\(len\(',
                "description": "Using range(len(x)) instead of enumerate()",
                "suggestion": "Use enumerate(x) for index and value"
            },
            {
                "pattern": r'\+\s*=\s*["\']',
                "description": "String concatenation in loop (potential O(n²))",
                "suggestion": "Use list and join() or io.StringIO"
            },
            {
                "pattern": r'if\s+\w+\s+in\s+\[',
                "description": "Membership test on list literal",
                "suggestion": "Use a set for O(1) lookup: if x in {a, b, c}"
            },
            {
                "pattern": r'\.append\([^)]+\)\s*$.*\.append\(',
                "description": "Multiple appends could use extend()",
                "suggestion": "Consider using extend() with a list"
            }
        ]

        for p in patterns:
            if re.search(p["pattern"], code, re.MULTILINE | re.DOTALL):
                issues.append({
                    "description": p["description"],
                    "suggestion": p["suggestion"]
                })

    return issues


def generate_review_summary(comments: List[Dict[str, Any]]) -> str:
    """Generate a summary of the code review."""
    total = len(comments)
    by_type = {}
    for c in comments:
        t = c.get("type", "other")
        by_type[t] = by_type.get(t, 0) + 1

    errors = sum(1 for c in comments if c.get("severity") == "error")
    warnings = sum(1 for c in comments if c.get("severity") == "warning")

    summary = f"Found {total} issues: {errors} errors, {warnings} warnings. "

    if by_type:
        breakdown = ", ".join(f"{v} {k}" for k, v in by_type.items())
        summary += f"Breakdown: {breakdown}."

    if errors > 0:
        summary += " Please address all errors before merging."
    elif warnings > 3:
        summary += " Consider addressing warnings to improve code quality."
    else:
        summary += " Code looks good overall."

    return summary
```

### Moon Tool: refactor_code

```python
async def refactor_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: refactor_code

    Refactor code to improve structure without changing behavior.

    Parameters:
        code: str - Code to refactor
        refactor_type: str - Type of refactoring (auto, extract_method, rename, inline, simplify)
        selection: str - Code selection for extract_method (optional)
        old_name: str - For rename refactoring (optional)
        new_name: str - For rename refactoring (optional)

    Returns:
        success: bool
        original_code: str
        refactored_code: str
        refactor_type: str
        changes: str - Diff-like description of changes
        explanation: str
        xp: dict
    """
    code = params.get("code")
    refactor_type = params.get("refactor_type", "auto")

    if not code:
        return {"success": False, "error": "Missing code"}

    # Auto-detect best refactoring if not specified
    if refactor_type == "auto":
        opportunities = detect_refactoring_opportunities(code)
        if opportunities:
            refactor_type = opportunities[0]["type"]
            params.update(opportunities[0].get("params", {}))
        else:
            return {
                "success": True,
                "message": "No refactoring needed - code looks good",
                "refactored_code": code
            }

    # Apply refactoring
    if refactor_type == "extract_method":
        refactored = await extract_method_refactor(qube, code, params.get("selection"))
    elif refactor_type == "rename":
        refactored = rename_symbol(code, params.get("old_name"), params.get("new_name"))
    elif refactor_type == "inline":
        refactored = await inline_variable(qube, code, params.get("variable"))
    elif refactor_type == "simplify":
        refactored = await simplify_code(qube, code)
    else:
        refactored = await ai_refactor(qube, code, refactor_type)

    # Generate change description
    changes = describe_changes(code, refactored)

    # Calculate XP
    xp_result = calculate_waitress_xp({"executed": True, "is_novel": True})
    await award_xp_to_skill(qube, "refactoring", xp_result["total"])

    return {
        "success": True,
        "original_code": code,
        "refactored_code": refactored,
        "refactor_type": refactor_type,
        "changes": changes,
        "explanation": explain_refactoring(refactor_type),
        "xp": xp_result
    }


def detect_refactoring_opportunities(code: str) -> List[Dict[str, Any]]:
    """Detect opportunities for refactoring."""
    opportunities = []
    import re

    # Long methods
    functions = re.findall(r'def (\w+)\([^)]*\):[^def]*', code, re.DOTALL)
    for func in functions:
        func_code = re.search(rf'def {func}\([^)]*\):(.*?)(?=\ndef |\Z)', code, re.DOTALL)
        if func_code and func_code.group(1).count('\n') > 20:
            opportunities.append({
                "type": "extract_method",
                "reason": f"Function {func} is too long (>20 lines)",
                "params": {}
            })

    # Deeply nested code
    if code.count('        ') > 5:  # 8+ spaces = 2+ levels
        opportunities.append({
            "type": "simplify",
            "reason": "Deeply nested code detected"
        })

    # Duplicate code (simple check)
    lines = code.split('\n')
    seen = {}
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 20:
            if stripped in seen:
                opportunities.append({
                    "type": "extract_method",
                    "reason": f"Duplicate code: {stripped[:30]}..."
                })
                break
            seen[stripped] = True

    return opportunities


async def extract_method_refactor(qube, code: str, selection: str = None) -> str:
    """Extract a method from code."""
    system_prompt = """Refactor this code by extracting a method.
Identify a good candidate for extraction (repeated code, long section, logical unit).
Create a new function and replace the original code with a call to it.

Output ONLY the refactored code."""

    prompt = f"```python\n{code}\n```"
    if selection:
        prompt += f"\n\nExtract this specific code: {selection}"

    return await call_model_directly(qube, system_prompt, prompt)


def rename_symbol(code: str, old_name: str, new_name: str) -> str:
    """Rename a symbol throughout the code."""
    if not old_name or not new_name:
        return code

    import re
    # Use word boundaries to avoid partial matches
    pattern = rf'\b{re.escape(old_name)}\b'
    return re.sub(pattern, new_name, code)


async def inline_variable(qube, code: str, variable: str = None) -> str:
    """Inline a variable (replace with its value)."""
    system_prompt = """Refactor by inlining variables.
Find variables that are used only once and replace them with their values.
This simplifies the code when the variable name doesn't add clarity.

Output ONLY the refactored code."""

    prompt = f"```python\n{code}\n```"
    if variable:
        prompt += f"\n\nInline this variable: {variable}"

    return await call_model_directly(qube, system_prompt, prompt)


async def simplify_code(qube, code: str) -> str:
    """Simplify code - reduce nesting, simplify conditionals."""
    system_prompt = """Simplify this code:
1. Reduce nesting (use early returns, guard clauses)
2. Simplify conditionals (combine, use ternary where appropriate)
3. Remove redundant code
4. Use more Pythonic idioms

Output ONLY the simplified code."""

    return await call_model_directly(qube, system_prompt, f"```python\n{code}\n```")


async def ai_refactor(qube, code: str, refactor_type: str) -> str:
    """Generic AI-powered refactoring."""
    return await call_model_directly(
        qube,
        f"Refactor this code using the '{refactor_type}' pattern. Output only the refactored code.",
        f"```python\n{code}\n```"
    )


def describe_changes(original: str, refactored: str) -> str:
    """Describe what changed between original and refactored."""
    orig_lines = set(original.strip().split('\n'))
    ref_lines = set(refactored.strip().split('\n'))

    added = len(ref_lines - orig_lines)
    removed = len(orig_lines - ref_lines)

    return f"+{added} lines added, -{removed} lines removed"


def explain_refactoring(refactor_type: str) -> str:
    """Explain what the refactoring does."""
    explanations = {
        "extract_method": "Extract Method: Pulled out a section of code into a new function for reusability and clarity.",
        "rename": "Rename: Changed symbol names to be more descriptive and follow conventions.",
        "inline": "Inline Variable: Replaced variables used once with their values to reduce indirection.",
        "simplify": "Simplify: Reduced nesting and complexity for better readability."
    }
    return explanations.get(refactor_type, f"Applied {refactor_type} refactoring")
```

### Moon Tool: git_operation

```python
async def git_operation(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: git_operation

    Execute git operations (simulated in sandbox).

    Parameters:
        operation: str - commit, branch, merge, status, diff, log
        params: dict - Operation-specific parameters

    Returns:
        success: bool
        operation: str
        result: dict
        message: str
        xp: dict
    """
    operation = params.get("operation")
    op_params = params.get("params", {})

    if not operation:
        return {"success": False, "error": "Missing operation"}

    # Simulate git operations (actual execution would require filesystem access)
    result = {"success": True, "data": {}}

    if operation == "commit":
        result["data"] = simulate_git_commit(op_params)
        result["message"] = f"Committed with message: {op_params.get('message', 'No message')}"

    elif operation == "branch":
        action = op_params.get("action", "create")
        name = op_params.get("name", "new-branch")
        result["data"] = {"action": action, "branch": name}
        result["message"] = f"Branch {name} {action}d"

    elif operation == "status":
        result["data"] = simulate_git_status()
        result["message"] = "Repository status retrieved"

    elif operation == "diff":
        result["data"] = {"target": op_params.get("target", "HEAD")}
        result["message"] = "Diff generated"

    elif operation == "log":
        count = op_params.get("count", 10)
        result["data"] = simulate_git_log(count)
        result["message"] = f"Retrieved {count} commits"

    elif operation == "merge":
        source = op_params.get("source")
        result["data"] = {"source": source, "target": "current"}
        result["message"] = f"Merged {source} into current branch"

    else:
        return {"success": False, "error": f"Unknown operation: {operation}"}

    # Calculate XP
    xp_result = calculate_waitress_xp({"executed": True, "is_novel": True})
    await award_xp_to_skill(qube, "version_control", xp_result["total"])

    return {
        "success": result["success"],
        "operation": operation,
        "result": result["data"],
        "message": result.get("message"),
        "xp": xp_result
    }


def simulate_git_commit(params: Dict[str, Any]) -> Dict[str, Any]:
    """Simulate git commit result."""
    import hashlib
    import time

    message = params.get("message", "Update")
    files = params.get("files", ["file.py"])

    # Generate fake commit hash
    commit_hash = hashlib.sha1(f"{message}{time.time()}".encode()).hexdigest()[:7]

    return {
        "commit": commit_hash,
        "message": message,
        "files_changed": len(files),
        "insertions": 10,
        "deletions": 5
    }


def simulate_git_status() -> Dict[str, Any]:
    """Simulate git status result."""
    return {
        "branch": "feature/coding-tools",
        "staged": ["handlers.py"],
        "modified": ["skill_scanner.py"],
        "untracked": []
    }


def simulate_git_log(count: int) -> List[Dict[str, Any]]:
    """Simulate git log result."""
    return [
        {"hash": "abc1234", "message": "Add coding tools", "author": "Qube", "date": "2024-01-15"},
        {"hash": "def5678", "message": "Fix XP calculation", "author": "Qube", "date": "2024-01-14"},
        {"hash": "ghi9012", "message": "Initial commit", "author": "Qube", "date": "2024-01-13"},
    ][:count]
```

### Moon Tool: generate_docs

```python
async def generate_docs(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: generate_docs

    Generate documentation for code.
    Supports docstrings, README, and API docs.

    Parameters:
        code: str - Code to document
        doc_type: str - "docstring", "readme", "api" (default: docstring)

    Returns:
        success: bool
        doc_type: str
        documented_code: str | None - For docstring type
        readme: str | None - For readme type
        api_docs: str | None - For api type
        xp: dict
    """
    code = params.get("code")
    doc_type = params.get("doc_type", "docstring")

    if not code:
        return {"success": False, "error": "Missing code"}

    result = {"success": True, "doc_type": doc_type}

    if doc_type == "docstring":
        documented_code = await add_docstrings(qube, code)
        result["documented_code"] = documented_code

    elif doc_type == "readme":
        readme = await generate_readme(qube, code)
        result["readme"] = readme

    elif doc_type == "api":
        api_docs = await generate_api_docs(qube, code)
        result["api_docs"] = api_docs

    else:
        return {"success": False, "error": f"Unknown doc_type: {doc_type}"}

    # Calculate XP
    xp_result = calculate_waitress_xp({"executed": True, "is_novel": True})
    await award_xp_to_skill(qube, "documentation", xp_result["total"])

    result["xp"] = xp_result
    return result


async def add_docstrings(qube, code: str) -> str:
    """Add docstrings to functions and classes."""
    system_prompt = """Add comprehensive docstrings to all functions and classes.
Use Google-style docstrings with:
- Brief description
- Args section with types
- Returns section with type
- Raises section if applicable
- Example usage for complex functions

Output the complete code with docstrings added."""

    return await call_model_directly(qube, system_prompt, f"```python\n{code}\n```")


async def generate_readme(qube, code: str) -> str:
    """Generate a README.md for the code."""
    system_prompt = """Generate a README.md for this code.
Include:
- Project title and description
- Installation instructions
- Usage examples
- API reference (brief)
- License placeholder

Use proper Markdown formatting."""

    return await call_model_directly(qube, system_prompt, f"```python\n{code}\n```")


async def generate_api_docs(qube, code: str) -> str:
    """Generate API documentation."""
    system_prompt = """Generate API documentation for this code.
For each public function/class:
- Name and purpose
- Parameters with types and descriptions
- Return value with type
- Example usage
- Notes/warnings

Format as Markdown."""

    return await call_model_directly(qube, system_prompt, f"```python\n{code}\n```")
```

---

## 14. Task 3.12: Register All Tools

### Tool Registry

**File:** `ai/tools/registry.py`
**Location:** Add to tool definitions section

```python
# ============================================================================
# CODING TOOLS (Phase 3)
# ============================================================================

CODING_TOOLS = [
    # Sun Tool
    ToolDefinition(
        name="develop_code",
        description="Write and execute code in one workflow. The fundamental coding tool.",
        parameters={
            "task": {"type": "string", "description": "Description of what to build", "required": True},
            "language": {"type": "string", "description": "Programming language (default: python)"},
            "submit": {"type": "boolean", "description": "Submit for XP (default: true)"},
            "test": {"type": "boolean", "description": "Include tests (default: true)"}
        },
        handler="develop_code",
        skill_required="coding",
        xp_model="waitress"
    ),

    # Planet 1: Testing
    ToolDefinition(
        name="run_tests",
        description="Execute a test suite against code. Returns pass/fail counts and coverage.",
        parameters={
            "code": {"type": "string", "description": "Code to test", "required": True},
            "test_code": {"type": "string", "description": "Test suite", "required": True},
            "framework": {"type": "string", "description": "Test framework (default: pytest)"},
            "coverage": {"type": "boolean", "description": "Measure coverage (default: true)"}
        },
        handler="run_tests_handler",
        skill_required="testing",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="write_unit_test",
        description="Generate unit tests for a function or class.",
        parameters={
            "code": {"type": "string", "description": "Code to test", "required": True},
            "focus": {"type": "string", "description": "Specific function/class to test"},
            "framework": {"type": "string", "description": "Test framework (default: pytest)"}
        },
        handler="write_unit_test",
        skill_required="unit_tests",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="measure_coverage",
        description="Measure test coverage and identify untested areas.",
        parameters={
            "code": {"type": "string", "description": "Code to analyze", "required": True},
            "test_code": {"type": "string", "description": "Test suite", "required": True}
        },
        handler="measure_coverage_handler",
        skill_required="test_coverage",
        xp_model="waitress"
    ),

    # Planet 2: Debugging
    ToolDefinition(
        name="debug_code",
        description="Systematic debugging - analyze error, trace cause, suggest fix.",
        parameters={
            "code": {"type": "string", "description": "Code with bug", "required": True},
            "error": {"type": "string", "description": "Error message", "required": True},
            "context": {"type": "string", "description": "Additional context"}
        },
        handler="debug_code",
        skill_required="debugging",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="analyze_error",
        description="Parse and explain error messages in human-readable form.",
        parameters={
            "error": {"type": "string", "description": "Error message/stack trace", "required": True}
        },
        handler="analyze_error",
        skill_required="error_analysis",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="find_root_cause",
        description="Trace an error back to its root cause.",
        parameters={
            "code": {"type": "string", "description": "Code with error", "required": True},
            "error": {"type": "string", "description": "Error message", "required": True},
            "execution_trace": {"type": "array", "description": "Optional execution trace"}
        },
        handler="find_root_cause",
        skill_required="root_cause",
        xp_model="waitress"
    ),

    # Planet 3: Algorithms
    ToolDefinition(
        name="benchmark_code",
        description="Benchmark code performance with varying input sizes.",
        parameters={
            "code": {"type": "string", "description": "Code to benchmark", "required": True},
            "inputs": {"type": "array", "description": "Test inputs of varying sizes"},
            "iterations": {"type": "integer", "description": "Runs per input (default: 3)"}
        },
        handler="benchmark_code",
        skill_required="algorithms",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="analyze_complexity",
        description="Analyze Big O time and space complexity.",
        parameters={
            "code": {"type": "string", "description": "Code to analyze", "required": True}
        },
        handler="analyze_complexity",
        skill_required="complexity_analysis",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="tune_performance",
        description="Suggest and apply performance optimizations.",
        parameters={
            "code": {"type": "string", "description": "Code to optimize", "required": True},
            "benchmark_results": {"type": "object", "description": "Previous benchmark results"}
        },
        handler="tune_performance",
        skill_required="performance_tuning",
        xp_model="waitress"
    ),

    # Planet 4: Hacking
    ToolDefinition(
        name="security_scan",
        description="Scan code for security vulnerabilities (OWASP Top 10).",
        parameters={
            "code": {"type": "string", "description": "Code to scan", "required": True},
            "scan_type": {"type": "string", "description": "quick or thorough (default: thorough)"},
            "language": {"type": "string", "description": "Programming language (default: python)"}
        },
        handler="security_scan",
        skill_required="hacking",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="find_exploit",
        description="Find specific exploits and generate proof of concept.",
        parameters={
            "code": {"type": "string", "description": "Code to analyze", "required": True},
            "vuln_type": {"type": "string", "description": "Type of vulnerability to look for"}
        },
        handler="find_exploit",
        skill_required="exploits",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="reverse_engineer",
        description="Analyze and deobfuscate code or binaries.",
        parameters={
            "target": {"type": "string", "description": "Code to analyze", "required": True},
            "target_type": {"type": "string", "description": "Type hint (minified_js, obfuscated, binary_hex)"}
        },
        handler="reverse_engineer",
        skill_required="reverse_engineering",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="pen_test",
        description="Conduct systematic penetration test.",
        parameters={
            "target": {"type": "string", "description": "Target to test", "required": True},
            "scope": {"type": "string", "description": "full or limited (default: limited)"}
        },
        handler="pen_test",
        skill_required="penetration_testing",
        xp_model="waitress"
    ),

    # Planet 5: Code Review
    ToolDefinition(
        name="review_code",
        description="Comprehensive code review for style, logic, performance, security.",
        parameters={
            "code": {"type": "string", "description": "Code to review", "required": True},
            "review_focus": {"type": "string", "description": "all, style, logic, performance, security"},
            "language": {"type": "string", "description": "Programming language (default: python)"}
        },
        handler="review_code",
        skill_required="code_review",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="refactor_code",
        description="Refactor code to improve structure without changing behavior.",
        parameters={
            "code": {"type": "string", "description": "Code to refactor", "required": True},
            "refactor_type": {"type": "string", "description": "auto, extract_method, rename, inline, simplify"},
            "selection": {"type": "string", "description": "Code selection for extract_method"},
            "old_name": {"type": "string", "description": "For rename refactoring"},
            "new_name": {"type": "string", "description": "For rename refactoring"}
        },
        handler="refactor_code",
        skill_required="refactoring",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="git_operation",
        description="Execute git operations (commit, branch, merge, status, diff, log).",
        parameters={
            "operation": {"type": "string", "description": "Git operation", "required": True},
            "params": {"type": "object", "description": "Operation-specific parameters"}
        },
        handler="git_operation",
        skill_required="version_control",
        xp_model="waitress"
    ),
    ToolDefinition(
        name="generate_docs",
        description="Generate documentation for code (docstrings, README, API docs).",
        parameters={
            "code": {"type": "string", "description": "Code to document", "required": True},
            "doc_type": {"type": "string", "description": "docstring, readme, api (default: docstring)"}
        },
        handler="generate_docs",
        skill_required="documentation",
        xp_model="waitress"
    ),
]


def register_coding_tools(registry: ToolRegistry) -> None:
    """Register all Coding tools with the registry."""
    for tool in CODING_TOOLS:
        registry.register(tool)
```

### Handler Registration

**File:** `ai/tools/handlers.py`
**Location:** Add to `register_default_tools` function

```python
def register_default_tools(qube) -> None:
    """Register all default tool handlers."""
    # ... existing registrations ...

    # Coding tools (Phase 3)
    qube.register_handler("develop_code", develop_code)
    qube.register_handler("run_tests", run_tests_handler)
    qube.register_handler("write_unit_test", write_unit_test)
    qube.register_handler("measure_coverage", measure_coverage_handler)
    qube.register_handler("debug_code", debug_code)
    qube.register_handler("analyze_error", analyze_error)
    qube.register_handler("find_root_cause", find_root_cause)
    qube.register_handler("benchmark_code", benchmark_code)
    qube.register_handler("analyze_complexity", analyze_complexity)
    qube.register_handler("tune_performance", tune_performance)
    qube.register_handler("security_scan", security_scan)
    qube.register_handler("find_exploit", find_exploit)
    qube.register_handler("reverse_engineer", reverse_engineer)
    qube.register_handler("pen_test", pen_test)
    qube.register_handler("review_code", review_code)
    qube.register_handler("refactor_code", refactor_code)
    qube.register_handler("git_operation", git_operation)
    qube.register_handler("generate_docs", generate_docs)
```

---

## 15. Task 3.13: Frontend Synchronization

### TypeScript Skill Definitions

**File:** `qubes-gui/src/data/skillDefinitions.ts`
**Location:** Add to skillDefinitions array

```typescript
// ============================================================================
// CODING (Phase 3) - 18 skills
// Theme: Ship It (Results-Focused)
// XP Model: Waitress (1 base + 0-9 tips)
// ============================================================================

// Sun
{
  id: 'coding',
  name: 'Coding',
  description: 'Master the art of writing and shipping working code',
  category: 'coding',
  tier: 'sun',
  xpRequired: 1000,
  toolReward: 'develop_code',
  icon: '💻',
},

// Planet 1: Testing
{
  id: 'testing',
  name: 'Testing',
  description: 'Write and run tests to verify code works correctly',
  category: 'coding',
  tier: 'planet',
  parent: 'coding',
  xpRequired: 500,
  toolReward: 'run_tests',
  icon: '🧪',
  unlocksAt: { skill: 'coding', xp: 100 },
},
{
  id: 'unit_tests',
  name: 'Unit Tests',
  description: 'Write focused tests for individual functions',
  category: 'coding',
  tier: 'moon',
  parent: 'testing',
  xpRequired: 250,
  toolReward: 'write_unit_test',
  icon: '🔬',
  unlocksAt: { skill: 'testing', xp: 50 },
},
{
  id: 'test_coverage',
  name: 'Test Coverage',
  description: 'Measure and improve test coverage',
  category: 'coding',
  tier: 'moon',
  parent: 'testing',
  xpRequired: 250,
  toolReward: 'measure_coverage',
  icon: '📊',
  unlocksAt: { skill: 'testing', xp: 50 },
},

// Planet 2: Debugging
{
  id: 'debugging',
  name: 'Debugging',
  description: 'Find and fix bugs systematically',
  category: 'coding',
  tier: 'planet',
  parent: 'coding',
  xpRequired: 500,
  toolReward: 'debug_code',
  icon: '🐛',
  unlocksAt: { skill: 'coding', xp: 100 },
},
{
  id: 'error_analysis',
  name: 'Error Analysis',
  description: 'Understand WHAT went wrong from error messages',
  category: 'coding',
  tier: 'moon',
  parent: 'debugging',
  xpRequired: 250,
  toolReward: 'analyze_error',
  icon: '🔍',
  unlocksAt: { skill: 'debugging', xp: 50 },
},
{
  id: 'root_cause',
  name: 'Root Cause',
  description: 'Understand WHY the error happened',
  category: 'coding',
  tier: 'moon',
  parent: 'debugging',
  xpRequired: 250,
  toolReward: 'find_root_cause',
  icon: '🎯',
  unlocksAt: { skill: 'debugging', xp: 50 },
},

// Planet 3: Algorithms
{
  id: 'algorithms',
  name: 'Algorithms',
  description: 'Optimize code performance and efficiency',
  category: 'coding',
  tier: 'planet',
  parent: 'coding',
  xpRequired: 500,
  toolReward: 'benchmark_code',
  icon: '⚡',
  unlocksAt: { skill: 'coding', xp: 100 },
},
{
  id: 'complexity_analysis',
  name: 'Complexity Analysis',
  description: 'Understand Big O time and space complexity',
  category: 'coding',
  tier: 'moon',
  parent: 'algorithms',
  xpRequired: 250,
  toolReward: 'analyze_complexity',
  icon: '📈',
  unlocksAt: { skill: 'algorithms', xp: 50 },
},
{
  id: 'performance_tuning',
  name: 'Performance Tuning',
  description: 'Make code faster through optimization',
  category: 'coding',
  tier: 'moon',
  parent: 'algorithms',
  xpRequired: 250,
  toolReward: 'tune_performance',
  icon: '🚀',
  unlocksAt: { skill: 'algorithms', xp: 50 },
},

// Planet 4: Hacking
{
  id: 'hacking',
  name: 'Hacking',
  description: 'Find and exploit security vulnerabilities',
  category: 'coding',
  tier: 'planet',
  parent: 'coding',
  xpRequired: 500,
  toolReward: 'security_scan',
  icon: '🔓',
  unlocksAt: { skill: 'coding', xp: 100 },
},
{
  id: 'exploits',
  name: 'Exploits',
  description: 'Discover exploitable vulnerabilities',
  category: 'coding',
  tier: 'moon',
  parent: 'hacking',
  xpRequired: 250,
  toolReward: 'find_exploit',
  icon: '💉',
  unlocksAt: { skill: 'hacking', xp: 50 },
},
{
  id: 'reverse_engineering',
  name: 'Reverse Engineering',
  description: 'Understand systems by taking them apart',
  category: 'coding',
  tier: 'moon',
  parent: 'hacking',
  xpRequired: 250,
  toolReward: 'reverse_engineer',
  icon: '🔧',
  unlocksAt: { skill: 'hacking', xp: 50 },
},
{
  id: 'penetration_testing',
  name: 'Penetration Testing',
  description: 'Systematic security testing methodology',
  category: 'coding',
  tier: 'moon',
  parent: 'hacking',
  xpRequired: 250,
  toolReward: 'pen_test',
  icon: '🛡️',
  unlocksAt: { skill: 'hacking', xp: 50 },
},

// Planet 5: Code Review
{
  id: 'code_review',
  name: 'Code Review',
  description: 'Critique and improve code quality',
  category: 'coding',
  tier: 'planet',
  parent: 'coding',
  xpRequired: 500,
  toolReward: 'review_code',
  icon: '👀',
  unlocksAt: { skill: 'coding', xp: 100 },
},
{
  id: 'refactoring',
  name: 'Refactoring',
  description: 'Improve code structure without changing behavior',
  category: 'coding',
  tier: 'moon',
  parent: 'code_review',
  xpRequired: 250,
  toolReward: 'refactor_code',
  icon: '♻️',
  unlocksAt: { skill: 'code_review', xp: 50 },
},
{
  id: 'version_control',
  name: 'Version Control',
  description: 'Manage code changes with git',
  category: 'coding',
  tier: 'moon',
  parent: 'code_review',
  xpRequired: 250,
  toolReward: 'git_operation',
  icon: '📚',
  unlocksAt: { skill: 'code_review', xp: 50 },
},
{
  id: 'documentation',
  name: 'Documentation',
  description: 'Write clear documentation for code',
  category: 'coding',
  tier: 'moon',
  parent: 'code_review',
  xpRequired: 250,
  toolReward: 'generate_docs',
  icon: '📝',
  unlocksAt: { skill: 'code_review', xp: 50 },
},
```

### Add Category Definition

```typescript
// In categories array
{
  id: 'coding',
  name: 'Coding',
  description: 'Ship It - Write, test, debug, and optimize code',
  icon: '💻',
  color: '#10B981', // Green
  xpModel: 'waitress', // Different from standard
},
```

---

## 16. Task 3.14: LEARNING Block Integration

### LEARNING Block Structure for Coding

Coding tools create LEARNING blocks to capture knowledge:

```python
# In core/block.py - Coding-specific LEARNING data

CODING_LEARNING_TYPES = [
    "procedure",      # How to solve a coding problem
    "pattern",        # Recognized code pattern
    "antipattern",    # Bad practice discovered
    "optimization",   # Performance improvement learned
    "security",       # Security vulnerability/fix learned
    "debugging",      # Debugging technique learned
]

# Example LEARNING block data for coding:
{
    "learning_type": "procedure",
    "domain": "coding",
    "task": "Sort a list of dictionaries by key",
    "language": "python",
    "fingerprint": "abc123def456",  # AST fingerprint
    "code_summary": "Used sorted() with key=lambda",
    "milestones_achieved": ["executed_successfully", "all_tests_passed"],
    "xp_earned": 7,
    "source": "develop_code",
    "confidence": 0.85,
    "tags": ["sorting", "python", "lambda"]
}
```

### LEARNING Block Creation Functions

**File:** `ai/tools/handlers.py`
**Location:** Add helper functions for coding LEARNING blocks

```python
async def create_coding_learning(
    qube,
    learning_type: str,
    task: str,
    code: str,
    language: str,
    result: Dict[str, Any],
    source_tool: str
) -> None:
    """
    Create a LEARNING block for coding activity.

    Args:
        qube: The Qube instance
        learning_type: Type of learning (procedure, pattern, etc.)
        task: Description of what was learned
        code: The code involved
        language: Programming language
        result: Result from the coding tool
        source_tool: Name of the tool that created this learning
    """
    from core.block import Block, BlockType
    from ai.tools.ast_fingerprint import fingerprint_code

    # Generate fingerprint
    fp_result = fingerprint_code(code, language)

    learning_data = {
        "learning_type": learning_type,
        "domain": "coding",
        "task": task,
        "language": language,
        "fingerprint": fp_result["fingerprint"],
        "code_summary": summarize_code(code, language),
        "milestones_achieved": result.get("xp", {}).get("milestones", []),
        "xp_earned": result.get("xp", {}).get("total", 0),
        "source": source_tool,
        "confidence": calculate_coding_confidence(result),
        "tags": extract_coding_tags(code, language)
    }

    block = Block(
        block_type=BlockType.LEARNING,
        data=learning_data
    )

    await qube.chain_state.add_block(block)


def calculate_coding_confidence(result: Dict[str, Any]) -> float:
    """
    Calculate confidence score for coding learning.

    Higher confidence for:
    - Tests passed
    - No security vulnerabilities
    - Good performance
    """
    confidence = 0.5  # Base confidence

    xp_data = result.get("xp", {})
    milestones = xp_data.get("milestones", [])

    if "executed_successfully" in milestones:
        confidence += 0.1
    if "all_tests_passed" in milestones:
        confidence += 0.2
    if "no_vulnerabilities" in milestones:
        confidence += 0.1
    if "good_performance" in milestones:
        confidence += 0.1

    return min(1.0, confidence)


def extract_coding_tags(code: str, language: str) -> List[str]:
    """Extract relevant tags from code."""
    tags = [language]

    # Python-specific tags
    if language == "python":
        if "async" in code:
            tags.append("async")
        if "class " in code:
            tags.append("oop")
        if "import pandas" in code or "import numpy" in code:
            tags.append("data-science")
        if "def test_" in code:
            tags.append("testing")
        if "flask" in code.lower() or "django" in code.lower():
            tags.append("web")

    return tags[:5]  # Limit to 5 tags
```

### Integration with Existing Tools

Each coding tool should call `create_coding_learning` on success:

```python
# Example in develop_code handler
if execution_result["success"]:
    await create_coding_learning(
        qube=qube,
        learning_type="procedure",
        task=task,
        code=code,
        language=language,
        result={"xp": xp_result},
        source_tool="develop_code"
    )
```

---

## 17. Task 3.15: Testing & Validation

### Unit Tests for Waitress XP

**File:** `tests/test_waitress_xp.py`

```python
import pytest
from ai.tools.waitress_xp import WaitressXPCalculator, calculate_waitress_xp


class TestWaitressXP:
    """Test Waitress XP calculation."""

    def test_base_xp_always_awarded(self):
        """Base XP (1) is always awarded."""
        result = calculate_waitress_xp({})
        assert result["base"] == 1
        assert result["total"] >= 1

    def test_execution_milestone(self):
        """Successful execution adds 1 tip."""
        result = calculate_waitress_xp({"executed": True})
        assert "executed_successfully" in result["milestones"]
        assert result["tips"] >= 1

    def test_tests_passed_milestone(self):
        """All tests passing adds 2 tips."""
        result = calculate_waitress_xp({
            "executed": True,
            "test_results": {"all_passed": True, "passed": 5, "total": 5}
        })
        assert "all_tests_passed" in result["milestones"]
        assert result["tips"] >= 3  # 1 for executed + 2 for tests

    def test_coverage_milestone(self):
        """Coverage >= 80% adds 1 tip."""
        result = calculate_waitress_xp({
            "executed": True,
            "coverage_percent": 85
        })
        assert "high_coverage" in result["milestones"]

    def test_no_vulnerabilities_milestone(self):
        """No vulnerabilities adds 1 tip."""
        result = calculate_waitress_xp({
            "executed": True,
            "vulnerabilities": []
        })
        assert "no_vulnerabilities" in result["milestones"]

    def test_tips_capped_at_9(self):
        """Tips are capped at 9 (max total XP is 10)."""
        result = calculate_waitress_xp({
            "executed": True,
            "test_results": {"all_passed": True},
            "coverage_percent": 100,
            "vulnerabilities": [],
            "performance": {"within_threshold": True},
            "lint_errors": [],
            "is_novel": True,
            "has_docs": True,
            "follows_patterns": True
        })
        assert result["tips"] <= 9
        assert result["total"] <= 10

    def test_duplicate_code_no_novel_tip(self):
        """Duplicate fingerprint doesn't get novel tip."""
        result = calculate_waitress_xp({
            "executed": True,
            "is_novel": False
        })
        assert "novel_approach" not in result["milestones"]
```

### Unit Tests for AST Fingerprinting

**File:** `tests/test_ast_fingerprint.py`

```python
import pytest
from ai.tools.ast_fingerprint import ASTFingerprinter, fingerprint_code


class TestASTFingerprint:
    """Test AST fingerprinting for anti-gaming."""

    def setup_method(self):
        self.fp = ASTFingerprinter()
        self.fp.clear_seen()

    def test_same_fingerprint_for_variable_rename(self):
        """Variable renames should produce same fingerprint."""
        code1 = "def add(a, b): return a + b"
        code2 = "def add(x, y): return x + y"

        fp1 = self.fp.fingerprint(code1, "python", check_duplicate=False)
        fp2 = self.fp.fingerprint(code2, "python", check_duplicate=False)

        assert fp1.fingerprint == fp2.fingerprint

    def test_different_fingerprint_for_different_algorithm(self):
        """Different algorithms should produce different fingerprints."""
        code1 = "def add(a, b): return a + b"
        code2 = "def add(a, b): return sum([a, b])"

        fp1 = self.fp.fingerprint(code1, "python", check_duplicate=False)
        fp2 = self.fp.fingerprint(code2, "python", check_duplicate=False)

        assert fp1.fingerprint != fp2.fingerprint

    def test_same_fingerprint_for_formatting_changes(self):
        """Formatting changes should produce same fingerprint."""
        code1 = "def add(a, b): return a + b"
        code2 = """
def add(a, b):
    return a + b
"""
        fp1 = self.fp.fingerprint(code1, "python", check_duplicate=False)
        fp2 = self.fp.fingerprint(code2, "python", check_duplicate=False)

        assert fp1.fingerprint == fp2.fingerprint

    def test_duplicate_detection(self):
        """Duplicate code should be detected."""
        code = "def add(a, b): return a + b"

        fp1 = self.fp.fingerprint(code, "python", check_duplicate=True)
        assert not fp1.is_duplicate

        fp2 = self.fp.fingerprint(code, "python", check_duplicate=True)
        assert fp2.is_duplicate

    def test_javascript_fingerprinting(self):
        """JavaScript fingerprinting should work."""
        code = "function add(a, b) { return a + b; }"
        fp = self.fp.fingerprint(code, "javascript")
        assert fp.fingerprint
        assert fp.language == "javascript"
```

### Integration Tests

**File:** `tests/test_coding_tools.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestDevelopCode:
    """Test develop_code tool."""

    @pytest.mark.asyncio
    async def test_basic_code_generation(self):
        """Test basic code generation."""
        qube = MagicMock()
        qube.chain_state.get_skill_xp.return_value = 0

        with patch('ai.tools.handlers.call_model_directly', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "```python\ndef hello():\n    print('Hello')\n```"

            with patch('ai.tools.handlers.execute_code', new_callable=AsyncMock) as mock_exec:
                mock_exec.return_value = {
                    "success": True,
                    "output": "Hello",
                    "errors": None,
                    "execution_time_ms": 100
                }

                from ai.tools.handlers import develop_code
                result = await develop_code(qube, {"task": "Print hello"})

                assert result["success"]
                assert "def hello" in result["code"]
                assert result["xp"]["total"] >= 1


class TestSecurityScan:
    """Test security_scan tool."""

    @pytest.mark.asyncio
    async def test_detects_eval_vulnerability(self):
        """Test that eval() is detected as vulnerability."""
        qube = MagicMock()

        code = """
def process(user_input):
    return eval(user_input)
"""
        from ai.tools.handlers import security_scan
        result = await security_scan(qube, {"code": code, "scan_type": "quick"})

        assert result["vulnerabilities_found"] > 0
        assert any(v["type"] == "code_injection" for v in result["all_vulnerabilities"])

    @pytest.mark.asyncio
    async def test_clean_code_no_vulnerabilities(self):
        """Test that clean code has no vulnerabilities."""
        qube = MagicMock()

        code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        from ai.tools.handlers import security_scan
        result = await security_scan(qube, {"code": code, "scan_type": "quick"})

        assert result["vulnerabilities_found"] == 0
```

### Validation Checklist

```markdown
## Phase 3 Validation Checklist

### Skill Definitions
- [ ] 18 skills defined in Python (utils/skill_definitions.py)
- [ ] 18 skills defined in TypeScript (skillDefinitions.ts)
- [ ] Skill IDs match between Python and TypeScript
- [ ] All tool rewards correctly mapped
- [ ] XP requirements correct (Sun: 1000, Planet: 500, Moon: 250)

### Tool Mappings
- [ ] 18 tools in TOOL_TO_SKILL_MAPPING
- [ ] All tools in WAITRESS_XP_TOOLS set
- [ ] Handler functions registered

### Waitress XP System
- [ ] Base XP always 1
- [ ] Tips capped at 9
- [ ] All milestones correctly calculated
- [ ] XP flows up hierarchy (trickle-up)

### AST Fingerprinting
- [ ] Same fingerprint for variable renames
- [ ] Same fingerprint for formatting changes
- [ ] Different fingerprint for algorithm changes
- [ ] Duplicate detection works
- [ ] Fingerprints stored in LEARNING blocks

### Code Execution
- [ ] Subprocess backend works for Python
- [ ] Docker backend works (if available)
- [ ] Timeout enforced
- [ ] Memory limit enforced
- [ ] Safe from injection attacks

### LEARNING Blocks
- [ ] Created on successful code operations
- [ ] Contain fingerprint, milestones, XP
- [ ] Indexed for retrieval

### Security Tools
- [ ] Disclaimer on all hacking tools
- [ ] PoCs are educational, not weaponized
- [ ] No actual exploitation performed
```

---

## Appendix A: Tool Summary Table

| Tool Name | Skill | Tier | XP Model | Purpose |
|-----------|-------|------|----------|---------|
| `develop_code` | coding | Sun | Waitress | Write and execute code |
| `run_tests` | testing | Planet | Waitress | Execute test suites |
| `write_unit_test` | unit_tests | Moon | Waitress | Generate unit tests |
| `measure_coverage` | test_coverage | Moon | Waitress | Measure test coverage |
| `debug_code` | debugging | Planet | Waitress | Systematic debugging |
| `analyze_error` | error_analysis | Moon | Waitress | Explain error messages |
| `find_root_cause` | root_cause | Moon | Waitress | Trace to root cause |
| `benchmark_code` | algorithms | Planet | Waitress | Performance benchmarking |
| `analyze_complexity` | complexity_analysis | Moon | Waitress | Big O analysis |
| `tune_performance` | performance_tuning | Moon | Waitress | Optimize performance |
| `security_scan` | hacking | Planet | Waitress | Vulnerability scanning |
| `find_exploit` | exploits | Moon | Waitress | Find exploits (educational) |
| `reverse_engineer` | reverse_engineering | Moon | Waitress | Analyze/deobfuscate |
| `pen_test` | penetration_testing | Moon | Waitress | Systematic pen testing |
| `review_code` | code_review | Planet | Waitress | Code quality review |
| `refactor_code` | refactoring | Moon | Waitress | Improve code structure |
| `git_operation` | version_control | Moon | Waitress | Git operations |
| `generate_docs` | documentation | Moon | Waitress | Generate documentation |

---

## Appendix B: File Reference

| File | Purpose | Changes |
|------|---------|---------|
| `utils/skill_definitions.py` | Python skill definitions | Add 18 coding skills |
| `ai/skill_scanner.py` | Tool-to-skill mapping, XP calculation | Add mappings, Waitress XP logic |
| `ai/tools/handlers.py` | Tool handler implementations | Add 18 handler functions |
| `ai/tools/registry.py` | Tool registration | Register 18 coding tools |
| `ai/tools/waitress_xp.py` | Waitress XP calculation | **NEW FILE** |
| `ai/tools/ast_fingerprint.py` | AST fingerprinting | **NEW FILE** |
| `ai/tools/code_execution.py` | Safe code execution | **NEW FILE** |
| `qubes-gui/src/data/skillDefinitions.ts` | TypeScript skill definitions | Add 18 coding skills |
| `tests/test_waitress_xp.py` | Waitress XP tests | **NEW FILE** |
| `tests/test_ast_fingerprint.py` | Fingerprinting tests | **NEW FILE** |
| `tests/test_coding_tools.py` | Coding tools tests | **NEW FILE** |

---

## Appendix C: Waitress XP Tip Calculation

### Milestone Values

| Milestone | Condition | Tip Value |
|-----------|-----------|-----------|
| `executed_successfully` | Code ran without crash | +1 |
| `all_tests_passed` | All tests pass | +2 |
| `high_coverage` | Coverage ≥ 80% | +1 |
| `no_vulnerabilities` | Security scan clean | +1 |
| `good_performance` | Within time threshold | +1 |
| `clean_code` | No linting errors | +1 |
| `novel_approach` | New fingerprint | +1 |
| `well_documented` | Has docstrings/comments | +0.5 |
| `follows_patterns` | Matches project style | +0.5 |

### Example Calculations

**Minimal Success (1 XP):**
- Code submitted but crashes
- Base: 1, Tips: 0
- Total: 1 XP

**Basic Working Code (3 XP):**
- Code executes successfully (+1)
- No tests, no security scan
- Novel approach (+1)
- Base: 1, Tips: 2
- Total: 3 XP

**Well-Tested Code (7 XP):**
- Executes successfully (+1)
- All tests pass (+2)
- 85% coverage (+1)
- No vulnerabilities (+1)
- Clean code (+1)
- Base: 1, Tips: 6
- Total: 7 XP

**Maximum Quality (10 XP):**
- All milestones achieved
- Base: 1, Tips: 9 (capped)
- Total: 10 XP

---

## End of Phase 3 Implementation Blueprint

**Document Statistics:**
- Total Tools: 18
- New Files: 6
- Modified Files: 5
- Test Files: 3

**Next Phase:** Phase 4 (Creative Expression)
