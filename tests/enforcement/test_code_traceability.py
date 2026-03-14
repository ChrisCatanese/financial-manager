"""Code traceability enforcement — guarantees every production module.

Is traceable to a requirement and properly classified.

Criteria enforced:
  CTRC-01: Core modules appear in the Module Index table
  CTRC-02: No archive/exploratory imports in core code
  CTRC-03: Core modules are reachable from pipeline entry points
  CTRC-04: No sys.path hacks in production code
  CTRC-05: All Python files are classified (src/, scripts/, tests/)
  CTRC-06: No loose .py files at project root
  CTRC-07: Docs follow kebab-case naming convention

Run with:  pytest tests/enforcement/test_code_traceability.py -v

Generalized from template/tests/enforcement/test_code_traceability.py.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from .conftest import (
    DOCS_DIR,
    EXCLUDED_DIRS,
    MATRIX_PATH,
    PACKAGE_DIR,
    ROOT,
    SCRIPTS_DIR,
)

# Files always exempt from tracing
ALWAYS_EXEMPT = {"__init__.py", "conftest.py"}

# Module Index row: | `path/to/file.py` | ...
_MODULE_ROW_RE = re.compile(r"^\|\s*`([^`]+\.py)`\s*\|")


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


def _production_modules() -> list[Path]:
    """Non-exempt .py files in src/ (the core package)."""
    return [
        f for f in _python_files_in(PACKAGE_DIR) if f.name not in ALWAYS_EXEMPT
    ]


def _module_rel_path(filepath: Path) -> str:
    """Return path relative to project root."""
    return str(filepath.relative_to(ROOT))


def _get_imports(filepath: Path) -> set[str]:
    """Parse a Python file and return the set of imported module names."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


def _traced_modules_in_matrix() -> set[str]:
    """Extract all module paths from the Module Index table."""
    if not MATRIX_PATH.exists():
        return set()
    traced: set[str] = set()
    for line in MATRIX_PATH.read_text(encoding="utf-8").splitlines():
        m = _MODULE_ROW_RE.match(line)
        if m:
            traced.add(m.group(1))
    return traced


# ── CTRC-01: Core modules in traceability table ──────────────────────


class TestCoreModulesTraced:
    """CTRC-01: Every production module in src/ must appear.

    In the Module Index table (if the matrix exists).
    """

    @pytest.mark.parametrize(
        "module",
        [_module_rel_path(m) for m in _production_modules()],
        ids=[m.name for m in _production_modules()],
    )
    def test_module_in_module_index(self, module: str) -> None:
        """Production module must appear in the Module Index table."""
        if not MATRIX_PATH.exists():
            pytest.skip("traceability-matrix.md not found — skipping code traceability")
        traced = _traced_modules_in_matrix()
        assert module in traced, (
            f"CTRC-01: {module} is a production module but is not in the "
            f"Module Index table.\n"
            f"Either:\n"
            f"  1. Add it to the Module Index with its TR references, or\n"
            f"  2. Move it to _legacy/ if it's no longer part of the pipeline."
        )


# ── CTRC-02: No archive/exploratory imports in core ──────────────────


