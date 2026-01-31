"""
Coding Tools (Phase 3)

Theme: Ship It (Results-Focused)
XP Model: Waitress (base 1 + tips 0-9)

18 tools total:
- Sun: develop_code
- Planet 1 (Testing): run_tests, Moons: write_unit_test, measure_coverage
- Planet 2 (Debugging): debug_code, Moons: analyze_error, find_root_cause
- Planet 3 (Algorithms): benchmark_code, Moons: analyze_complexity, tune_performance
- Planet 4 (Hacking): security_scan, Moons: find_exploit, reverse_engineer, pen_test
- Planet 5 (Code Review): review_code, Moons: refactor_code, git_operation, generate_docs

NOTE: Code execution environment is placeholder - returns mock results.
Real implementation will use Pyodide (browser) or Docker (server).
"""

from typing import Dict, Any, Optional, List
import re
import hashlib


# ============================================================================
# PLACEHOLDER CODE EXECUTION
# These will be replaced with real Pyodide/Docker execution later
# ============================================================================

async def _placeholder_execute(code: str, language: str = "python") -> Dict[str, Any]:
    """Placeholder code execution - returns mock success result."""
    return {
        "success": True,
        "output": f"[Placeholder] Code execution simulated for {language}\n>>> Code length: {len(code)} chars",
        "errors": None,
        "execution_time_ms": 42.0,
        "backend": "placeholder"
    }


async def _placeholder_run_tests(code: str, test_code: str) -> Dict[str, Any]:
    """Placeholder test execution - returns mock test results."""
    # Count test functions to simulate results
    test_count = len(re.findall(r'def test_', test_code)) or 1
    return {
        "success": True,
        "all_passed": True,
        "total": test_count,
        "passed": test_count,
        "failed": 0,
        "output": f"[Placeholder] {test_count} tests passed",
        "errors": None,
        "execution_time_ms": 100.0
    }


def _placeholder_fingerprint(code: str, language: str = "python") -> Dict[str, Any]:
    """Generate a simple fingerprint for code."""
    # Simple hash-based fingerprint
    normalized = re.sub(r'\s+', ' ', code.strip())
    fp = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return {
        "fingerprint": fp,
        "language": language,
        "is_duplicate": False,
        "node_count": len(code.split())
    }


