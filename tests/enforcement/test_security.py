"""Security enforcement — zero-tolerance for dangerous patterns.

Criteria enforced:
  SEC-01: No pickle.load / pickle.loads in core code
  SEC-02: No subprocess with shell=True
  SEC-03: No eval() / exec() in core code
  SEC-04: No os.system() calls
  SEC-05: No yaml.load() without SafeLoader
  SEC-06: No hardcoded passwords/secrets/API keys
  SEC-07: No connection strings with embedded credentials

Run with:  pytest tests/enforcement/test_security.py -v
"""

from __future__ import annotations

import re
from pathlib import Path

from .conftest import EXCLUDED_DIRS, PACKAGE_DIR, ROOT, SCRIPTS_DIR

_SCAN_DIRS = [PACKAGE_DIR, SCRIPTS_DIR]


def _core_python_files() -> list[Path]:
    """All .py files in src/ and scripts/ excluding caches."""
    results = []
    for scan_dir in _SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for p in scan_dir.rglob("*.py"):
            if any(part in EXCLUDED_DIRS for part in p.parts):
                continue
            results.append(p)
    return sorted(results)


def _scan_for_pattern(
    files: list[Path],
    pattern: re.Pattern,
    *,
    skip_comments: bool = True,
) -> list[tuple[Path, int, str]]:
    """Return (file, line_no, line_text) for all matches."""
    hits: list[tuple[Path, int, str]] = []
    for fpath in files:
        try:
            lines = fpath.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if skip_comments and stripped.startswith("#"):
                continue
            if pattern.search(line):
                hits.append((fpath, i, stripped))
    return hits


def _fmt(hits: list[tuple[Path, int, str]]) -> str:
    """Format hits for assertion messages."""
    return "\n".join(f"  {f.relative_to(ROOT)}:{n}: {t}" for f, n, t in hits)


class TestNoPickle:
    """SEC-01: pickle.load / pickle.loads must never appear in core code."""

    _PATTERN = re.compile(r"\bpickle\.(load|loads)\s*\(")

    def test_no_pickle_load(self):
        """No pickle deserialization in production code."""
        hits = _scan_for_pattern(_core_python_files(), self._PATTERN)
        assert not hits, f"SEC-01: pickle.load found:\n{_fmt(hits)}"


class TestNoSubprocessShellTrue:
    """SEC-02: subprocess calls must not use shell=True."""

    _PATTERN = re.compile(r"subprocess\.\w+\([^)]*shell\s*=\s*True")

    def test_no_shell_true(self):
        """No command injection vectors."""
        hits = _scan_for_pattern(_core_python_files(), self._PATTERN)
        assert not hits, f"SEC-02: subprocess shell=True found:\n{_fmt(hits)}"


class TestNoEvalExec:
    """SEC-03: eval() and exec() must not appear in core code."""

    _PATTERN = re.compile(r"\b(eval|exec)\s*\(")

    def test_no_eval_or_exec(self):
        """No arbitrary code execution."""
        hits = _scan_for_pattern(_core_python_files(), self._PATTERN)
        assert not hits, f"SEC-03: eval/exec found:\n{_fmt(hits)}"


class TestNoOsSystem:
    """SEC-04: os.system() must not be used."""

    _PATTERN = re.compile(r"\bos\.system\s*\(")

    def test_no_os_system(self):
        """os.system is deprecated and unsafe."""
        hits = _scan_for_pattern(_core_python_files(), self._PATTERN)
        assert not hits, f"SEC-04: os.system() found:\n{_fmt(hits)}"


class TestNoUnsafeYamlLoad:
    """SEC-05: yaml.load() must not be used — use yaml.safe_load() instead."""

    _PATTERN = re.compile(r"\byaml\.load\s*\(")
    _SAFE_PATTERN = re.compile(r"\byaml\.safe_load\s*\(")

    def test_no_yaml_load(self):
        """Only yaml.safe_load() is allowed."""
        hits = _scan_for_pattern(_core_python_files(), self._PATTERN)
        unsafe = [(f, n, t) for f, n, t in hits if not self._SAFE_PATTERN.search(t)]
        assert not unsafe, f"SEC-05: yaml.load() without SafeLoader:\n{_fmt(unsafe)}"


class TestNoHardcodedSecrets:
    """SEC-06: No hardcoded passwords, secrets, API keys, or tokens."""

    _PATTERN = re.compile(
        r"""(?:password|secret|api_key|api_secret|token|auth_token"""
        r"""|private_key|access_key)\s*=\s*["'][^"']{4,}["']""",
        re.IGNORECASE,
    )
    _SAFE = re.compile(
        r"""(placeholder|example|your[-_]?|xxx|changeme|TODO|FIXME""" r"""|test[-_]?|dummy|mock|fake|sample)""",
        re.IGNORECASE,
    )

    def test_no_hardcoded_secrets(self):
        """No credential literals in source."""
        hits = _scan_for_pattern(_core_python_files(), self._PATTERN)
        real = [(f, n, t) for f, n, t in hits if not self._SAFE.search(t)]
        assert not real, f"SEC-06: Hardcoded secrets found:\n{_fmt(real)}"


class TestNoConnectionStrings:
    """SEC-07: No connection strings with embedded credentials."""

    _PATTERN = re.compile(
        r"""(jdbc:|odbc:|mongodb(\+srv)?://|postgres(ql)?://|mysql://""" r"""|mssql://|Server=|Data Source=)""",
        re.IGNORECASE,
    )

    def test_no_connection_strings(self):
        """Connection strings must use config or env vars."""
        hits = _scan_for_pattern(_core_python_files(), self._PATTERN)
        assert not hits, f"SEC-07: Connection strings found:\n{_fmt(hits)}"
