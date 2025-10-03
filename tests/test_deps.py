"""Test dependency handling"""

import sys
import pytest
from unittest.mock import patch, MagicMock

from maigret.deps import (
    check_socid_extractor_installed,
    get_socid_install_message,
    require_socid_extractor,
    import_socid_extractor,
    DependencyError,
    safe_import,
)


def test_check_socid_extractor_installed_when_available():
    """Test that check returns True when socid_extractor is installed"""
    with patch.dict(sys.modules, {'socid_extractor': MagicMock()}):
        assert check_socid_extractor_installed() is True


def test_check_socid_extractor_installed_when_missing():
    """Test that check returns False when socid_extractor is not installed"""
    # Temporarily remove socid_extractor from sys.modules if it exists
    socid_backup = sys.modules.get('socid_extractor')
    if 'socid_extractor' in sys.modules:
        del sys.modules['socid_extractor']

    # Mock the import to raise ImportError
    with patch('builtins.__import__', side_effect=ImportError("No module named 'socid_extractor'")):
        result = check_socid_extractor_installed()

    # Restore if it was there
    if socid_backup:
        sys.modules['socid_extractor'] = socid_backup

    assert result is False


def test_get_socid_install_message():
    """Test that install message contains helpful information"""
    message = get_socid_install_message()

    assert isinstance(message, str)
    assert len(message) > 0
    assert 'socid-extractor' in message or 'socid_extractor' in message
    assert 'pip install' in message
    assert 'poetry install' in message


def test_require_socid_extractor_when_available():
    """Test that require_socid_extractor doesn't raise when module is available"""
    with patch('maigret.deps.check_socid_extractor_installed', return_value=True):
        # Should not raise
        require_socid_extractor()


def test_require_socid_extractor_when_missing():
    """Test that require_socid_extractor raises DependencyError when module is missing"""
    with patch('maigret.deps.check_socid_extractor_installed', return_value=False):
        with pytest.raises(DependencyError) as exc_info:
            require_socid_extractor()

        error_message = str(exc_info.value)
        assert 'socid' in error_message.lower()
        assert 'pip install' in error_message


def test_import_socid_extractor_when_available():
    """Test that import_socid_extractor returns module when available"""
    mock_module = MagicMock()
    with patch.dict(sys.modules, {'socid_extractor': mock_module}):
        result = import_socid_extractor()
        assert result == mock_module


def test_import_socid_extractor_when_missing():
    """Test that import_socid_extractor raises DependencyError when module is missing"""
    # Remove module if it exists
    socid_backup = sys.modules.get('socid_extractor')
    if 'socid_extractor' in sys.modules:
        del sys.modules['socid_extractor']

    # Create a mock import function
    import builtins
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == 'socid_extractor':
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    with patch('builtins.__import__', side_effect=mock_import):
        with pytest.raises(DependencyError) as exc_info:
            import_socid_extractor()

        error_message = str(exc_info.value)
        assert 'socid' in error_message.lower()

    # Restore if it was there
    if socid_backup:
        sys.modules['socid_extractor'] = socid_backup


def test_safe_import_with_existing_module():
    """Test safe_import with a module that exists"""
    result = safe_import('sys')
    assert result == sys


def test_safe_import_with_missing_module():
    """Test safe_import with a module that doesn't exist"""
    with pytest.raises(DependencyError) as exc_info:
        safe_import('nonexistent_module_xyz123')

    error_message = str(exc_info.value)
    assert 'nonexistent_module_xyz123' in error_message


def test_safe_import_with_custom_error_message():
    """Test safe_import with a custom error message"""
    custom_message = "Custom error: please install this module"

    with pytest.raises(DependencyError) as exc_info:
        safe_import('nonexistent_module_xyz123', error_message=custom_message)

    assert str(exc_info.value) == custom_message


def test_dependency_error_is_import_error():
    """Test that DependencyError is a subclass of ImportError"""
    assert issubclass(DependencyError, ImportError)

    error = DependencyError("test message")
    assert isinstance(error, ImportError)
    assert str(error) == "test message"


def test_install_message_has_all_methods():
    """Test that install message includes all installation methods"""
    message = get_socid_install_message()

    # Should include pip method
    assert 'pip install socid-extractor' in message

    # Should include poetry method
    assert 'poetry install' in message

    # Should include version specification
    assert '0.0.27' in message or '>=' in message

    # Should include helpful context
    assert 'required' in message.lower() or 'dependency' in message.lower()
