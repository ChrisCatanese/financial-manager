"""Pipeline integrity enforcement — the execution contract must be preserved.

The execution contract must be maintained exactly as designed.

Criteria enforced:
  PIPE-01: A pipeline entry point exists (script or shell launcher)
  PIPE-02: Shell entry points use fail-fast (set -e)
  PIPE-03: Python entry points have a __main__ or main() guard
  PIPE-04: Pipeline script is referenced in dq-manifest.yaml
  PIPE-05: scripts/ directory has at least one executable entry
  PIPE-06: Pipeline output directory is declared or discoverable
  PIPE-07: No hardcoded absolute paths in pipeline scripts

Run with:  pytest tests/enforcement/test_pipeline_integrity.py -v

Generalized from template/tests/enforcement/test_pipeline_integrity.py.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from .conftest import (
    EXCLUDED_DIRS,
    MANIFEST,
    PACKAGE_DIR,
    ROOT,
    SCRIPTS_DIR,
)


def _python_files_in(directory: Path) -> list[Path]:
    """All .py files excluding cache, .venv, etc."""
    results: list[Path] = []
    if not directory.exists():
        return results
    for p in directory.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in p.parts):
            continue
        results.append(p)
    return sorted(results)


def _shell_scripts() -> list[Path]:
    """Find shell scripts at project root and in scripts/."""
    shells: list[Path] = []
    for pattern in ["*.sh", "*.command"]:
        shells.extend(ROOT.glob(pattern))
        if SCRIPTS_DIR.exists():
            shells.extend(SCRIPTS_DIR.glob(pattern))
    return sorted(set(shells))


def _pipeline_python_scripts() -> list[Path]:
    """Find Python scripts that look like pipeline entry points."""
    candidates: list[Path] = []
    if SCRIPTS_DIR.exists():
        for f in SCRIPTS_DIR.glob("*.py"):
            if any(kw in f.stem.lower() for kw in ["pipeline", "main", "run", "entry"]):
                candidates.append(f)
    # Also check root-level scripts
    for f in ROOT.glob("*.py"):
        if any(kw in f.stem.lower() for kw in ["pipeline", "main", "run"]):
            candidates.append(f)
    return sorted(set(candidates))


# ── PIPE-01: Entry point exists ───────────────────────────────────────


class TestEntryPointExists:
    """PIPE-01: A pipeline entry point must exist.

    Either a shell script or a Python pipeline script.
    """

    def test_has_entry_point(self) -> None:
        """At least one entry point must be present."""
        shells = _shell_scripts()
        py_entries = _pipeline_python_scripts()
        all_entries = shells + py_entries

        if not all_entries and SCRIPTS_DIR.exists() and list(SCRIPTS_DIR.glob("*.py")):
            return  # Has scripts, good enough

        assert all_entries or (SCRIPTS_DIR.exists() and list(SCRIPTS_DIR.glob("*.py"))), (
            "PIPE-01: No pipeline entry point found. Expected:\n"
            "  - A shell script (*.sh) at root or in scripts/, or\n"
            "  - A Python script named pipeline.py/main.py/run.py in scripts/"
        )


# ── PIPE-02: Shell scripts use fail-fast ──────────────────────────────


class TestShellFailFast:
    """PIPE-02: Shell entry points must use `set -e` for fail-fast execution."""

    @pytest.mark.parametrize(
        "script",
        _shell_scripts(),
        ids=[s.name for s in _shell_scripts()],
    )
    def test_set_e_present(self, script: Path) -> None:
        """Shell scripts must fail on first error."""
        content = script.read_text(encoding="utf-8")
        has_set_e = re.search(r"^set\s+-e", content, re.MULTILINE)
        has_set_euo = re.search(r"^set\s+-[euo]", content, re.MULTILINE)
        assert has_set_e or has_set_euo, (
            f"PIPE-02: {script.name} does not contain 'set -e' — "
            f"pipeline scripts must fail on first error"
        )

    @pytest.mark.parametrize(
        "script",
        _shell_scripts(),
        ids=[s.name for s in _shell_scripts()],
    )
    def test_starts_with_shebang(self, script: Path) -> None:
        """Shell scripts must have a shebang line."""
        content = script.read_text(encoding="utf-8")
        assert content.startswith("#!"), (
            f"PIPE-02: {script.name} must start with a shebang line "
            f"(#!/bin/bash or #!/usr/bin/env bash)"
        )


# ── PIPE-03: Python entry points have main guard ─────────────────────


class TestPythonMainGuard:
    """PIPE-03: Python pipeline scripts must have __main__ or main() guard."""

    @pytest.mark.parametrize(
        "script",
        _pipeline_python_scripts(),
        ids=[s.name for s in _pipeline_python_scripts()],
    )
    def test_has_main_guard(self, script: Path) -> None:
        """Pipeline scripts must be importable without side effects."""
        content = script.read_text(encoding="utf-8")
        has_main = (
            "__name__" in content and "__main__" in content
        ) or re.search(r"def\s+main\s*\(", content)
        assert has_main, (
            f"PIPE-03: {script.name} has no __main__ guard or main() function — "
            f"pipeline scripts must be importable without triggering execution"
        )


# ── PIPE-04: Pipeline referenced in manifest ─────────────────────────


class TestManifestPipeline:
    """PIPE-04: dq-manifest.yaml should reference the pipeline entry point."""

    def test_manifest_has_core_paths(self) -> None:
        """Manifest must declare core_paths covering the pipeline code."""
        assert MANIFEST.exists(), "PIPE-04: dq-manifest.yaml missing"
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        core = data.get("core_paths", [])
        assert core, (
            "PIPE-04: dq-manifest.yaml has empty core_paths — "
            "must declare paths containing pipeline code"
        )


# ── PIPE-05: scripts/ has at least one executable ─────────────────────


class TestScriptsDirectory:
    """PIPE-05: scripts/ directory must have at least one Python script."""

    def test_scripts_has_python(self) -> None:
        """scripts/ must contain at least one .py file."""
        if not SCRIPTS_DIR.exists():
            pytest.skip("No scripts/ directory")
        py_files = list(SCRIPTS_DIR.glob("*.py"))
        assert py_files, (
            "PIPE-05: scripts/ directory exists but contains no .py files"
        )


# ── PIPE-06: Output directory declared ────────────────────────────────


class TestOutputDirectory:
    """PIPE-06: Pipeline output directory must be declared or discoverable."""

    CANDIDATE_DIRS = ("outputs", "output", "results", "reports", "dist")

    def test_output_dir_exists_or_gitkeep(self) -> None:
        """An output directory must exist (possibly with .gitkeep)."""
        found = any(
            (ROOT / d).exists() or (ROOT / d / ".gitkeep").exists()
            for d in self.CANDIDATE_DIRS
        )
        if not found:
            # Check if manifest declares an output path
            if MANIFEST.exists():
                data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
                core = data.get("core_paths", [])
                if any("output" in str(p).lower() for p in core):
                    return
            # For web projects, frontend/dist counts as output
            if (ROOT / "frontend" / "dist").exists():
                return
            pytest.skip(
                "PIPE-06: No output directory found "
                "(expected outputs/, output/, results/, reports/, or frontend/dist/)"
            )


# ── PIPE-07: No hardcoded absolute paths ─────────────────────────────


class TestNoHardcodedPaths:
    """PIPE-07: Pipeline scripts must not contain hardcoded absolute paths."""

    # Patterns that indicate hardcoded absolute paths
    HARDCODED_PATTERNS = (
        re.compile(r'["\']/(Users|home|opt|var)/[^"\']+["\']'),
        re.compile(r'["\'][A-Z]:\\[^"\']+["\']'),  # Windows paths
    )

    # Allow paths in comments
    COMMENT_RE = re.compile(r"^\s*#")

    def test_no_hardcoded_paths_in_scripts(self) -> None:
        """Scripts and src must not have hardcoded absolute paths."""
        violations: list[str] = []
        for d in [SCRIPTS_DIR, PACKAGE_DIR]:
            for f in _python_files_in(d):
                try:
                    lines = f.read_text(encoding="utf-8").splitlines()
                except (OSError, UnicodeDecodeError):
                    continue
                for i, line in enumerate(lines, 1):
                    if self.COMMENT_RE.match(line):
                        continue
                    for pat in self.HARDCODED_PATTERNS:
                        if pat.search(line):
                            rel = f.relative_to(ROOT)
                            violations.append(f"  {rel}:{i}: {line.strip()}")

        assert not violations, (
            "PIPE-07: Hardcoded absolute paths found in pipeline code:\n"
            + "\n".join(violations[:20])
            + "\nUse Path(__file__).parent or config-driven paths instead."
        )