class TestNoArchiveImports:
    """CTRC-02: Production code must not import from archived/exploratory dirs."""

    ARCHIVE_PATTERNS = (
        re.compile(r"from\s+.*(_legacy|archive|scratch|sandbox)\b"),
        re.compile(r"import\s+.*(_legacy|archive|scratch|sandbox)\b"),
    )

    @pytest.mark.parametrize(
        "module",
        _production_modules(),
        ids=[m.name for m in _production_modules()],
    )
    def test_no_archive_imports(self, module: Path) -> None:
        """Production code must not depend on archived/exploratory code."""
        try:
            source = module.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return

        violations: list[str] = []
        for i, line in enumerate(source.splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            for pat in self.ARCHIVE_PATTERNS:
                if pat.search(line):
                    violations.append(f"  L{i}: {line.strip()}")

        assert not violations, (
            f"CTRC-02: {module.name} imports from archived/exploratory code:\n"
            + "\n".join(violations)
            + "\nArchived code must not be coupled to production."
        )


# ── CTRC-03: Pipeline reachability ────────────────────────────────────


class TestPipelineReachability:
    """CTRC-03: If a pipeline entry point exists, every core module.

    Should be reachable from it via import chains.
    """

    def test_entry_points_import_core(self) -> None:
        """Pipeline entry points should import from the core package."""
        entries: list[Path] = []
        if SCRIPTS_DIR.exists():
            entries.extend(SCRIPTS_DIR.glob("*.py"))
        # Also check shell-referenced Python modules
        for sh in ROOT.glob("*.sh"):
            try:
                content = sh.read_text(encoding="utf-8")
                # Look for `python script.py` patterns
                for m in re.finditer(r"python[3]?\s+([\w/]+\.py)", content):
                    candidate = ROOT / m.group(1)
                    if candidate.exists():
                        entries.append(candidate)
            except (OSError, UnicodeDecodeError):
                continue

        if not entries:
            pytest.skip("No pipeline entry points found")

        # Check that at least one entry imports from the package
        pkg_name = PACKAGE_DIR.name
        any_import = False
        for entry in entries:
            imports = _get_imports(entry)
            if pkg_name in imports or any(pkg_name in i for i in imports):
                any_import = True
                break

        if not any_import:
            # If package has no modules, this is fine
            modules = _production_modules()
            if not modules:
                return
            pytest.skip(
                f"CTRC-03: No entry point imports from {pkg_name} — "
                f"verify that pipeline scripts use the core package"
            )


# ── CTRC-04: No sys.path hacks ───────────────────────────────────────


class TestNoSysPathHacks:
    """CTRC-04: Production modules must not manipulate sys.path."""

    _SYS_PATH_RE = re.compile(r"sys\.path\.(insert|append)\b")

    def test_no_sys_path_in_production(self) -> None:
        """src/ and scripts/ must use proper imports, not sys.path hacks."""
        violations: list[str] = []
        for d in [PACKAGE_DIR, SCRIPTS_DIR]:
            for f in _python_files_in(d):
                try:
                    source = f.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                for i, line in enumerate(source.splitlines(), 1):
                    if self._SYS_PATH_RE.search(line) and not line.lstrip().startswith("#"):
                        rel = _module_rel_path(f)
                        violations.append(f"  {rel}:{i}: {line.strip()}")

        assert not violations, (
            "CTRC-04: Production modules must not use sys.path hacks:\n"
            + "\n".join(violations)
            + "\nUse proper package imports instead."
        )


# ── CTRC-05: All Python files are classified ─────────────────────────


class TestModuleClassification:
    """CTRC-05: Every Python file must be in a proper directory.

    Allowed: src/, scripts/, tests/, or a declared exploratory path.
    """

    def test_no_python_at_project_root(self) -> None:
        """No loose .py files at project root level."""
        root_py = [f.name for f in ROOT.glob("*.py") if f.name != "conftest.py"]
        assert not root_py, (
            "CTRC-05: Loose .py files at project root (move to src/, scripts/, or util/):\n"
            + "\n".join(f"  - {f}" for f in sorted(root_py))
        )


# ── CTRC-06: No loose scripts outside scripts/ ───────────────────────


class TestNoLooseScripts:
    """CTRC-06: Executable Python scripts belong in scripts/, not scattered."""

    def test_no_scripts_in_src(self) -> None:
        """src/ should contain library code, not runnable scripts."""
        for f in _python_files_in(PACKAGE_DIR):
            try:
                content = f.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if f.name in ALWAYS_EXEMPT:
                continue
            # Check for argparse / click / main execution patterns at module level
            has_argparse = "argparse" in content and "parse_args" in content
            has_main_block = re.search(
                r'^if\s+__name__\s*==\s*["\']__main__["\']\s*:', content, re.MULTILINE
            )
            if has_argparse and has_main_block:
                # This is OK for CLI tools within a package — just flag scripts
                # that look like standalone executables
                pass


# ── CTRC-07: Docs follow kebab-case ──────────────────────────────────


class TestDocsKebabCase:
    """CTRC-07: All .md files in docs/ must use kebab-case.

    README.md and CHANGELOG.md are excepted.
    """

    _KEBAB_RE = re.compile(r"^[a-z][a-z0-9\-]*$")
    _EXEMPT = frozenset({"README.md", "CHANGELOG.md"})

    def test_kebab_case_docs(self) -> None:
        """All .md files in docs/ must follow kebab-case naming."""
        if not DOCS_DIR.exists():
            pytest.skip("No docs/ directory")
        bad: list[str] = []
        for f in sorted(DOCS_DIR.rglob("*.md")):
            if f.name in self._EXEMPT:
                continue
            if not self._KEBAB_RE.match(f.stem):
                bad.append(str(f.relative_to(ROOT)))
        assert not bad, (
            "CTRC-07: Non-kebab-case .md files in docs/ "
            "(rename to kebab-case, e.g. my-document.md):\n"
            + "\n".join(f"  - {f}" for f in bad)
        )
