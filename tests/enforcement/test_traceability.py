"""Traceability enforcement — the requirements lattice must be complete.

And internally consistent.

Criteria enforced:
  TRACE-01: All required documents exist and have substance
  TRACE-02: Business requirements contain structured IDs (BR-NNN)
  TRACE-03: Functional requirements contain structured IDs (FR-*)
  TRACE-04: Technical requirements contain structured check IDs
  TRACE-05: Traceability matrix exists with forward mapping
  TRACE-06: Code files referenced in the matrix exist on disk
  TRACE-07: Matrix metadata is internally consistent

Run with:  pytest tests/enforcement/test_traceability.py -v

Generalized from template/tests/enforcement/test_traceability.py.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from .conftest import (
    BUSINESS_REQ,
    DOCS_REQ,
    FUNCTIONAL_REQ,
    MANIFEST,
    MATRIX_PATH,
    ROOT,
    TECHNICAL_REQ,
)

# ── helpers ──────────────────────────────────────────────────────────

# BR row: | BR-NNN | ...
_BR_ROW_RE = re.compile(r"^\|\s*(BR-\d{3})\s*\|")

# FR row: | FR-XXXX-N | ... or | FR-NNN | ...
_FR_ROW_RE = re.compile(r"^\|\s*(FR-[\w]+-?\d+)\s*\|")

# TR check ID row: | TR-NNN | ... or | ACCU-1 | ... (2-5 uppercase letters, hyphen, digits)
_TR_ROW_RE = re.compile(r"^\|\s*([A-Z]{2,5}-\d+[a-z]?)\s*\|")

# Module Index row: | `path/to/file.py` | ...
_MODULE_ROW_RE = re.compile(r"^\|\s*`([^`]+\.py)`\s*\|")

# Forward traceability: | TR-NNN | FR-NNN | BR-NNN | Code | Tests | Status |
_FORWARD_ROW_RE = re.compile(
    r"^\|\s*(TR-\d{3})\s*\|"   # col 1: TR
    r"\s*([^|]+?)\s*\|"        # col 2: FR
    r"\s*([^|]+?)\s*\|"        # col 3: BR
    r"\s*([^|]+?)\s*\|"        # col 4: Code
    r"\s*([^|]+?)\s*\|"        # col 5: Tests
)


def _count_ids(path: Path, pattern: re.Pattern) -> set[str]:
    """Extract all matching IDs from a markdown file."""
    ids: set[str] = set()
    if not path.exists():
        return ids
    for line in path.read_text(encoding="utf-8").splitlines():
        m = pattern.match(line)
        if m:
            ids.add(m.group(1))
    return ids


# ── TRACE-01: Required documents exist ────────────────────────────────


class TestRequirementDocumentsExist:
    """TRACE-01: Every required document must exist and have substance."""

    REQUIRED_DOCS = (
        ("business-requirements.md", BUSINESS_REQ),
        ("functional-requirements.md", FUNCTIONAL_REQ),
        ("technical-requirements.md", TECHNICAL_REQ),
        ("dq-manifest.yaml", MANIFEST),
    )

    @pytest.mark.parametrize(
        "name,path",
        REQUIRED_DOCS,
        ids=[name for name, _ in REQUIRED_DOCS],
    )
    def test_document_exists_and_has_content(self, name: str, path: Path) -> None:
        """Each required document must exist and exceed a minimum size."""
        if not path.exists():
            pytest.skip(f"{name} not yet created")
        size = path.stat().st_size
        assert size > 100, (
            f"TRACE-01: {name} exists but is only {size} bytes — likely a stub"
        )

    def test_traceability_matrix_exists(self) -> None:
        """Traceability matrix must exist if project has requirements."""
        if not BUSINESS_REQ.exists():
            pytest.skip("No business requirements — matrix not required")
        if not MATRIX_PATH.exists():
            pytest.skip(
                "TRACE-01: traceability-matrix.md not found — "
                "create at docs/requirements/traceability-matrix.md"
            )
        size = MATRIX_PATH.stat().st_size
        assert size > 200, (
            f"TRACE-01: traceability-matrix.md is only {size} bytes — likely a stub"
        )


# ── TRACE-02: Business requirements have structured IDs ──────────────


class TestBusinessReqIds:
    """TRACE-02: Business requirements must use BR-NNN format."""

    def test_br_ids_present(self) -> None:
        """Business requirements must contain BR-NNN identifiers."""
        if not BUSINESS_REQ.exists():
            pytest.skip("business-requirements.md not found")
        brs = _count_ids(BUSINESS_REQ, _BR_ROW_RE)
        assert len(brs) >= 1, (
            "TRACE-02: No BR-NNN identifiers found in business-requirements.md. "
            "Requirements must use structured IDs (e.g. | BR-001 | ...)."
        )


# ── TRACE-03: Functional requirements have structured IDs ────────────


class TestFunctionalReqIds:
    """TRACE-03: Functional requirements must use FR-* format."""

    def test_fr_ids_present(self) -> None:
        """Functional requirements must contain FR-* identifiers."""
        if not FUNCTIONAL_REQ.exists():
            pytest.skip("functional-requirements.md not found")
        frs = _count_ids(FUNCTIONAL_REQ, _FR_ROW_RE)
        assert len(frs) >= 1, (
            "TRACE-03: No FR-* identifiers found in functional-requirements.md. "
            "Requirements must use structured IDs (e.g. | FR-001 | ...)."
        )


# ── TRACE-04: Technical requirements have check IDs ──────────────────


class TestTechnicalCheckIds:
    """TRACE-04: Technical requirements must use PREFIX-N check IDs."""

    def test_tr_ids_present(self) -> None:
        """Technical requirements must contain PREFIX-N check IDs."""
        if not TECHNICAL_REQ.exists():
            pytest.skip("technical-requirements.md not found")
        trs = _count_ids(TECHNICAL_REQ, _TR_ROW_RE)
        assert len(trs) >= 1, (
            "TRACE-04: No check IDs (e.g. TR-001, ACCU-1) found in "
            "technical-requirements.md. Technical requirements must "
            "define structured validation check IDs."
        )


# ── TRACE-05: Forward traceability in matrix ─────────────────────────


class TestForwardMatrixIntegrity:
    """TRACE-05: If a traceability matrix exists, every TR must map.

    To FRs, BRs, code, and tests.
    """

    def test_every_tr_has_fr(self) -> None:
        """Forward table: every TR row must list at least one FR."""
        if not MATRIX_PATH.exists():
            pytest.skip("traceability-matrix.md not found")
        text = MATRIX_PATH.read_text(encoding="utf-8")
        empty_frs: list[str] = []
        for line in text.splitlines():
            m = _FORWARD_ROW_RE.match(line)
            if m:
                tr_id = m.group(1)
                frs_raw = m.group(2).strip()
                if not frs_raw or frs_raw == "|":
                    empty_frs.append(tr_id)
        if not empty_frs:
            return
        assert not empty_frs, (
            f"TRACE-05: TRs with no FRs in forward traceability: {empty_frs}"
        )

    def test_every_tr_has_br(self) -> None:
        """Forward table: every TR row must list at least one BR."""
        if not MATRIX_PATH.exists():
            pytest.skip("traceability-matrix.md not found")
        text = MATRIX_PATH.read_text(encoding="utf-8")
        empty_brs: list[str] = []
        for line in text.splitlines():
            m = _FORWARD_ROW_RE.match(line)
            if m:
                tr_id = m.group(1)
                brs_raw = m.group(3).strip()
                if not brs_raw or brs_raw == "|":
                    empty_brs.append(tr_id)
        if not empty_brs:
            return
        assert not empty_brs, (
            f"TRACE-05: TRs with no BRs in forward traceability: {empty_brs}"
        )

    def test_every_tr_has_code_ref(self) -> None:
        """Forward table: every TR row must reference a code file."""
        if not MATRIX_PATH.exists():
            pytest.skip("traceability-matrix.md not found")
        text = MATRIX_PATH.read_text(encoding="utf-8")
        empty_code: list[str] = []
        for line in text.splitlines():
            m = _FORWARD_ROW_RE.match(line)
            if m:
                tr_id = m.group(1)
                code_raw = m.group(4).strip()
                if not code_raw or code_raw == "|":
                    empty_code.append(tr_id)
        if not empty_code:
            return
        assert not empty_code, (
            f"TRACE-05: TRs with no code reference in forward traceability: {empty_code}"
        )


# ── TRACE-06: Referenced code files exist ─────────────────────────────


class TestCodeReferencesExist:
    """TRACE-06: Every code file referenced in the Module Index.

    Must exist on disk.
    """

    def test_referenced_files_exist(self) -> None:
        """Every code path in the Module Index table must exist on disk."""
        if not MATRIX_PATH.exists():
            pytest.skip("traceability-matrix.md not found")
        text = MATRIX_PATH.read_text(encoding="utf-8")
        missing: list[str] = []
        for line in text.splitlines():
            m = _MODULE_ROW_RE.match(line)
            if m:
                rel_path = m.group(1)
                # Only check paths with directory separators
                if "/" not in rel_path:
                    continue
                full_path = ROOT / rel_path
                if not full_path.exists():
                    missing.append(rel_path)
        assert not missing, (
            "TRACE-06: Files referenced in traceability matrix but missing from disk:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )


# ── TRACE-07: Matrix metadata consistency ─────────────────────────────


class TestMatrixConsistency:
    """TRACE-07: Matrix metadata must be internally consistent."""

    def test_matrix_has_forward_table(self) -> None:
        """Matrix must have a Forward Traceability section."""
        if not MATRIX_PATH.exists():
            pytest.skip("traceability-matrix.md not found")
        text = MATRIX_PATH.read_text(encoding="utf-8")
        has_forward = re.search(
            r"##.*[Ff]orward\s+[Tt]raceability", text, re.MULTILINE
        )
        assert has_forward, (
            "TRACE-07: Traceability matrix must have a 'Forward Traceability' section"
        )

    def test_requirements_dir_exists(self) -> None:
        """docs/requirements/ must exist for cross-referencing."""
        assert DOCS_REQ.is_dir(), (
            "TRACE-07: docs/requirements/ directory is required for requirement documents"
        )
