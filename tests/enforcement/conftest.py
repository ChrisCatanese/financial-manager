"""Shared fixtures for enforcement tests."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent

PACKAGE_DIR = ROOT / "src"
SCRIPTS_DIR = ROOT / "scripts"
CONFIG_DIR = ROOT / "config"
INPUTS_DIR = ROOT / "inputs"

DOCS_DIR = ROOT / "docs"
DOCS_REQ = DOCS_DIR / "requirements"
DOCS_STD = DOCS_DIR / "standards"

MATRIX_PATH = DOCS_REQ / "traceability-matrix.md"
BUSINESS_REQ = DOCS_REQ / "business-requirements.md"
FUNCTIONAL_REQ = DOCS_REQ / "functional-requirements.md"
TECHNICAL_REQ = DOCS_REQ / "technical-requirements.md"
MANIFEST = ROOT / "dq-manifest.yaml"

EXCLUDED_DIRS = {"_legacy", ".venv", "__pycache__", "cache", "node_modules"}


@pytest.fixture
def project_root() -> Path:
    """Return the project root."""
    return ROOT
