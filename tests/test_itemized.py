"""Tests for the itemized deduction breakdown and solar credit."""

from __future__ import annotations

from financial_manager.engine.itemized import (
    SALT_CAP,
    SALT_CAP_MFS,
    SOLAR_CREDIT_RATE,
    compute_itemized_deductions,
    compute_solar_credit,
)


class TestItemizedDeductions:
    """Tests for compute_itemized_deductions()."""

    def test_salt_cap_applied(self) -> None:
        """SALT should be capped at $10,000."""
        result = compute_itemized_deductions(
            state_local_income_tax=8000,
            property_tax=5000,
        )
        assert result.salt_total == 13_000
        assert result.salt_deductible == SALT_CAP

    def test_salt_under_cap(self) -> None:
        """SALT under the cap should not be reduced."""
        result = compute_itemized_deductions(
            state_local_income_tax=3000,
            property_tax=2000,
        )
        assert result.salt_deductible == 5000

    def test_salt_cap_mfs(self) -> None:
        """MFS SALT cap is $5,000."""
        result = compute_itemized_deductions(
            state_local_income_tax=4000,
            property_tax=4000,
            is_mfs=True,
        )
        assert result.salt_deductible == SALT_CAP_MFS

    def test_mortgage_interest(self) -> None:
        """Mortgage interest should pass through to total."""
        result = compute_itemized_deductions(mortgage_interest=12000)
        assert result.mortgage_interest == 12000
        assert result.total_itemized >= 12000

    def test_mortgage_points(self) -> None:
        """Mortgage points should be included."""
        result = compute_itemized_deductions(mortgage_points=3000)
        assert result.mortgage_points == 3000
        assert result.total_itemized >= 3000

    def test_medical_threshold(self) -> None:
        """Medical expenses should only be deductible above 7.5% of AGI."""
        # AGI = 100,000 → threshold = 7,500
        result = compute_itemized_deductions(medical_total=10_000, agi=100_000)
        assert result.medical_deductible == 2500

    def test_medical_below_threshold(self) -> None:
        """Medical expenses below threshold should be zero."""
        result = compute_itemized_deductions(medical_total=5000, agi=100_000)
        assert result.medical_deductible == 0

    def test_charitable_included(self) -> None:
        """Charitable donations should be included in total."""
        result = compute_itemized_deductions(charitable_cash=5000, charitable_noncash=1000)
        assert result.total_itemized == 6000

    def test_comprehensive_total(self) -> None:
        """All deduction categories should sum correctly."""
        result = compute_itemized_deductions(
            mortgage_interest=15000,
            mortgage_points=2000,
            state_local_income_tax=6000,
            property_tax=6000,
            charitable_cash=3000,
            medical_total=20000,
            agi=200_000,  # threshold = 15000, so 5000 deductible
            other_deductions=500,
        )
        # SALT: 12000 capped to 10000
        # Medical: 20000 - 15000 = 5000
        expected = 15000 + 2000 + 10000 + 3000 + 5000 + 500
        assert result.total_itemized == expected


class TestSolarCredit:
    """Tests for compute_solar_credit()."""

    def test_solar_credit_rate(self) -> None:
        """Solar credit should be 30% of system cost."""
        result = compute_solar_credit(30_000)
        assert result.credit_rate == SOLAR_CREDIT_RATE
        assert result.credit_amount == 9000

    def test_solar_credit_zero(self) -> None:
        """Zero cost should produce zero credit."""
        result = compute_solar_credit(0)
        assert result.credit_amount == 0

    def test_solar_credit_large_system(self) -> None:
        """Large system should get proportional credit."""
        result = compute_solar_credit(50_000)
        assert result.credit_amount == 15_000
