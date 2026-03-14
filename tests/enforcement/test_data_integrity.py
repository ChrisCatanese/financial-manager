"""Data integrity enforcement — ALCOA+ principles must be traceable.

Across validation checks, requirements, and documentation.

ALCOA+ Principles (ICH Q7 / 21 CFR Part 11):
  A  = Attributable     (who did it, when)
  L  = Legible          (readable, understandable, permanent)
  C  = Contemporaneous  (recorded at time of activity)
  O  = Original         (first recording, source of truth)
  A+ = Accurate         (correct, precise, within tolerance)
  C+ = Complete         (all data present, nothing omitted)
  C+ = Consistent       (self-consistent, no contradictions)
  E+ = Enduring         (available for the record's lifetime)
  A+ = Available        (accessible when needed)

Criteria enforced:
  DINT-01: Technical requirements reference ALCOA+ principles
  DINT-02: Validation scripts contain check IDs
  DINT-03: Check IDs are sequential (no large gaps)
  DINT-04: Change-log entries carry traceability metadata
  DINT-05: dq-manifest.yaml declares enforcement level

Run with:  pytest tests/enforcement/test_data_integrity.py -v

Generalized from template/tests/enforcement/test_data_integrity.py.
"""

from __future__ import annotations

import json
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
    TECHNICAL_REQ,
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


def _extract_check_ids(filepath: Path) -> list[str]:
    """Extract all check IDs like TRAC-1, VLID-12, TR-001, etc. from a file."""
    if not filepath.exists():
        return []
    content = filepath.read_text(encoding="utf-8")
    return re.findall(r"[A-Z]{2,5}-\d+[a-z]?", content)


def _unique_check_ids_in_dir(directory: Path) -> set[str]:
    """Get unique check IDs across all .py files in a directory."""
    all_ids: set[str] = set()
    for f in _python_files_in(directory):
        all_ids.update(_extract_check_ids(f))
    return all_ids


def _check_ids_by_prefix(directory: Path) -> dict[str, set[str]]:
    """Group unique check IDs from all .py files in a dir by their prefix."""
    ids = _unique_check_ids_in_dir(directory)
    groups: dict[str, set[str]] = {}
    for cid in ids:
        prefix = cid.rsplit("-", 1)[0]
        groups.setdefault(prefix, set()).add(cid)
    return groups


# ── DINT-01: Technical requirements reference ALCOA+ ─────────────────


class TestAlcoaReferenced:
    """DINT-01: Technical requirements should reference ALCOA+ principles.

    If the project handles regulated or quality-critical data.
    """

    def test_tech_reqs_mention_data_integrity(self) -> None:
        """Technical requirements doc should reference data integrity."""
        if not TECHNICAL_REQ.exists():
            pytest.skip("technical-requirements.md not found")
        content = TECHNICAL_REQ.read_text(encoding="utf-8").lower()
        keywords = ["alcoa", "data integrity", "attributable", "traceable"]
        found = any(kw in content for kw in keywords)
        if not found:
            pytest.skip(
                "DINT-01: Technical requirements do not reference ALCOA+ "
                "(skip if project is not data-integrity-scoped)"
            )


# ── DINT-02: Validation scripts contain check IDs ────────────────────


class TestValidationCheckIds:
    """DINT-02: If the project has validation scripts, they must use.

    Structured check IDs (PREFIX-NNN pattern).
    """

    def test_scripts_have_check_ids(self) -> None:
        """Scripts with 'valid' in the name should have check IDs."""
        validation_scripts: list[Path] = []
        for d in [SCRIPTS_DIR, PACKAGE_DIR]:
            for f in _python_files_in(d):
                if "valid" in f.stem.lower():
                    validation_scripts.append(f)

        if not validation_scripts:
            pytest.skip("No validation scripts found")

        for script in validation_scripts:
            ids = _extract_check_ids(script)
            assert ids, (
                f"DINT-02: {script.name} appears to be a validation script "
                f"but contains no structured check IDs (e.g. ACCU-1, COMP-1)"
            )


# ── DINT-03: Check IDs are sequential ────────────────────────────────


class TestCheckIdSequential:
    """DINT-03: Within each prefix group, check IDs should be sequential.

    No large gaps that suggest deleted checks without replacement.
    """

    MAX_GAP = 5  # Allow small gaps for deprecated checks

    def test_no_large_gaps_in_check_ids(self) -> None:
        """Scan src/ and scripts/ for check IDs with large sequence gaps."""
        all_groups: dict[str, set[str]] = {}
        for d in [PACKAGE_DIR, SCRIPTS_DIR]:
            for prefix, ids in _check_ids_by_prefix(d).items():
                all_groups.setdefault(prefix, set()).update(ids)

        if not all_groups:
            pytest.skip("No check IDs found in project")

        large_gaps: list[str] = []
        for prefix, ids in sorted(all_groups.items()):
            nums: list[int] = []
            for cid in ids:
                match = re.search(r"-(\d+)", cid)
                if match:
                    nums.append(int(match.group(1)))
            if len(nums) < 2:
                continue
            nums.sort()
            for i in range(1, len(nums)):
                gap = nums[i] - nums[i - 1]
                if gap > self.MAX_GAP:
                    large_gaps.append(f"  {prefix}: gap between {nums[i - 1]} and {nums[i]} (gap={gap})")

        assert not large_gaps, "DINT-03: Large gaps in check ID sequences:\n" + "\n".join(large_gaps)


# ── DINT-04: Change-log entries carry traceability ───────────────────


class TestChangeLogTraceability:
    """DINT-04: Resolved change-log entries must have traceability.

    Metadata: requirement_refs, test_refs, requirement_change.
    """

    CL_PATH = ROOT / "docs" / "change-log.json"

    def test_resolved_entries_have_refs(self) -> None:
        """Every resolved entry must reference at least one requirement."""
        if not self.CL_PATH.exists():
            pytest.skip("docs/change-log.json not found")

        data = json.loads(self.CL_PATH.read_text(encoding="utf-8"))
        items = data.get("items", [])
        resolved = [i for i in items if i.get("resolved")]

        if not resolved:
            pytest.skip("No resolved change-log entries to check")

        untraceable: list[str] = []
        for entry in resolved:
            eid = entry.get("id", "???")
            refs = entry.get("requirement_refs", [])
            change = entry.get("requirement_change", "")
            if not refs and not change:
                untraceable.append(eid)

        assert not untraceable, (
            "DINT-04: Resolved change-log entries without traceability:\n"
            + "\n".join(f"  {eid}" for eid in untraceable)
            + "\nResolved entries must have requirement_refs or requirement_change."
        )


# ── DINT-05: Manifest declares enforcement level ─────────────────────


class TestManifestEnforcement:
    """DINT-05: dq-manifest.yaml must declare enforcement level."""

    def test_enforcement_declared(self) -> None:
        """Manifest must have enforcement: strict|warn|off."""
        assert MANIFEST.exists(), "DINT-05: dq-manifest.yaml missing"
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        level = data.get("enforcement")
        assert level in {"strict", "warn", "off"}, f"DINT-05: enforcement must be strict|warn|off, got {level!r}"

    def test_change_log_path_declared(self) -> None:
        """Manifest should declare the change_log path."""
        data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
        assert "change_log" in data, "DINT-05: dq-manifest.yaml missing 'change_log' path declaration"
