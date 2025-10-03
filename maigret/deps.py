"""
Dependency checking utilities for Maigret
"""
from typing import Optional, Any


class DependencyError(ImportError):
    """Raised when a required dependency is not installed"""
    pass


def check_socid_extractor_installed() -> bool:
    """
    Check if socid_extractor module is available

    Returns:
        bool: True if socid_extractor is installed, False otherwise
    """
    try:
        import socid_extractor  # noqa: F401
        return True
    except ImportError:
        return False


def get_socid_install_message() -> str:
    """
    Get installation instructions for socid_extractor

    Returns:
        str: User-friendly error message with installation instructions
    """
    return """
socid_extractor module is not properly installed.

This is a required dependency for Maigret to extract user IDs from web pages.

Please install it using one of the following methods:

  Using pip:
    pip install socid-extractor

  Using poetry:
    poetry install

  Using pip with specific version:
    pip install socid-extractor>=0.0.27

If you installed Maigret from source, make sure to install all dependencies:
    pip install -e .

For more information, visit: https://github.com/soxoj/socid-extractor
"""


def require_socid_extractor() -> None:
    """
    Ensure socid_extractor is installed, raise DependencyError if not

    Raises:
        DependencyError: If socid_extractor is not installed
    """
    if not check_socid_extractor_installed():
        raise DependencyError(get_socid_install_message())


def import_socid_extractor():
    """
    Safely import socid_extractor module

    Returns:
        module: socid_extractor module if available

    Raises:
        DependencyError: If socid_extractor is not installed
    """
    try:
        import socid_extractor
        return socid_extractor
    except ImportError:
        raise DependencyError(get_socid_install_message())


def safe_import(module_name: str, error_message: Optional[str] = None) -> Any:
    """
    Safely import a module with a custom error message

    Args:
        module_name: Name of the module to import
        error_message: Custom error message if import fails

    Returns:
        The imported module

    Raises:
        DependencyError: If the module cannot be imported
    """
    try:
        return __import__(module_name)
    except ImportError:
        if error_message:
            raise DependencyError(error_message)
        raise DependencyError(
            f"Required module '{module_name}' is not installed"
        )
