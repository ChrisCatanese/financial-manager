"""Tests for tax bracket data integrity."""

from __future__ import annotations

import pytest

from financial_manager.data.tax_brackets import TAX_BRACKETS, get_brackets
from financial_manager.models.filing_status import FilingStatus


class TestBracketData:
    """Test that bracket data is complete and well-formed."""

    @pytest.mark.parametrize("year", [2024, 2025])
    def test_all_statuses_have_brackets(self, year: int):
        """Every filing status must have bracket data for each supported year."""
        for status in FilingStatus:
            brackets = get_brackets(year, status)
            assert len(brackets) == 7, f"Expected 7 brackets for {year}/{status.value}"

    @pytest.mark.parametrize("year", [2024, 2025])
    def test_brackets_are_ascending(self, year: int):
        """Bracket ceilings must be strictly ascending."""
        for status in FilingStatus:
            brackets = get_brackets(year, status)
            ceilings = [ceiling for _, ceiling in brackets]
            for i in range(1, len(ceilings)):
                assert ceilings[i] > ceilings[i - 1], (
                    f"Non-ascending brackets for {year}/{status.value}: "
                    f"{ceilings[i-1]} >= {ceilings[i]}"
                )

    @pytest.mark.parametrize("year", [2024, 2025])
    def test_rates_are_ascending(self, year: int):
        """Tax rates must be strictly ascending across brackets."""
        for status in FilingStatus:
            brackets = get_brackets(year, status)
            rates = [rate for rate, _ in brackets]
            for i in range(1, len(rates)):
                assert rates[i] > rates[i - 1], (
                    f"Non-ascending rates for {year}/{status.value}"
                )

    def test_first_rate_is_10_percent(self):
        """First bracket is always 10%."""
        for key, brackets in TAX_BRACKETS.items():
            assert brackets[0][0] == 0.10, f"First rate for {key} is not 10%"

    def test_last_rate_is_37_percent(self):
        """Last bracket is always 37%."""
        for key, brackets in TAX_BRACKETS.items():
            assert brackets[-1][0] == 0.37, f"Last rate for {key} is not 37%"

    def test_last_ceiling_is_infinity(self):
        """Last bracket ceiling is always infinity."""
        for key, brackets in TAX_BRACKETS.items():
            assert brackets[-1][1] == float("inf"), f"Last ceiling for {key} is not inf"

    def test_unsupported_year_raises(self):
        """Requesting brackets for an unsupported year should raise ValueError."""
        with pytest.raises(ValueError, match="No bracket data"):
            get_brackets(2020, FilingStatus.SINGLE)
