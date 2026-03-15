"""Tests for the CSV importer module."""

from __future__ import annotations

import textwrap
from pathlib import Path

from financial_manager.connectors.csv_importer import (
    _normalize_action,
    _parse_money,
    detect_csv_format,
    import_csv,
)

# ── Money parsing ─────────────────────────────────────────────────────


class TestParseMoney:
    """Tests for monetary value parsing."""

    def test_simple_number(self) -> None:
        """Parse a plain numeric string."""
        assert _parse_money("1234.56") == 1234.56

    def test_with_dollar_sign(self) -> None:
        """Parse a dollar-sign-prefixed string with commas."""
        assert _parse_money("$1,234.56") == 1234.56

    def test_negative(self) -> None:
        """Parse a negative value with leading minus."""
        assert _parse_money("-100.00") == -100.00

    def test_parenthetical_negative(self) -> None:
        """Parse parenthetical negatives like ``($100.00)``."""
        assert _parse_money("($100.00)") == -100.00

    def test_empty_string(self) -> None:
        """Return 0.0 for empty input."""
        assert _parse_money("") == 0.0

    def test_whitespace(self) -> None:
        """Return 0.0 for whitespace-only input."""
        assert _parse_money("  ") == 0.0

    def test_commas_and_dollar(self) -> None:
        """Strip commas and dollar signs from large values."""
        assert _parse_money("$12,345,678.90") == 12345678.90

    def test_plus_sign(self) -> None:
        """Parse a value with an explicit plus sign."""
        assert _parse_money("+500.00") == 500.00


# ── Format detection ──────────────────────────────────────────────────


class TestDetectCsvFormat:
    """Tests for CSV format auto-detection from headers."""

    def test_fidelity_positions(self) -> None:
        """Detect Fidelity positions CSV from its column signature."""
        headers = [
            "Account Name/Number", "Symbol", "Description", "Quantity",
            "Last Price", "Current Value", "Cost Basis Total",
        ]
        institution, fmt = detect_csv_format(headers)
        assert institution == "Fidelity"
        assert fmt == "fidelity_positions"

    def test_fidelity_activity(self) -> None:
        """Detect Fidelity activity CSV from its column signature."""
        headers = [
            "Run Date", "Account", "Action", "Symbol",
            "Description", "Quantity", "Price ($)", "Amount ($)",
        ]
        institution, fmt = detect_csv_format(headers)
        assert institution == "Fidelity"
        assert fmt == "fidelity_activity"

    def test_generic_bank(self) -> None:
        """Detect generic bank CSV with date/description/amount."""
        headers = ["Date", "Description", "Amount"]
        institution, fmt = detect_csv_format(headers)
        assert institution == "generic"
        assert fmt == "bank_transactions"

    def test_split_debit_credit(self) -> None:
        """Detect bank CSV with separate debit/credit columns."""
        headers = ["Date", "Description", "Debit", "Credit"]
        institution, fmt = detect_csv_format(headers)
        assert institution == "generic"
        assert fmt == "bank_transactions_split"

    def test_unknown_format(self) -> None:
        """Return unknown for unrecognized column headers."""
        headers = ["foo", "bar", "baz"]
        institution, fmt = detect_csv_format(headers)
        assert institution == "unknown"
        assert fmt == "unknown"

    def test_case_insensitive(self) -> None:
        """Match headers regardless of case."""
        headers = ["DATE", "DESCRIPTION", "AMOUNT"]
        institution, fmt = detect_csv_format(headers)
        assert institution == "generic"
        assert fmt == "bank_transactions"

    def test_extra_columns_still_match(self) -> None:
        """Extra columns beyond the signature should still match."""
        headers = ["Date", "Description", "Amount", "Balance", "Notes"]
        institution, fmt = detect_csv_format(headers)
        assert institution == "generic"
        assert fmt == "bank_transactions"


# ── Action normalization ──────────────────────────────────────────────


class TestNormalizeAction:
    """Tests for transaction action normalization."""

    def test_you_bought(self) -> None:
        """Normalize Fidelity 'YOU BOUGHT' to 'buy'."""
        assert _normalize_action("YOU BOUGHT") == "buy"

    def test_dividend_received(self) -> None:
        """Normalize 'Dividend Received' to 'dividend'."""
        assert _normalize_action("Dividend Received") == "dividend"

    def test_short_term_cap_gain(self) -> None:
        """Normalize 'Short-Term Cap Gain' to 'short_term_gain'."""
        assert _normalize_action("Short-Term Cap Gain") == "short_term_gain"

    def test_passthrough_unknown(self) -> None:
        """Unknown actions pass through lowercased."""
        result = _normalize_action("SOME WEIRD ACTION")
        assert result == "some weird action"


# ── Full CSV import ───────────────────────────────────────────────────


