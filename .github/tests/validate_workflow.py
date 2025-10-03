#!/usr/bin/env python3
"""Standalone workflow validation script."""
import sys
import yaml
from pathlib import Path


def validate_workflow():
    """Validate the python-publish.yml workflow."""
    workflow_path = Path(__file__).parent.parent.parent / '.github' / 'workflows' / 'python-publish.yml'
    
    print(f"Validating workflow: {workflow_path}")
    
    # Check file exists
    if not workflow_path.exists():
        print("ERROR: Workflow file does not exist")
        return False
    
    # Check YAML syntax
    try:
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ERROR: Invalid YAML syntax: {e}")
        return False
    
    print("✓ YAML syntax is valid")
    
    # Check structure
    errors = []
    
    if 'name' not in workflow:
        errors.append("Missing 'name' field")
    
    if 'on' not in workflow:
        errors.append("Missing 'on' (triggers) field")
    elif 'release' not in workflow['on']:
        errors.append("Missing 'release' trigger")
    
    if 'permissions' not in workflow:
        errors.append("Missing 'permissions' field")
    elif workflow.get('permissions', {}).get('id-token') != 'write':
        errors.append("Missing 'id-token: write' permission for trusted publishing")
    
    if 'jobs' not in workflow:
        errors.append("Missing 'jobs' field")
    elif 'build-and-publish' not in workflow['jobs']:
        errors.append("Missing 'build-and-publish' job")
    else:
        job = workflow['jobs']['build-and-publish']
        steps = job.get('steps', [])
        
        # Check for required steps
        has_checkout = any('checkout' in step.get('uses', '').lower() for step in steps)
        has_uv_setup = any('setup-uv' in step.get('uses', '').lower() for step in steps)
        has_build = any('uv build' in step.get('run', '') for step in steps)
        has_publish = any('pypi-publish' in step.get('uses', '').lower() for step in steps)
        
        if not has_checkout:
            errors.append("Missing checkout step")
        if not has_uv_setup:
            errors.append("Missing uv setup step")
        if not has_build:
            errors.append("Missing 'uv build' step")
        if not has_publish:
            errors.append("Missing PyPI publish step")
    
    # Check for anti-patterns
    workflow_str = yaml.dump(workflow)
    if 'setup.py' in workflow_str:
        errors.append("Workflow references setup.py (should use Poetry/uv)")
    
    if 'push' in workflow.get('on', {}):
        errors.append("WARNING: Workflow triggers on push (may cause duplicate runs)")
    
    if errors:
        print("\nValidation errors:")
        for error in errors:
            print(f"  ✗ {error}")
        return False
    
    print("✓ Workflow structure is valid")
    print("✓ All required steps present")
    print("✓ No anti-patterns detected")
    print("\nWorkflow validation PASSED")
    return True


if __name__ == '__main__':
    success = validate_workflow()
    sys.exit(0 if success else 1)