def _calculate_waitress_xp(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate XP using Waitress model.
    Base: 1 XP (always)
    Tips: 0-9 based on quality milestones
    """
    base = 1
    tips = 0
    milestones = []

    # Milestone 1: Code executed (+1)
    if result.get("executed", False):
        tips += 1
        milestones.append("executed_successfully")

    # Milestone 2: Tests passed (+2)
    if result.get("tests_passed", False):
        tips += 2
        milestones.append("all_tests_passed")

    # Milestone 3: High coverage (+1)
    if result.get("coverage_percent", 0) >= 80:
        tips += 1
        milestones.append("high_coverage")

    # Milestone 4: No vulnerabilities (+1)
    if len(result.get("vulnerabilities", [])) == 0:
        tips += 1
        milestones.append("no_vulnerabilities")

    # Milestone 5: Good performance (+1)
    if result.get("performance_ok", False):
        tips += 1
        milestones.append("good_performance")

    # Milestone 6: Clean code (+1)
    if len(result.get("lint_errors", [])) == 0:
        tips += 1
        milestones.append("clean_code")

    # Milestone 7: Novel approach (+1)
    if result.get("is_novel", True):
        tips += 1
        milestones.append("novel_approach")

    tips = min(tips, 9)  # Cap at 9

    return {
        "base": base,
        "tips": tips,
        "total": base + tips,
        "milestones": milestones,
        "model": "waitress"
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def call_model_for_code(qube, system_prompt: str, user_prompt: str) -> str:
    """Call the AI model to generate or analyze code."""
    # Import here to avoid circular imports
    from ai.tools.handlers import call_model_directly
    return await call_model_directly(qube, system_prompt, user_prompt)


def extract_code_block(response: str, language: str = "python") -> str:
    """Extract code from markdown code blocks."""
    # Try language-specific block
    pattern = rf'```{language}\n(.*?)```'
    match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try generic code block
    pattern = r'```\n(.*?)```'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Return as-is
    return response.strip()


# ============================================================================
# SUN TOOL: develop_code
# ============================================================================

async def develop_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sun Tool: develop_code

    Write and execute code in one workflow.
    Uses Waitress XP model (base 1 + tips 0-9).

    Parameters:
        task: str - Description of what to build
        language: str - Programming language (default: python)
        include_tests: bool - Whether to include tests (default: True)

    Returns:
        success: bool
        code: str - Generated code
        output: str - Execution output
        fingerprint: str - Code fingerprint
        xp: dict - Waitress XP result
    """
    task = params.get("task")
    language = params.get("language", "python")
    include_tests = params.get("include_tests", True)

    if not task:
        return {"success": False, "error": "Missing required parameter: task"}

    # Generate code using LLM
    system_prompt = f"""You are an expert {language} programmer.
Write clean, working code that accomplishes the given task.
Include comments explaining the approach.
{"Include basic test functions at the end." if include_tests else ""}
Output ONLY the code, no explanations."""

    response = await call_model_for_code(qube, system_prompt, f"Task: {task}")
    code = extract_code_block(response, language)

    # Fingerprint the code
    fp_result = _placeholder_fingerprint(code, language)

    # Execute the code (placeholder)
    exec_result = await _placeholder_execute(code, language)

    # Run tests if included (placeholder)
    test_results = {"all_passed": False, "total": 0}
    if include_tests and exec_result["success"]:
        test_results = await _placeholder_run_tests(code, code)

    # Calculate Waitress XP
    xp_input = {
        "executed": exec_result["success"],
        "tests_passed": test_results.get("all_passed", False),
        "is_novel": not fp_result["is_duplicate"],
        "lint_errors": [],
        "vulnerabilities": []
    }
    xp_result = _calculate_waitress_xp(xp_input)

    return {
        "success": exec_result["success"],
        "code": code,
        "output": exec_result["output"],
        "errors": exec_result.get("errors"),
        "fingerprint": fp_result["fingerprint"],
        "is_novel": not fp_result["is_duplicate"],
        "test_results": test_results if include_tests else None,
        "xp": xp_result
    }


# ============================================================================
# PLANET 1: TESTING
# ============================================================================

async def run_tests(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: run_tests

    Execute a test suite against code.

    Parameters:
        code: str - Code to test
        test_code: str - Test suite
        framework: str - Test framework (default: pytest)

    Returns:
        success: bool
        all_passed: bool
        total_tests: int
        passed: int
        failed: int
    """
    code = params.get("code")
    test_code = params.get("test_code")
    framework = params.get("framework", "pytest")

    if not code or not test_code:
        return {"success": False, "error": "Missing required parameters: code and test_code"}

    result = await _placeholder_run_tests(code, test_code)

    xp_input = {
        "executed": True,
        "tests_passed": result["all_passed"],
        "is_novel": True
    }
    xp_result = _calculate_waitress_xp(xp_input)

    return {
        "success": result["success"],
        "all_passed": result["all_passed"],
        "total_tests": result["total"],
        "passed": result["passed"],
        "failed": result["failed"],
        "output": result["output"],
        "xp": xp_result
    }


async def write_unit_test(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: write_unit_test

    Generate unit tests for a function or class.

    Parameters:
        code: str - Code to test
        focus: str - Specific function/class to test (optional)
        framework: str - Test framework (default: pytest)

    Returns:
        success: bool
        test_code: str - Generated test code
        test_count: int - Number of test cases
    """
    code = params.get("code")
    focus = params.get("focus", "")
    framework = params.get("framework", "pytest")

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    system_prompt = f"""You are an expert test engineer using {framework}.
Generate comprehensive unit tests for the given code.
{"Focus on testing: " + focus if focus else "Test all public functions."}
Include edge cases and error conditions.
Output ONLY the test code."""

    response = await call_model_for_code(qube, system_prompt, f"Code to test:\n{code}")
    test_code = extract_code_block(response, "python")

    # Count test functions
    test_count = len(re.findall(r'def test_', test_code))

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "test_code": test_code,
        "test_count": test_count,
        "framework": framework,
        "xp": xp_result
    }


async def measure_coverage(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: measure_coverage

    Measure and analyze test coverage.

    Parameters:
        code: str - Source code
        test_code: str - Test code

    Returns:
        success: bool
        coverage_percent: float
        uncovered_lines: list
        suggestions: list
    """
    code = params.get("code")
    test_code = params.get("test_code")

    if not code or not test_code:
        return {"success": False, "error": "Missing required parameters: code and test_code"}

    # Placeholder: estimate coverage based on test count vs code complexity
    code_lines = len([l for l in code.split('\n') if l.strip() and not l.strip().startswith('#')])
    test_funcs = len(re.findall(r'def test_', test_code))

    # Simple heuristic: each test covers ~10 lines
    estimated_coverage = min(100, (test_funcs * 10 / max(code_lines, 1)) * 100)

    xp_input = {
        "executed": True,
        "coverage_percent": estimated_coverage,
        "is_novel": True
    }
    xp_result = _calculate_waitress_xp(xp_input)

    return {
        "success": True,
        "coverage_percent": round(estimated_coverage, 1),
        "uncovered_lines": [],  # Placeholder
        "suggestions": [
            "Add tests for edge cases",
            "Test error handling paths"
        ] if estimated_coverage < 80 else [],
        "xp": xp_result
    }


# ============================================================================
# PLANET 2: DEBUGGING
# ============================================================================

async def debug_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: debug_code

    Find and fix bugs systematically.

    Parameters:
        code: str - Code with bug
        error_message: str - Error message or description
        context: str - Additional context

    Returns:
        success: bool
        analysis: str - Bug analysis
        fix: str - Suggested fix
        fixed_code: str - Corrected code
    """
    code = params.get("code")
    error_message = params.get("error_message", "")
    context = params.get("context", "")

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    system_prompt = """You are an expert debugger.
Analyze the code and error to find the bug.
Provide:
1. What the bug is
2. Why it happens
3. How to fix it
4. The corrected code"""

    user_prompt = f"""Code:
```
{code}
```

Error: {error_message}
Context: {context}"""

    response = await call_model_for_code(qube, system_prompt, user_prompt)
    fixed_code = extract_code_block(response, "python")

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "analysis": response[:500],
        "fix": "See analysis",
        "fixed_code": fixed_code,
        "xp": xp_result
    }


async def analyze_error(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: analyze_error

    Understand WHAT went wrong from error messages.

    Parameters:
        error_message: str - The error/exception message
        traceback: str - Full traceback (optional)
        language: str - Programming language

    Returns:
        success: bool
        error_type: str
        explanation: str
        likely_causes: list
    """
    error_message = params.get("error_message")
    traceback = params.get("traceback", "")
    language = params.get("language", "python")

    if not error_message:
        return {"success": False, "error": "Missing required parameter: error_message"}

    system_prompt = f"""You are an expert {language} debugger.
Analyze the error message and explain:
1. What type of error this is
2. What it means in plain English
3. The most likely causes"""

    user_prompt = f"Error: {error_message}\nTraceback: {traceback}"

    response = await call_model_for_code(qube, system_prompt, user_prompt)

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "error_type": error_message.split(':')[0] if ':' in error_message else "Unknown",
        "explanation": response[:500],
        "likely_causes": [
            "See explanation above"
        ],
        "xp": xp_result
    }


async def find_root_cause(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: find_root_cause

    Understand WHY the error happened (deeper analysis).

    Parameters:
        code: str - Relevant code
        error_message: str - Error message
        context: str - What was being attempted

    Returns:
        success: bool
        root_cause: str
        chain_of_events: list
        prevention: str
    """
    code = params.get("code", "")
    error_message = params.get("error_message")
    context = params.get("context", "")

    if not error_message:
        return {"success": False, "error": "Missing required parameter: error_message"}

    system_prompt = """You are a root cause analysis expert.
Go beyond the immediate error to find the underlying cause.
Provide:
1. The root cause (not just the symptom)
2. The chain of events that led to the error
3. How to prevent this class of errors in the future"""

    user_prompt = f"""Error: {error_message}
Context: {context}
Code:
```
{code}
```"""

    response = await call_model_for_code(qube, system_prompt, user_prompt)

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "root_cause": response[:300],
        "chain_of_events": ["See analysis"],
        "prevention": "Apply proper validation and error handling",
        "xp": xp_result
    }


# ============================================================================
# PLANET 3: ALGORITHMS
# ============================================================================

async def benchmark_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: benchmark_code

    Measure and compare code performance.

    Parameters:
        code: str - Code to benchmark
        iterations: int - Number of iterations (default: 1000)
        compare_to: str - Alternative implementation (optional)

    Returns:
        success: bool
        execution_time_ms: float
        memory_kb: int
        comparison: dict (if compare_to provided)
    """
    code = params.get("code")
    iterations = params.get("iterations", 1000)
    compare_to = params.get("compare_to")

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    # Placeholder benchmark results
    result = {
        "success": True,
        "execution_time_ms": 42.5,
        "memory_kb": 1024,
        "iterations": iterations,
        "xp": _calculate_waitress_xp({"executed": True, "performance_ok": True, "is_novel": True})
    }

    if compare_to:
        result["comparison"] = {
            "original_ms": 42.5,
            "alternative_ms": 38.2,
            "speedup": "1.11x faster"
        }

    return result


async def analyze_complexity(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: analyze_complexity

    Analyze Big O time and space complexity.

    Parameters:
        code: str - Code to analyze
        function_name: str - Specific function (optional)

    Returns:
        success: bool
        time_complexity: str
        space_complexity: str
        explanation: str
    """
    code = params.get("code")
    function_name = params.get("function_name", "")

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    system_prompt = """You are an algorithms expert.
Analyze the code and determine:
1. Time complexity (Big O)
2. Space complexity (Big O)
3. Brief explanation of why"""

    user_prompt = f"""Code:
```
{code}
```
{"Focus on function: " + function_name if function_name else ""}"""

    response = await call_model_for_code(qube, system_prompt, user_prompt)

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "time_complexity": "O(n)",  # Would be extracted from response
        "space_complexity": "O(1)",
        "explanation": response[:400],
        "xp": xp_result
    }


