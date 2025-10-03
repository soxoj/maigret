#!/usr/bin/env python3
"""Quality score calculator for workflow improvements."""
import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run pytest and return pass/fail status."""
    result = subprocess.run(
        ['python3', '-m', 'pytest', '.github/tests/test_python_publish.py', '-v', '--tb=no'],
        cwd=Path(__file__).parent.parent.parent,
        capture_output=True,
        text=True
    )
    
    # Count passed tests
    output = result.stdout + result.stderr
    if 'passed' in output:
        # Extract "X passed"
        parts = output.split('passed')[0].split()
        if parts:
            try:
                passed = int(parts[-1])
                return passed, result.returncode == 0
            except ValueError:
                pass
    
    return 0, False


def validate_yaml():
    """Validate YAML syntax."""
    result = subprocess.run(
        ['python3', '.github/tests/validate_workflow.py'],
        cwd=Path(__file__).parent.parent.parent,
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def calculate_complexity():
    """Calculate code complexity (simplified)."""
    workflow_path = Path(__file__).parent.parent / 'workflows' / 'python-publish.yml'
    with open(workflow_path) as f:
        lines = f.readlines()
    
    # Count steps (complexity indicator)
    steps = sum(1 for line in lines if line.strip().startswith('- name:') or line.strip().startswith('- uses:'))
    
    # Normalize: 5-10 steps is good, score inversely with complexity
    # Lower step count (focused workflow) = better score
    if steps <= 8:
        return 1.0  # Perfect
    elif steps <= 12:
        return 0.9  # Good
    else:
        return max(0.5, 1.0 - (steps - 12) * 0.05)  # Decreasing


def calculate_quality_score():
    """Calculate overall quality score."""
    print("=" * 60)
    print("QUALITY SCORE REPORT - Issue #2110")
    print("=" * 60)
    print()
    
    # Run tests
    print("Running tests...")
    num_tests, tests_pass = run_tests()
    print(f"  Tests: {num_tests} passed")
    print(f"  Status: {'PASS' if tests_pass else 'FAIL'}")
    print()
    
    # Validate YAML
    print("Validating YAML...")
    yaml_valid = validate_yaml()
    print(f"  YAML validation: {'PASS' if yaml_valid else 'FAIL'}")
    print()
    
    # Calculate metrics
    tests_passing_score = 1.0 if tests_pass and num_tests >= 20 else (num_tests / 20.0)
    yaml_score = 1.0 if yaml_valid else 0.0
    complexity_score = calculate_complexity()
    
    # Quality scoring weights
    weights = {
        'tests_passing': 0.40,      # 40% - Tests are critical
        'yaml_valid': 0.30,          # 30% - Must be valid YAML
        'complexity': 0.15,          # 15% - Code quality
        'best_practices': 0.15,      # 15% - Following conventions
    }
    
    # Best practices check (simplified)
    workflow_path = Path(__file__).parent.parent / 'workflows' / 'python-publish.yml'
    with open(workflow_path) as f:
        content = f.read()
    
    best_practices_score = 0.0
    checks = {
        'Uses trusted publishing': 'id-token: write' in content,
        'No setup.py references': 'setup.py' not in content,
        'Uses modern uv tool': 'setup-uv' in content,
        'Has artifact upload': 'upload-artifact' in content,
        'Proper trigger': "'on':" in content or 'on:' in content,
    }
    
    print("Best Practices Check:")
    for check, result in checks.items():
        print(f"  {check}: {'✓' if result else '✗'}")
        if result:
            best_practices_score += 1.0 / len(checks)
    print()
    
    # Calculate weighted score
    score = (
        tests_passing_score * weights['tests_passing'] +
        yaml_score * weights['yaml_valid'] +
        complexity_score * weights['complexity'] +
        best_practices_score * weights['best_practices']
    )
    
    print("Metrics:")
    print(f"  Tests passing: {tests_passing_score:.2f} (weight: {weights['tests_passing']})")
    print(f"  YAML valid: {yaml_score:.2f} (weight: {weights['yaml_valid']})")
    print(f"  Complexity: {complexity_score:.2f} (weight: {weights['complexity']})")
    print(f"  Best practices: {best_practices_score:.2f} (weight: {weights['best_practices']})")
    print()
    print("=" * 60)
    print(f"OVERALL QUALITY SCORE: {score:.2f}/1.00")
    print("=" * 60)
    print()
    
    # Determine status
    if score >= 0.90:
        print("Status: EXCELLENT ✓✓✓")
        print("Recommendation: Ready for production")
    elif score >= 0.85:
        print("Status: GOOD ✓✓")
        print("Recommendation: Ready for merge")
    elif score >= 0.70:
        print("Status: ACCEPTABLE ✓")
        print("Recommendation: Consider improvements")
    else:
        print("Status: NEEDS WORK ✗")
        print("Recommendation: Additional fixes required")
    print()
    
    return score


if __name__ == '__main__':
    score = calculate_quality_score()
    sys.exit(0 if score >= 0.85 else 1)
