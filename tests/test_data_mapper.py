"""Tests for the financial data mapper module."""

from __future__ import annotations

import pytest

from financial_manager.connectors.csv_importer import CsvImportResult, CsvTransaction
from financial_manager.connectors.data_mapper import (
    DividendIncome,
    ImportSummary,
    InterestIncome,
    _categorize_transaction,
    map_csv_results,
    map_ofx_results,
    merge_summaries,
)
from financial_manager.connectors.ofx_importer import OfxImportResult, OfxTransaction

# ── Transaction categorisation ────────────────────────────────────────


class TestCategorizeTransaction:
    """Tests for tax-category detection from transaction descriptions."""

    def test_interest(self) -> None:
        """Categorise an interest payment description."""
        assert _categorize_transaction("INTEREST PAYMENT") == "interest"

    def test_charitable(self) -> None:
        """Categorise a charitable donation description."""
        assert _categorize_transaction("DONATION TO RED CROSS") == "charitable"

    def test_medical(self) -> None:
        """Categorise a medical expense description."""
        assert _categorize_transaction("PHARMACY PURCHASE") == "medical"

    def test_property_tax(self) -> None:
        """Categorise a property tax payment description."""
        assert _categorize_transaction("PROPERTY TAX BILL") == "property_tax"

    def test_unrelated_returns_empty(self) -> None:
        """Return empty string for a non-tax-relevant description."""
        assert _categorize_transaction("COFFEE SHOP") == ""


# ── CSV result mapping ────────────────────────────────────────────────


class TestMapCsvResults:
    """Tests for mapping CSV import results to tax-relevant summaries."""

    def test_empty_results(self) -> None:
        """Produce a zero-valued summary from an empty results list."""
        summary = map_csv_results([])
        assert summary.total_interest == 0.0
        assert summary.sources_imported == 0

    def test_interest_transactions(self) -> None:
        """Map two interest transactions and verify total_interest."""
        result = CsvImportResult(
            source_path="interest.csv",
            institution="TestBank",
            format_type="bank_transactions",
            transactions=[
                CsvTransaction(date="2025-01-15", description="INTEREST EARNED", action="interest", amount=25.50),
                CsvTransaction(date="2025-02-15", description="INTEREST EARNED", action="interest", amount=30.00),
            ],
        )
        summary = map_csv_results([result], tax_year=2025)

        assert summary.total_interest == pytest.approx(55.50)
        assert len(summary.interest_income) == 1
        assert summary.interest_income[0].institution == "TestBank"

    def test_dividend_and_sell(self) -> None:
        """Map a dividend and a sell transaction into their respective buckets."""
        result = CsvImportResult(
            source_path="activity.csv",
            institution="Fidelity",
            format_type="fidelity_activity",
            transactions=[
                CsvTransaction(
                    date="2025-03-01", symbol="VTI", description="VANGUARD TOTAL STOCK",
                    action="dividend", amount=45.67,
                ),
                CsvTransaction(
                    date="2025-06-15", symbol="AAPL", description="APPLE INC",
                    action="sell", amount=9750.00,
                ),
            ],
        )
        summary = map_csv_results([result], tax_year=2025)

        assert summary.total_ordinary_dividends == pytest.approx(45.67)
        assert len(summary.dividend_income) == 1
        assert len(summary.capital_gains) == 1
        assert summary.capital_gains[0].transactions[0].security == "AAPL"


# ── OFX result mapping ───────────────────────────────────────────────


class TestMapOfxResults:
    """Tests for mapping OFX import results to tax-relevant summaries."""

    def test_bank_interest(self) -> None:
        """Map an OFX INT transaction to interest income."""
        result = OfxImportResult(
            source_path="bank.ofx",
            institution="TestBank",
            account_id="****6789",
            account_type="CHECKING",
            transactions=[
                OfxTransaction(
                    date="2025-01-15", fit_id="T001", name="INTEREST PAYMENT",
                    amount=12.50, tran_type="INT", account_id="****6789", account_type="CHECKING",
                ),
            ],
        )
        summary = map_ofx_results([result], tax_year=2025)

        assert summary.total_interest == pytest.approx(12.50)
        assert len(summary.interest_income) == 1
        assert summary.interest_income[0].institution == "TestBank"

    def test_empty(self) -> None:
        """Produce a zero-valued summary from an empty OFX results list."""
        summary = map_ofx_results([])
        assert summary.total_interest == 0.0
        assert summary.sources_imported == 0


# ── Summary merging ───────────────────────────────────────────────────


class TestMergeSummaries:
    """Tests for merging multiple ImportSummary objects."""

    def test_merge_two(self) -> None:
        """Merge two summaries and verify combined totals are recomputed."""
        s1 = ImportSummary(
            tax_year=2025,
            interest_income=[
                InterestIncome(institution="BankA", total_interest=100.00),
            ],
            sources_imported=1,
        )
        s2 = ImportSummary(
            tax_year=2025,
            interest_income=[
                InterestIncome(institution="BankB", total_interest=50.00),
            ],
            dividend_income=[
                DividendIncome(institution="BrokerC", ordinary_dividends=200.00),
            ],
            sources_imported=2,
        )

        merged = merge_summaries(s1, s2)

        assert merged.tax_year == 2025
        assert len(merged.interest_income) == 2
        assert merged.total_interest == pytest.approx(150.00)
        assert len(merged.dividend_income) == 1
        assert merged.total_ordinary_dividends == pytest.approx(200.00)
        assert merged.sources_imported == 3
