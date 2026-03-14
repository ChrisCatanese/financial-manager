"""Shared fixtures for enforcement tests.

Sets ROOT to the project root and exposes path constants
matching the DQ project template's directory layout.

Projects cloned from the template should update PACKAGE_DIR
to point to their actual source package name.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


# ── Path constants ───────────────────────────────────────────────────
# Update PACKAGE_DIR when you create your src/ package.

PACKAGE_DIR = ROOT / "src"
SCRIPTS_DIR = ROOT / "scripts"
CONFIG_DIR = ROOT / "config"
INPUTS_DIR = ROOT / "inputs"
OUTPUTS_DIR = ROOT / "outputs"

DOCS_DIR = ROOT / "docs"
DOCS_REQ = DOCS_DIR / "requirements"
DOCS_STD = DOCS_DIR / "standards"

MATRIX_PATH = DOCS_REQ / "traceability-matrix.md"
BUSINESS_REQ = DOCS_REQ / "business-requirements.md"
FUNCTIONAL_REQ = DOCS_REQ / "functional-requirements.md"
TECHNICAL_REQ = DOCS_REQ / "technical-requirements.md"
MANIFEST = ROOT / "dq-manifest.yaml"

# Directories excluded from enforcement scans
EXCLUDED_DIRS = {"_legacy", ".venv", "__pycache__", "cache", "node_modules"}

# Pipeline entry script(s) — override in project-specific conftest
PIPELINE_SCRIPT: Path | None = None
for _candidate in [
    ROOT / "scripts" / "pipeline.py",
    ROOT / "run_pipeline.sh",
    ROOT / "run_forecast.sh",
    ROOT / "launcher.sh",
]:
    if _candidate.exists():
        PIPELINE_SCRIPT = _candidate
        break


@pytest.fixture
def project_root() -> Path:
    """Return the project root."""
    return ROOT
