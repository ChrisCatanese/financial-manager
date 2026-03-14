"""Tests for Pydantic data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from financial_manager.models.filing_status import FilingStatus
from financial_manager.models.tax_input import TaxInput
from financial_manager.models.tax_result import BracketResult, TaxResult


class TestFilingStatus:
    """Test FilingStatus enum."""

    def test_all_statuses_defined(self):
        """All 5 IRS filing statuses must be defined."""
        assert len(FilingStatus) == 5

    def test_status_values(self):
        """Status string values must be lowercase snake_case."""
        expected = {
            "single",
            "married_filing_jointly",
            "married_filing_separately",
            "head_of_household",
            "qualifying_surviving_spouse",
        }
        actual = {s.value for s in FilingStatus}
        assert actual == expected


class TestTaxInput:
    """Test TaxInput Pydantic model."""

    def test_default_values(self):
        """TaxInput should have sensible defaults."""
        ti = TaxInput(gross_income=50_000)
        assert ti.filing_status == FilingStatus.SINGLE
        assert ti.tax_year == 2024
        assert ti.above_the_line_deductions == 0.0
        assert ti.itemized_deductions == 0.0

    def test_negative_income_rejected(self):
        """Negative gross income should be rejected."""
        with pytest.raises(ValidationError):
            TaxInput(gross_income=-1000)

    def test_invalid_year_rejected(self):
        """Tax year outside 2024-2025 range should be rejected."""
        with pytest.raises(ValidationError):
            TaxInput(gross_income=50_000, tax_year=2023)

    def test_all_fields_populated(self):
        """All fields should be assignable."""
        ti = TaxInput(
            gross_income=150_000,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
            tax_year=2025,
            above_the_line_deductions=5_000,
            itemized_deductions=30_000,
            num_dependents=2,
            num_qualifying_children=2,
        )
        assert ti.gross_income == 150_000
        assert ti.num_qualifying_children == 2


class TestTaxResult:
    """Test TaxResult Pydantic model."""

    def test_result_creation(self):
        """TaxResult should be constructable with all required fields."""
        result = TaxResult(
            tax_year=2024,
            filing_status=FilingStatus.SINGLE,
            gross_income=100_000,
            agi=100_000,
            standard_deduction=14_600,
            deduction_used=14_600,
            taxable_income=85_400,
            total_tax=13_841,
            effective_rate=0.13841,
            marginal_rate=0.22,
            brackets=[
                BracketResult(
                    rate=0.10,
                    range_low=0,
                    range_high=11_600,
                    taxable_in_bracket=11_600,
                    tax_in_bracket=1_160,
                ),
            ],
        )
        assert result.total_tax == 13_841
        assert len(result.brackets) == 1
