"""Tests for deduction logic."""

from __future__ import annotations

from financial_manager.engine.deductions import apply_deductions
from financial_manager.models.filing_status import FilingStatus


class TestDeductions:
    """Test standard and itemized deduction application."""

    def test_standard_deduction_single_2024(self):
        """Single filer should get $14,600 standard deduction in 2024."""
        taxable, standard, used = apply_deductions(
            agi=50_000,
            tax_year=2024,
            filing_status=FilingStatus.SINGLE,
        )
        assert standard == 14_600.0
        assert used == 14_600.0
        assert taxable == 35_400.0

    def test_standard_deduction_mfj_2024(self):
        """MFJ filer should get $29,200 standard deduction in 2024."""
        taxable, standard, used = apply_deductions(
            agi=80_000,
            tax_year=2024,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
        )
        assert standard == 29_200.0
        assert used == 29_200.0
        assert taxable == 50_800.0

    def test_itemized_overrides_standard(self):
        """When itemized > standard, itemized should be used."""
        taxable, standard, used = apply_deductions(
            agi=100_000,
            tax_year=2024,
            filing_status=FilingStatus.SINGLE,
            itemized_deductions=25_000,
        )
        assert standard == 14_600.0
        assert used == 25_000.0
        assert taxable == 75_000.0

    def test_standard_beats_low_itemized(self):
        """When itemized < standard, standard should be used."""
        taxable, standard, used = apply_deductions(
            agi=100_000,
            tax_year=2024,
            filing_status=FilingStatus.SINGLE,
            itemized_deductions=5_000,
        )
        assert used == 14_600.0
        assert taxable == 85_400.0

    def test_taxable_income_floors_at_zero(self):
        """Taxable income cannot go negative."""
        taxable, _, _ = apply_deductions(
            agi=5_000,
            tax_year=2024,
            filing_status=FilingStatus.SINGLE,
        )
        assert taxable == 0.0

    def test_2025_deductions(self):
        """2025 standard deductions should be higher than 2024."""
        _, std_2024, _ = apply_deductions(50_000, 2024, FilingStatus.SINGLE)
        _, std_2025, _ = apply_deductions(50_000, 2025, FilingStatus.SINGLE)
        assert std_2025 > std_2024
