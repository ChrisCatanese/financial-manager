"""Tests for the import hub API module."""

from __future__ import annotations

import csv
from pathlib import Path

from financial_manager.api.import_hub import (
    FileAssessment,
    _assess_csv,
    _build_folder_tree,
    _count_files,
    _detect_file_type,
    _match_to_account,
)
from financial_manager.user_config import (
    Filer,
    FinancialAccount,
    Property,
    UserConfig,
)

# ── Helpers ───────────────────────────────────────────────────────────


def _make_config() -> UserConfig:
    """Build a minimal UserConfig for testing."""
    return UserConfig(
        tax_year=2025,
        filing_status="married_filing_jointly",
        primary_filer=Filer(first_name="Chris", last_name="Catanese", role="primary"),
        spouse=Filer(first_name="Sarah", last_name="Catanese", role="spouse"),
        properties=[
            Property(label="House", address="20 Livingston Ave", role="purchased"),
            Property(label="Condo", address="20 Livingston Ave #901", role="sold"),
        ],
        accounts=[
            FinancialAccount(institution="Fidelity", account_type="brokerage", owner="joint"),
            FinancialAccount(institution="Wells Fargo", account_type="bank", owner="joint"),
        ],
    )


def _write_fidelity_csv(path: Path) -> None:
    """Write a minimal Fidelity positions CSV for testing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Account Name/Number", "Symbol", "Description", "Quantity",
            "Last Price", "Last Price Change", "Current Value",
            "Today's Gain/Loss Dollar", "Today's Gain/Loss Percent",
            "Total Gain/Loss Dollar", "Total Gain/Loss Percent",
            "Percent Of Account", "Cost Basis Total", "Average Cost Basis",
            "Type",
        ])
        writer.writerow([
            "Z12345678", "AAPL", "APPLE INC", "100",
            "$150.00", "+$1.50", "$15,000.00",
            "+$150.00", "+1.01%",
            "+$5,000.00", "+50.00%",
            "30.00%", "$10,000.00", "$100.00",
            "Cash",
        ])


# ── Tests: detect_file_type ──────────────────────────────────────────


class TestDetectFileType:
    """Tests for _detect_file_type."""

    def test_csv(self, tmp_path: Path) -> None:
        """Detect CSV file type."""
        p = tmp_path / "test.csv"
        p.touch()
        assert _detect_file_type(p) == "csv"

    def test_ofx(self, tmp_path: Path) -> None:
        """Detect OFX file type."""
        p = tmp_path / "test.ofx"
        p.touch()
        assert _detect_file_type(p) == "ofx"

    def test_qfx(self, tmp_path: Path) -> None:
        """Detect QFX file type."""
        p = tmp_path / "test.qfx"
        p.touch()
        assert _detect_file_type(p) == "qfx"

    def test_pdf(self, tmp_path: Path) -> None:
        """Detect PDF file type."""
        p = tmp_path / "test.pdf"
        p.touch()
        assert _detect_file_type(p) == "pdf"

    def test_image(self, tmp_path: Path) -> None:
        """Detect image file type."""
        p = tmp_path / "test.jpg"
        p.touch()
        assert _detect_file_type(p) == "image"

    def test_unknown(self, tmp_path: Path) -> None:
        """Unknown extension returns 'other'."""
        p = tmp_path / "test.xyz"
        p.touch()
        assert _detect_file_type(p) == "other"


# ── Tests: count_files ───────────────────────────────────────────────


class TestCountFiles:
    """Tests for _count_files."""

    def test_empty_dir(self, tmp_path: Path) -> None:
        """Empty directory returns 0."""
        assert _count_files(tmp_path) == 0

    def test_nonexistent_dir(self, tmp_path: Path) -> None:
        """Non-existent directory returns 0."""
        assert _count_files(tmp_path / "nope") == 0

    def test_with_files(self, tmp_path: Path) -> None:
        """Count only regular files, skip dotfiles."""
        (tmp_path / "a.csv").touch()
        (tmp_path / "b.pdf").touch()
        (tmp_path / ".hidden").touch()
        assert _count_files(tmp_path) == 2


# ── Tests: build_folder_tree ─────────────────────────────────────────


class TestBuildFolderTree:
    """Tests for _build_folder_tree."""

    def test_structure(self) -> None:
        """Folder tree has Joint, filer names, Property, Exports."""
        config = _make_config()
        tree = _build_folder_tree(config)

        names = [n.name for n in tree]
        assert "Joint" in names
        assert "Chris" in names
        assert "Sarah" in names
        assert "Property" in names
        assert "Exports" in names

    def test_joint_children(self) -> None:
        """Joint folder has Banking, Brokerage, Insurance children."""
        config = _make_config()
        tree = _build_folder_tree(config)
        joint = next(n for n in tree if n.name == "Joint")
        child_names = [c.name for c in joint.children]
        assert "Banking" in child_names
        assert "Brokerage" in child_names

    def test_property_children(self) -> None:
        """Property folder has one child per property."""
        config = _make_config()
        tree = _build_folder_tree(config)
        prop = next(n for n in tree if n.name == "Property")
        child_names = [c.name for c in prop.children]
        assert "House" in child_names
        assert "Condo" in child_names

    def test_export_children(self) -> None:
        """Exports folder has one child per account."""
        config = _make_config()
        tree = _build_folder_tree(config)
        exports = next(n for n in tree if n.name == "Exports")
        child_names = [c.name for c in exports.children]
        assert "Fidelity" in child_names
        assert "Wells Fargo" in child_names


# ── Tests: match_to_account ──────────────────────────────────────────


class TestMatchToAccount:
    """Tests for _match_to_account."""

    def test_match_fidelity(self) -> None:
        """Fidelity assessment routes to Exports/Fidelity."""
        config = _make_config()
        assessment = FileAssessment(detected_institution="Fidelity")
        _match_to_account(assessment, config)
        assert assessment.detected_owner == "joint"
        assert "Fidelity" in assessment.suggested_destination

    def test_no_match(self) -> None:
        """Unknown institution routes to Exports/Other."""
        config = _make_config()
        assessment = FileAssessment(detected_institution="Chase")
        _match_to_account(assessment, config)
        assert "Other" in assessment.suggested_destination


# ── Tests: assess_csv ─────────────────────────────────────────────────


class TestAssessCsv:
    """Tests for _assess_csv."""

    def test_fidelity_positions(self, tmp_path: Path) -> None:
        """Fidelity positions CSV is correctly assessed."""
        csv_path = tmp_path / "positions.csv"
        _write_fidelity_csv(csv_path)
        config = _make_config()
        result = _assess_csv(csv_path, config)
        assert result.detected_institution == "Fidelity"
        assert result.record_count >= 1
        assert result.can_import is True

    def test_invalid_csv(self, tmp_path: Path) -> None:
        """Invalid CSV file sets can_import=False."""
        bad = tmp_path / "bad.csv"
        bad.write_text("not,real,csv\ndata\n")
        config = _make_config()
        result = _assess_csv(bad, config)
        # Should still produce an assessment (may have warnings)
        assert result.filename == "bad.csv"