async def tune_performance(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: tune_performance

    Optimize code for better performance.

    Parameters:
        code: str - Code to optimize
        target: str - What to optimize for (speed/memory)
        constraints: str - Any constraints

    Returns:
        success: bool
        optimized_code: str
        improvements: list
        expected_speedup: str
    """
    code = params.get("code")
    target = params.get("target", "speed")
    constraints = params.get("constraints", "")

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    system_prompt = f"""You are a performance optimization expert.
Optimize the code for {target}.
{"Constraints: " + constraints if constraints else ""}
Explain each optimization you make."""

    user_prompt = f"Code to optimize:\n```\n{code}\n```"

    response = await call_model_for_code(qube, system_prompt, user_prompt)
    optimized_code = extract_code_block(response, "python")

    xp_result = _calculate_waitress_xp({"executed": True, "performance_ok": True, "is_novel": True})

    return {
        "success": True,
        "optimized_code": optimized_code,
        "improvements": ["See optimized code"],
        "expected_speedup": "2-3x (estimated)",
        "xp": xp_result
    }


# ============================================================================
# PLANET 4: HACKING (Security)
# ============================================================================

async def security_scan(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: security_scan

    Scan code for security vulnerabilities.

    Parameters:
        code: str - Code to scan
        language: str - Programming language
        check_types: list - Types of vulnerabilities to check

    Returns:
        success: bool
        vulnerabilities: list
        severity_summary: dict
        recommendations: list
    """
    code = params.get("code")
    language = params.get("language", "python")

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    # Check for common vulnerability patterns
    vulnerabilities = []

    danger_patterns = {
        "python": [
            (r'eval\s*\(', "HIGH", "Use of eval() - code injection risk"),
            (r'exec\s*\(', "HIGH", "Use of exec() - code injection risk"),
            (r'os\.system\s*\(', "MEDIUM", "Use of os.system() - command injection risk"),
            (r'pickle\.loads?\s*\(', "HIGH", "Pickle deserialization - arbitrary code execution"),
            (r'input\s*\(', "LOW", "Direct input() - validate before use"),
        ],
        "javascript": [
            (r'eval\s*\(', "HIGH", "Use of eval() - code injection risk"),
            (r'innerHTML\s*=', "MEDIUM", "innerHTML assignment - XSS risk"),
            (r'document\.write\s*\(', "MEDIUM", "document.write() - XSS risk"),
        ]
    }

    patterns = danger_patterns.get(language, [])
    for pattern, severity, message in patterns:
        if re.search(pattern, code):
            vulnerabilities.append({
                "severity": severity,
                "issue": message,
                "pattern": pattern
            })

    severity_summary = {
        "high": len([v for v in vulnerabilities if v["severity"] == "HIGH"]),
        "medium": len([v for v in vulnerabilities if v["severity"] == "MEDIUM"]),
        "low": len([v for v in vulnerabilities if v["severity"] == "LOW"])
    }

    xp_input = {
        "executed": True,
        "vulnerabilities": vulnerabilities,
        "is_novel": True
    }
    xp_result = _calculate_waitress_xp(xp_input)

    return {
        "success": True,
        "vulnerabilities": vulnerabilities,
        "severity_summary": severity_summary,
        "recommendations": [
            "Review all HIGH severity issues",
            "Consider input validation",
            "Use parameterized queries for database operations"
        ] if vulnerabilities else ["No critical vulnerabilities found"],
        "xp": xp_result
    }


async def find_exploit(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: find_exploit

    Discover exploitable vulnerabilities in code.

    Parameters:
        code: str - Code to analyze
        attack_surface: str - What to focus on (input, auth, etc.)

    Returns:
        success: bool
        exploits_found: list
        proof_of_concept: str
        remediation: str
    """
    code = params.get("code")
    attack_surface = params.get("attack_surface", "general")

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    system_prompt = """You are a security researcher (ethical hacker).
Analyze the code for exploitable vulnerabilities.
Focus on: input validation, authentication, authorization, injection attacks.
For each vulnerability found, provide:
1. Description
2. Proof of concept (safe example)
3. How to fix it"""

    user_prompt = f"""Code to analyze:
```
{code}
```
Focus area: {attack_surface}"""

    response = await call_model_for_code(qube, system_prompt, user_prompt)

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "exploits_found": [response[:300]],
        "proof_of_concept": "See analysis",
        "remediation": "Apply recommended fixes",
        "xp": xp_result
    }


async def reverse_engineer(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: reverse_engineer

    Understand systems by taking them apart.

    Parameters:
        code: str - Code/binary to analyze
        objective: str - What to understand

    Returns:
        success: bool
        structure: dict
        logic_flow: str
        key_functions: list
    """
    code = params.get("code")
    objective = params.get("objective", "understand the overall logic")

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    system_prompt = """You are a reverse engineering expert.
Analyze the code to understand how it works:
1. Overall structure and architecture
2. Key functions and their purposes
3. Data flow and logic
4. Any interesting or suspicious patterns"""

    user_prompt = f"""Code to analyze:
```
{code}
```
Objective: {objective}"""

    response = await call_model_for_code(qube, system_prompt, user_prompt)

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "structure": {"summary": response[:300]},
        "logic_flow": "See analysis",
        "key_functions": [],
        "xp": xp_result
    }


async def pen_test(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: pen_test

    Systematic penetration testing methodology.

    Parameters:
        target: str - What to test (code, API, system)
        scope: str - Testing scope
        methodology: str - Methodology (OWASP, PTES, etc.)

    Returns:
        success: bool
        test_plan: list
        findings: list
        risk_rating: str
    """
    target = params.get("target")
    scope = params.get("scope", "full")
    methodology = params.get("methodology", "OWASP")

    if not target:
        return {"success": False, "error": "Missing required parameter: target"}

    system_prompt = f"""You are a penetration testing expert using {methodology} methodology.
Create a test plan and identify potential vulnerabilities:
1. Reconnaissance steps
2. Test cases to execute
3. Potential vulnerability areas
4. Recommended testing tools"""

    user_prompt = f"Target: {target}\nScope: {scope}"

    response = await call_model_for_code(qube, system_prompt, user_prompt)

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "test_plan": [response[:400]],
        "findings": [],  # Would be populated during actual testing
        "risk_rating": "Medium",
        "methodology": methodology,
        "xp": xp_result
    }


# ============================================================================
# PLANET 5: CODE REVIEW
# ============================================================================

async def review_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planet Tool: review_code

    Critique and improve code quality.

    Parameters:
        code: str - Code to review
        focus: str - What to focus on (style, performance, security)
        standards: str - Coding standards to apply

    Returns:
        success: bool
        overall_rating: str
        issues: list
        suggestions: list
        praise: list
    """
    code = params.get("code")
    focus = params.get("focus", "general")
    standards = params.get("standards", "PEP 8")

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    system_prompt = f"""You are a senior code reviewer.
Review the code for quality, focusing on: {focus}
Apply {standards} standards.
Provide:
1. Overall quality rating (Excellent/Good/Needs Work/Poor)
2. Specific issues found
3. Suggestions for improvement
4. What's done well (be positive too!)"""

    user_prompt = f"Code to review:\n```\n{code}\n```"

    response = await call_model_for_code(qube, system_prompt, user_prompt)

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "overall_rating": "Good",  # Would be extracted from response
        "issues": [response[:300]],
        "suggestions": ["See review comments"],
        "praise": ["Code is well-structured"],
        "xp": xp_result
    }


async def refactor_code(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: refactor_code

    Improve code structure without changing behavior.

    Parameters:
        code: str - Code to refactor
        goal: str - Refactoring goal (readability, DRY, SOLID)
        preserve: str - What to preserve

    Returns:
        success: bool
        refactored_code: str
        changes_made: list
        before_after: dict
    """
    code = params.get("code")
    goal = params.get("goal", "improve readability")
    preserve = params.get("preserve", "all functionality")

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    system_prompt = f"""You are a refactoring expert.
Refactor the code to {goal}.
Preserve: {preserve}
Apply clean code principles and design patterns where appropriate.
Explain each change you make."""

    user_prompt = f"Code to refactor:\n```\n{code}\n```"

    response = await call_model_for_code(qube, system_prompt, user_prompt)
    refactored_code = extract_code_block(response, "python")

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "refactored_code": refactored_code,
        "changes_made": ["See refactored code"],
        "before_after": {
            "lines_before": len(code.split('\n')),
            "lines_after": len(refactored_code.split('\n'))
        },
        "xp": xp_result
    }


async def git_operation(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: git_operation

    Manage code changes with git.

    Parameters:
        operation: str - Git operation (commit, branch, merge, etc.)
        message: str - Commit message (for commit)
        args: dict - Additional arguments

    Returns:
        success: bool
        output: str
        suggestion: str
    """
    operation = params.get("operation")
    message = params.get("message", "")
    args = params.get("args", {})

    if not operation:
        return {"success": False, "error": "Missing required parameter: operation"}

    # Placeholder - would integrate with actual git
    valid_operations = ["status", "commit", "branch", "merge", "rebase", "log", "diff"]

    if operation not in valid_operations:
        return {
            "success": False,
            "error": f"Unknown operation: {operation}. Valid: {valid_operations}"
        }

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "output": f"[Placeholder] git {operation} executed successfully",
        "suggestion": f"Consider using 'git {operation} --help' for more options",
        "xp": xp_result
    }


async def generate_docs(qube, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Moon Tool: generate_docs

    Generate documentation for code.

    Parameters:
        code: str - Code to document
        style: str - Documentation style (docstring, markdown, JSDoc)
        include: list - What to include (params, returns, examples)

    Returns:
        success: bool
        documentation: str
        format: str
    """
    code = params.get("code")
    style = params.get("style", "docstring")
    include = params.get("include", ["params", "returns", "examples"])

    if not code:
        return {"success": False, "error": "Missing required parameter: code"}

    system_prompt = f"""You are a technical documentation expert.
Generate {style} style documentation for the code.
Include: {', '.join(include)}
Be clear, concise, and helpful."""

    user_prompt = f"Code to document:\n```\n{code}\n```"

    response = await call_model_for_code(qube, system_prompt, user_prompt)

    xp_result = _calculate_waitress_xp({"executed": True, "is_novel": True})

    return {
        "success": True,
        "documentation": response,
        "format": style,
        "xp": xp_result
    }


# ============================================================================
# EXPORT HANDLERS
# ============================================================================

CODING_TOOL_HANDLERS = {
    # Sun
    "develop_code": develop_code,

    # Planet 1: Testing
    "run_tests": run_tests,
    "write_unit_test": write_unit_test,
    "measure_coverage": measure_coverage,

    # Planet 2: Debugging
    "debug_code": debug_code,
    "analyze_error": analyze_error,
    "find_root_cause": find_root_cause,

    # Planet 3: Algorithms
    "benchmark_code": benchmark_code,
    "analyze_complexity": analyze_complexity,
    "tune_performance": tune_performance,

    # Planet 4: Hacking
    "security_scan": security_scan,
    "find_exploit": find_exploit,
    "reverse_engineer": reverse_engineer,
    "pen_test": pen_test,

    # Planet 5: Code Review
    "review_code": review_code,
    "refactor_code": refactor_code,
    "git_operation": git_operation,
    "generate_docs": generate_docs,
}
