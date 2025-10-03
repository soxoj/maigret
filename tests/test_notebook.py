"""Tests for the Google Colab notebook (example.ipynb)."""

import json
import os
from pathlib import Path


def test_notebook_exists():
    """Test that the notebook file exists."""
    notebook_path = Path(__file__).parent.parent / "example.ipynb"
    assert notebook_path.exists(), "example.ipynb should exist in repository root"


def test_notebook_valid_json():
    """Test that the notebook is valid JSON."""
    notebook_path = Path(__file__).parent.parent / "example.ipynb"
    with open(notebook_path, 'r', encoding='utf-8') as f:
        try:
            notebook_data = json.load(f)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Notebook is not valid JSON: {e}")

    assert isinstance(notebook_data, dict), "Notebook should be a JSON object"


def test_notebook_structure():
    """Test that the notebook has the required structure."""
    notebook_path = Path(__file__).parent.parent / "example.ipynb"
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook_data = json.load(f)

    # Check required fields
    assert "nbformat" in notebook_data, "Notebook should have nbformat field"
    assert "cells" in notebook_data, "Notebook should have cells field"
    assert isinstance(notebook_data["cells"], list), "cells should be a list"
    assert len(notebook_data["cells"]) > 0, "Notebook should have at least one cell"


def test_notebook_installation_command():
    """Test that the notebook uses correct Poetry-based installation."""
    notebook_path = Path(__file__).parent.parent / "example.ipynb"
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook_data = json.load(f)

    # Get all source code from cells
    all_source = []
    for cell in notebook_data["cells"]:
        if "source" in cell:
            # Source can be a list of strings or a single string
            source = cell["source"]
            if isinstance(source, list):
                all_source.extend(source)
            else:
                all_source.append(source)

    combined_source = '\n'.join(all_source)

    # Check for git clone command
    assert "git clone" in combined_source, "Notebook should clone the repository"
    assert "soxoj/maigret" in combined_source, "Notebook should clone maigret repository"

    # Check for pip install command (Poetry-compatible)
    assert "pip" in combined_source or "pip3" in combined_source, "Notebook should use pip to install"
    assert "install" in combined_source, "Notebook should have install command"

    # Ensure it uses the directory-based install (not requirements.txt)
    # The correct command is: pip3 install ./maigret/ or pip3 install .
    assert "./maigret" in combined_source or "pip3 install ." in combined_source, \
        "Notebook should use directory-based Poetry installation (pip3 install ./maigret/ or pip3 install .)"


def test_notebook_no_old_requirements_reference():
    """Test that the notebook doesn't reference the old requirements.txt path."""
    notebook_path = Path(__file__).parent.parent / "example.ipynb"
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook_data = json.load(f)

    # Get all source code from cells
    all_source = []
    for cell in notebook_data["cells"]:
        if "source" in cell:
            source = cell["source"]
            if isinstance(source, list):
                all_source.extend(source)
            else:
                all_source.append(source)

    combined_source = '\n'.join(all_source)

    # Check that there's no reference to installing from requirements.txt
    assert "-r requirements.txt" not in combined_source, \
        "Notebook should not use old requirements.txt approach"
    assert "pip install -r" not in combined_source or "docs/requirements.txt" in combined_source, \
        "If using requirements.txt, should reference docs/requirements.txt (but better to use Poetry)"


def test_notebook_maigret_command():
    """Test that the notebook includes maigret usage command."""
    notebook_path = Path(__file__).parent.parent / "example.ipynb"
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook_data = json.load(f)

    # Get all source code from cells
    all_source = []
    for cell in notebook_data["cells"]:
        if "source" in cell:
            source = cell["source"]
            if isinstance(source, list):
                all_source.extend(source)
            else:
                all_source.append(source)

    combined_source = '\n'.join(all_source)

    # Check for maigret command
    assert "maigret" in combined_source.lower(), "Notebook should include maigret command"
