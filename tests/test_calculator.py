"""Tests for the core tax calculator engine."""

from __future__ import annotations

import pytest

from financial_manager.engine.calculator import TaxCalculator
from financial_manager.models.filing_status import FilingStatus
from financial_manager.models.tax_input import TaxInput


class TestAGI:
    """Test Adjusted Gross Income computation."""

    def test_agi_basic(self):
        """AGI = gross income - above-the-line deductions."""
        calc = TaxCalculator()
        assert calc.compute_agi(100_000, 5_000) == 95_000.0

    def test_agi_no_deductions(self):
        """AGI equals gross income when no deductions."""
        calc = TaxCalculator()
        assert calc.compute_agi(75_000, 0) == 75_000.0

    def test_agi_floors_at_zero(self):
        """AGI cannot go negative."""
        calc = TaxCalculator()
        assert calc.compute_agi(1_000, 5_000) == 0.0


class TestProgressiveTax:
    """Test progressive bracket tax calculations."""

    def test_single_10_percent_bracket_only(self):
        """Income fully within the 10% bracket (2024 Single)."""
        calc = TaxCalculator()
        tax_input = TaxInput(
            gross_income=10_000,
            filing_status=FilingStatus.SINGLE,
            tax_year=2024,
        )
        result = calc.calculate(tax_input)
        # Taxable income = 10,000 - 14,600 (standard deduction) = 0
        assert result.taxable_income == 0.0
        assert result.total_tax == 0.0

    def test_single_50k_income_2024(self):
        """Single filer with $50,000 income in 2024."""
        calc = TaxCalculator()
        tax_input = TaxInput(
            gross_income=50_000,
            filing_status=FilingStatus.SINGLE,
            tax_year=2024,
        )
        result = calc.calculate(tax_input)
        # Taxable = 50,000 - 14,600 = 35,400
        assert result.taxable_income == 35_400.0
        # 10% on first 11,600 = 1,160
        # 12% on 11,600 to 35,400 = 23,800 * 0.12 = 2,856
        expected_tax = 1_160.0 + 2_856.0
        assert result.total_tax == expected_tax
        assert result.marginal_rate == 0.12

    def test_single_100k_income_2024(self):
        """Single filer with $100,000 income in 2024."""
        calc = TaxCalculator()
        tax_input = TaxInput(
            gross_income=100_000,
            filing_status=FilingStatus.SINGLE,
            tax_year=2024,
        )
        result = calc.calculate(tax_input)
        # Taxable = 100,000 - 14,600 = 85,400
        assert result.taxable_income == 85_400.0
        # 10% on 0-11,600 = 1,160
        # 12% on 11,600-47,150 = 35,550 * 0.12 = 4,266
        # 22% on 47,150-85,400 = 38,250 * 0.22 = 8,415
        expected_tax = 1_160.0 + 4_266.0 + 8_415.0
        assert result.total_tax == expected_tax
        assert result.marginal_rate == 0.22

    def test_mfj_150k_income_2024(self):
        """Married Filing Jointly with $150,000 income in 2024."""
        calc = TaxCalculator()
        tax_input = TaxInput(
            gross_income=150_000,
            filing_status=FilingStatus.MARRIED_FILING_JOINTLY,
            tax_year=2024,
        )
        result = calc.calculate(tax_input)
        # Taxable = 150,000 - 29,200 = 120,800
        assert result.taxable_income == 120_800.0
        # 10% on 0-23,200 = 2,320
        # 12% on 23,200-94,300 = 71,100 * 0.12 = 8,532
        # 22% on 94,300-120,800 = 26,500 * 0.22 = 5,830
        expected_tax = 2_320.0 + 8_532.0 + 5_830.0
        assert result.total_tax == expected_tax

    def test_zero_income(self):
        """Zero income should result in zero tax."""
        calc = TaxCalculator()
        tax_input = TaxInput(gross_income=0)
        result = calc.calculate(tax_input)
        assert result.total_tax == 0.0
        assert result.effective_rate == 0.0


class TestBracketBreakdown:
    """Test that bracket breakdown is returned correctly."""

    def test_breakdown_has_entries(self):
        """Bracket breakdown should have entries for each applicable bracket."""
        calc = TaxCalculator()
        tax_input = TaxInput(
            gross_income=100_000,
            filing_status=FilingStatus.SINGLE,
            tax_year=2024,
        )
        result = calc.calculate(tax_input)
        assert len(result.brackets) == 3  # 10%, 12%, 22%
        assert result.brackets[0].rate == 0.10
        assert result.brackets[1].rate == 0.12
        assert result.brackets[2].rate == 0.22

    def test_bracket_sum_equals_total(self):
        """Sum of bracket taxes should equal total tax."""
        calc = TaxCalculator()
        tax_input = TaxInput(
            gross_income=200_000,
            filing_status=FilingStatus.SINGLE,
            tax_year=2024,
        )
        result = calc.calculate(tax_input)
        bracket_total = sum(b.tax_in_bracket for b in result.brackets)
        assert abs(bracket_total - result.total_tax) < 0.02


class TestEffectiveRate:
    """Test effective tax rate calculations."""

    def test_effective_rate_reasonable(self):
        """Effective rate should be between 0 and marginal rate."""
        calc = TaxCalculator()
        tax_input = TaxInput(
            gross_income=100_000,
            filing_status=FilingStatus.SINGLE,
            tax_year=2024,
        )
        result = calc.calculate(tax_input)
        assert 0 < result.effective_rate < result.marginal_rate


class TestTaxYear2025:
    """Test 2025 tax year brackets."""

    def test_single_50k_2025(self):
        """Single filer with $50k in 2025 — brackets are slightly different."""
        calc = TaxCalculator()
        tax_input = TaxInput(
            gross_income=50_000,
            filing_status=FilingStatus.SINGLE,
            tax_year=2025,
        )
        result = calc.calculate(tax_input)
        # Taxable = 50,000 - 15,750 = 34,250
        assert result.taxable_income == 34_250.0
        assert result.standard_deduction == 15_750.0
        # 10% on 0-11,925 = 1,192.50
        # 12% on 11,925-34,250 = 22,325 * 0.12 = 2,679.00
        expected_tax = 1_192.50 + 2_679.00
        assert result.total_tax == expected_tax


class TestAllFilingStatuses:
    """Ensure all filing statuses work without errors."""

    @pytest.mark.parametrize("status", list(FilingStatus))
    def test_each_status_2024(self, status: FilingStatus):
        """Each filing status should calculate without error for 2024."""
        calc = TaxCalculator()
        tax_input = TaxInput(
            gross_income=75_000,
            filing_status=status,
            tax_year=2024,
        )
        result = calc.calculate(tax_input)
        assert result.total_tax >= 0
        assert result.filing_status == status

    @pytest.mark.parametrize("status", list(FilingStatus))
    def test_each_status_2025(self, status: FilingStatus):
        """Each filing status should calculate without error for 2025."""
        calc = TaxCalculator()
        tax_input = TaxInput(
            gross_income=75_000,
            filing_status=status,
            tax_year=2025,
        )
        result = calc.calculate(tax_input)
        assert result.total_tax >= 0
