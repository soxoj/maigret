"""Tests for python-publish.yml workflow validation."""
import yaml
import pytest
from pathlib import Path


class TestPythonPublishWorkflow:
    """Test suite for python-publish.yml workflow."""

    @pytest.fixture
    def workflow_file(self):
        """Load the workflow file."""
        workflow_path = Path(__file__).parent.parent / 'workflows' / 'python-publish.yml'
        with open(workflow_path, 'r') as f:
            return yaml.safe_load(f)

    def test_workflow_file_exists(self):
        """Test that the workflow file exists."""
        workflow_path = Path(__file__).parent.parent / 'workflows' / 'python-publish.yml'
        assert workflow_path.exists(), "python-publish.yml workflow file should exist"

    def test_yaml_syntax_valid(self, workflow_file):
        """Test that the YAML syntax is valid."""
        assert workflow_file is not None, "Workflow file should be valid YAML"
        assert isinstance(workflow_file, dict), "Workflow should be a dictionary"

    def test_workflow_name(self, workflow_file):
        """Test that workflow has a descriptive name."""
        assert 'name' in workflow_file, "Workflow should have a name"
        assert 'PyPI' in workflow_file['name'], "Workflow name should mention PyPI"

    def test_workflow_triggers(self, workflow_file):
        """Test that workflow triggers are correct."""
        assert 'on' in workflow_file, "Workflow should have triggers"
        assert 'release' in workflow_file['on'], "Workflow should trigger on release"
        assert workflow_file['on']['release']['types'] == ['created'], \
            "Workflow should trigger on release created event"

    def test_no_duplicate_triggers(self, workflow_file):
        """Test that workflow doesn't have duplicate triggers."""
        # Should only trigger on release, not also on tag push
        assert 'push' not in workflow_file['on'], \
            "Workflow should not trigger on push to avoid duplicate runs"

    def test_permissions(self, workflow_file):
        """Test that permissions are correctly set for trusted publishing."""
        assert 'permissions' in workflow_file, "Workflow should define permissions"
        assert workflow_file['permissions']['id-token'] == 'write', \
            "Should have id-token write permission for trusted publishing"
        assert workflow_file['permissions']['contents'] == 'read', \
            "Should have contents read permission"

    def test_job_exists(self, workflow_file):
        """Test that build-and-publish job exists."""
        assert 'jobs' in workflow_file, "Workflow should have jobs"
        assert 'build-and-publish' in workflow_file['jobs'], \
            "Should have build-and-publish job"

    def test_runs_on_ubuntu(self, workflow_file):
        """Test that job runs on ubuntu-latest."""
        job = workflow_file['jobs']['build-and-publish']
        assert job['runs-on'] == 'ubuntu-latest', \
            "Job should run on ubuntu-latest for consistency"

    def test_checkout_step(self, workflow_file):
        """Test that repository is checked out."""
        steps = workflow_file['jobs']['build-and-publish']['steps']
        checkout_steps = [s for s in steps if 'checkout' in s.get('uses', '').lower()]
        assert len(checkout_steps) > 0, "Should have a checkout step"
        assert 'actions/checkout@v4' in checkout_steps[0]['uses'], \
            "Should use actions/checkout@v4"

    def test_python_setup(self, workflow_file):
        """Test that Python is set up with correct version."""
        steps = workflow_file['jobs']['build-and-publish']['steps']
        python_steps = [s for s in steps if 'setup-python' in s.get('uses', '').lower()]
        assert len(python_steps) > 0, "Should have a Python setup step"
        
        python_step = python_steps[0]
        assert 'actions/setup-python@v5' in python_step['uses'], \
            "Should use latest setup-python action"
        assert 'with' in python_step, "Python setup should have configuration"
        assert 'python-version' in python_step['with'], \
            "Should specify Python version"
        assert python_step['with']['python-version'] == '3.10', \
            "Should use Python 3.10 (minimum supported version)"

    def test_uv_setup(self, workflow_file):
        """Test that uv is set up correctly."""
        steps = workflow_file['jobs']['build-and-publish']['steps']
        uv_steps = [s for s in steps if 'setup-uv' in s.get('uses', '').lower()]
        assert len(uv_steps) > 0, "Should have a uv setup step"
        
        uv_step = uv_steps[0]
        assert 'astral-sh/setup-uv@v5' in uv_step['uses'], \
            "Should use setup-uv@v5"

    def test_build_step(self, workflow_file):
        """Test that package is built with uv."""
        steps = workflow_file['jobs']['build-and-publish']['steps']
        build_steps = [s for s in steps if s.get('run', '').strip() == 'uv build']
        assert len(build_steps) > 0, "Should have a uv build step"

    def test_verify_artifacts_step(self, workflow_file):
        """Test that build artifacts are verified."""
        steps = workflow_file['jobs']['build-and-publish']['steps']
        verify_steps = [s for s in steps if 'verify' in s.get('name', '').lower()]
        assert len(verify_steps) > 0, "Should verify build artifacts"

    def test_upload_artifacts_step(self, workflow_file):
        """Test that artifacts are uploaded for debugging."""
        steps = workflow_file['jobs']['build-and-publish']['steps']
        upload_steps = [s for s in steps if 'upload-artifact' in s.get('uses', '').lower()]
        assert len(upload_steps) > 0, "Should upload build artifacts"
        
        upload_step = upload_steps[0]
        assert 'actions/upload-artifact@v4' in upload_step['uses'], \
            "Should use upload-artifact@v4"
        assert upload_step['with']['path'] == 'dist/', \
            "Should upload dist/ directory"

    def test_pypi_publish_step(self, workflow_file):
        """Test that PyPI publish step is correctly configured."""
        steps = workflow_file['jobs']['build-and-publish']['steps']
        publish_steps = [s for s in steps if 'pypi-publish' in s.get('uses', '').lower()]
        assert len(publish_steps) > 0, "Should have PyPI publish step"
        
        publish_step = publish_steps[0]
        assert 'pypa/gh-action-pypi-publish@release/v1' in publish_step['uses'], \
            "Should use official PyPI publish action"
        assert 'with' in publish_step, "Publish step should have configuration"
        assert publish_step['with']['packages-dir'] == 'dist/', \
            "Should publish from dist/ directory"

    def test_step_order(self, workflow_file):
        """Test that steps are in correct order."""
        steps = workflow_file['jobs']['build-and-publish']['steps']
        
        # Get indices of key steps
        checkout_idx = next((i for i, s in enumerate(steps) if 'checkout' in s.get('uses', '').lower()), -1)
        build_idx = next((i for i, s in enumerate(steps) if s.get('run', '').strip() == 'uv build'), -1)
        publish_idx = next((i for i, s in enumerate(steps) if 'pypi-publish' in s.get('uses', '').lower()), -1)
        
        # Verify indices are valid
        assert checkout_idx == 0, "Checkout should be first step"
        assert build_idx > 0, "Build step should exist after checkout"
        assert publish_idx > build_idx, "Publish should come after build"

    def test_no_setup_py_references(self, workflow_file):
        """Test that workflow doesn't reference setup.py."""
        workflow_str = yaml.dump(workflow_file)
        assert 'setup.py' not in workflow_str, \
            "Workflow should not reference setup.py (project uses Poetry)"

    def test_uses_trusted_publishing(self, workflow_file):
        """Test that workflow uses OIDC trusted publishing."""
        # Check permissions for OIDC
        assert workflow_file['permissions']['id-token'] == 'write', \
            "Should use OIDC trusted publishing with id-token permission"
        
        # Check no password/token in publish step
        steps = workflow_file['jobs']['build-and-publish']['steps']
        publish_steps = [s for s in steps if 'pypi-publish' in s.get('uses', '').lower()]
        publish_step = publish_steps[0]
        
        assert 'password' not in publish_step.get('with', {}), \
            "Should not use password (use trusted publishing)"
        assert 'token' not in publish_step.get('with', {}), \
            "Should not use token (use trusted publishing)"


class TestWorkflowIntegration:
    """Integration tests for workflow functionality."""

    def test_pyproject_toml_compatible(self):
        """Test that project has pyproject.toml for uv build."""
        pyproject_path = Path(__file__).parent.parent.parent / 'pyproject.toml'
        assert pyproject_path.exists(), \
            "pyproject.toml must exist for uv build to work"
        
        with open(pyproject_path, 'r') as f:
            content = f.read()
            assert '[build-system]' in content, \
                "pyproject.toml must have build-system section"
            assert 'poetry-core' in content, \
                "Should use poetry-core as build backend"

    def test_no_setup_py_exists(self):
        """Test that setup.py doesn't exist (confirms migration to Poetry)."""
        setup_path = Path(__file__).parent.parent.parent / 'setup.py'
        assert not setup_path.exists(), \
            "setup.py should not exist (migrated to Poetry/pyproject.toml)"