class TestImportCsv:
    """Tests for end-to-end CSV file import."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Return a warning for nonexistent files."""
        result = import_csv(tmp_path / "nonexistent.csv")
        assert len(result.warnings) == 1
        assert "not found" in result.warnings[0].lower()

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        """Return a warning for unsupported file extensions."""
        p = tmp_path / "data.xlsx"
        p.write_text("data")
        result = import_csv(p)
        assert len(result.warnings) == 1
        assert "extension" in result.warnings[0].lower()

    def test_empty_file(self, tmp_path: Path) -> None:
        """Handle empty CSV files gracefully."""
        p = tmp_path / "empty.csv"
        p.write_text("")
        result = import_csv(p)
        assert result.format_type == ""
        assert len(result.warnings) >= 1

    def test_fidelity_positions_csv(self, tmp_path: Path) -> None:
        """Parse a Fidelity positions CSV with AAPL and cash holdings."""
        csv_content = textwrap.dedent("""\
            Account Name/Number,Symbol,Description,Quantity,Last Price,Current Value,Cost Basis Total
            Z12345678,AAPL,APPLE INC,100,$150.25,"$15,025.00","$10,000.00"
            Z12345678,SPAXX,FIDELITY GOVT MONEY,500.00,$1.00,$500.00,$500.00
        """)
        p = tmp_path / "positions.csv"
        p.write_text(csv_content)
        result = import_csv(p)

        assert result.institution == "Fidelity"
        assert result.format_type == "fidelity_positions"
        assert len(result.holdings) == 2

        aapl = result.holdings[0]
        assert aapl.symbol == "AAPL"
        assert aapl.quantity == 100.0
        assert aapl.current_value == 15025.00
        assert aapl.cost_basis_total == 10000.00
        assert aapl.holding_type == "equity"

        cash = result.holdings[1]
        assert cash.symbol == "SPAXX"
        assert cash.holding_type == "cash"

    def test_fidelity_activity_csv(self, tmp_path: Path) -> None:
        """Parse a Fidelity activity CSV with buy/dividend/sell transactions."""
        csv_content = textwrap.dedent("""\
            Run Date,Account,Action,Symbol,Description,Quantity,Price ($),Amount ($)
            01/15/2025,Z12345678,YOU BOUGHT,VTI,VANGUARD TOTAL STOCK,10,250.50,"$2,505.00"
            03/01/2025,Z12345678,DIVIDEND RECEIVED,VTI,VANGUARD TOTAL STOCK,,,$ 45.67
            06/15/2025,Z12345678,YOU SOLD,AAPL,APPLE INC,50,195.00,"$9,750.00"
        """)
        p = tmp_path / "activity.csv"
        p.write_text(csv_content)
        result = import_csv(p)

        assert result.institution == "Fidelity"
        assert result.format_type == "fidelity_activity"
        assert len(result.transactions) == 3

        buy = result.transactions[0]
        assert buy.action == "buy"
        assert buy.symbol == "VTI"
        assert buy.amount == 2505.00

        div = result.transactions[1]
        assert div.action == "dividend"
        assert div.amount == 45.67

        sell = result.transactions[2]
        assert sell.action == "sell"
        assert sell.symbol == "AAPL"

    def test_generic_bank_csv(self, tmp_path: Path) -> None:
        """Parse a generic bank transaction CSV with interest detection."""
        csv_content = textwrap.dedent("""\
            Date,Description,Amount
            01/05/2025,INTEREST PAYMENT,12.34
            01/10/2025,GROCERY STORE,-85.50
            01/15/2025,DIRECT DEPOSIT,3500.00
        """)
        p = tmp_path / "bank.csv"
        p.write_text(csv_content)
        result = import_csv(p)

        assert result.format_type == "bank_transactions"
        assert len(result.transactions) == 3

        interest_txn = result.transactions[0]
        assert interest_txn.action == "interest"
        assert interest_txn.amount == 12.34

    def test_split_debit_credit_csv(self, tmp_path: Path) -> None:
        """Parse a bank CSV with separate debit and credit columns."""
        csv_content = textwrap.dedent("""\
            Date,Description,Debit,Credit
            01/05/2025,INTEREST PAYMENT,,50.00
            01/10/2025,CHECK 1234,100.00,
        """)
        p = tmp_path / "bank_split.csv"
        p.write_text(csv_content)
        result = import_csv(p)

        assert result.format_type == "bank_transactions_split"
        assert len(result.transactions) == 2

        interest_txn = result.transactions[0]
        assert interest_txn.amount == 50.00

        check_txn = result.transactions[1]
        assert check_txn.amount == -100.00

    def test_skips_preamble_lines(self, tmp_path: Path) -> None:
        """CSV with title lines before the actual header should be handled."""
        csv_content = textwrap.dedent("""\
            Fidelity Investments
            Account Positions as of 01/15/2025

            Account Name/Number,Symbol,Description,Quantity,Last Price,Current Value,Cost Basis Total
            Z12345678,VTI,VANGUARD TOTAL STOCK,50,$250.00,"$12,500.00","$10,000.00"
        """)
        p = tmp_path / "with_preamble.csv"
        p.write_text(csv_content)
        result = import_csv(p)

        assert result.institution == "Fidelity"
        assert len(result.holdings) == 1
        assert result.holdings[0].symbol == "VTI"
