"""Code quality enforcement — zero-tolerance tests for critical code hygiene rules.

Run with:  pytest tests/enforcement/test_code_quality.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

from .conftest import EXCLUDED_DIRS, PACKAGE_DIR, ROOT, SCRIPTS_DIR

_SCAN_DIRS = [PACKAGE_DIR, SCRIPTS_DIR]


def _production_files() -> list[Path]:
    """All .py files in package + scripts, excluding legacy and caches."""
    files: list[Path] = []
    for scan_dir in _SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for f in sorted(scan_dir.rglob("*.py")):
            if any(part in EXCLUDED_DIRS for part in f.parts):
                continue
            files.append(f)
    return files


def _rel(path: Path) -> str:
    """Return path relative to project root."""
    return str(path.relative_to(ROOT))


class TestNoBareExcepts:
    """Bare 'except:' hides all errors — forbidden in production code."""

    _PATTERN = re.compile(r"^\s*except\s*:")

    def test_no_bare_except(self):
        """No bare except: allowed in package or scripts."""
        violations: list[str] = []
        for f in _production_files():
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if self._PATTERN.match(line):
                    violations.append(f"  {_rel(f)}:{i}: {line.strip()}")
        assert not violations, (
            f"Bare 'except:' is forbidden ({len(violations)} found):\n"
            + "\n".join(violations[:20])
        )


class TestNoSysPathHacks:
    """sys.path manipulation breaks portability."""

    _PATTERN = re.compile(r"sys\.path\.(insert|append)\b")
    THRESHOLD = 0

    def test_sys_path_count_within_ratchet(self):
        """sys.path hack count must not exceed ratchet threshold."""
        violations: list[str] = []
        for f in _production_files():
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if self._PATTERN.search(line) and not line.lstrip().startswith("#"):
                    violations.append(f"  {_rel(f)}:{i}: {line.strip()}")
        assert len(violations) <= self.THRESHOLD, (
            f"sys.path hacks ({len(violations)}) exceed ratchet threshold "
            f"({self.THRESHOLD}):\n" + "\n".join(violations[:20])
        )


class TestNoSubprocessShell:
    """subprocess with shell=True is a command injection vector."""

    _PATTERN = re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True")

    def test_no_subprocess_shell(self):
        """No subprocess shell=True in production code."""
        violations: list[str] = []
        for f in _production_files():
            source = f.read_text(encoding="utf-8")
            for i, line in enumerate(source.splitlines(), 1):
                if self._PATTERN.search(line) and not line.lstrip().startswith("#"):
                    violations.append(f"  {_rel(f)}:{i}: {line.strip()}")
        assert not violations, (
            f"subprocess shell=True is forbidden ({len(violations)} found):\n"
            + "\n".join(violations[:20])
        )


class TestNoEvalExec:
    """eval() and exec() are forbidden — arbitrary code execution risk."""

    _PATTERN = re.compile(r"\b(eval|exec)\s*\(")

    def test_no_eval_exec(self):
        """No eval()/exec() in production code."""
        violations: list[str] = []
        for f in _production_files():
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if self._PATTERN.search(line) and not line.lstrip().startswith("#"):
                    violations.append(f"  {_rel(f)}:{i}: {line.strip()}")
        assert not violations, (
            f"eval()/exec() forbidden ({len(violations)} found):\n"
            + "\n".join(violations[:20])
        )
