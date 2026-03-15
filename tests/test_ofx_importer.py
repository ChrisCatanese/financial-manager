"""Tests for the OFX/QFX importer module."""

from __future__ import annotations

from pathlib import Path

from financial_manager.connectors.ofx_importer import (
    _mask_account,
    _parse_ofx_date,
    _sgml_to_xml,
    import_ofx,
)

# ── Date parsing ──────────────────────────────────────────────────────


class TestParseOfxDate:
    """Tests for OFX date string parsing."""

    def test_standard_date(self) -> None:
        """Parse a plain YYYYMMDD date to ISO format."""
        assert _parse_ofx_date("20250115") == "2025-01-15"

    def test_with_time(self) -> None:
        """Parse a date with time suffix, returning only the date portion."""
        assert _parse_ofx_date("20250115120000") == "2025-01-15"

    def test_empty_string(self) -> None:
        """Return empty string for empty input."""
        assert _parse_ofx_date("") == ""

    def test_unparseable(self) -> None:
        """Return the original string when the format is unrecognised."""
        assert _parse_ofx_date("not-a-date") == "not-a-date"


# ── Account masking ───────────────────────────────────────────────────


class TestMaskAccount:
    """Tests for account number masking."""

    def test_long_account(self) -> None:
        """Mask a long account number, keeping only the last 4 digits."""
        assert _mask_account("123456789") == "****6789"

    def test_short_account(self) -> None:
        """Return a short account number unchanged."""
        assert _mask_account("1234") == "1234"

    def test_empty(self) -> None:
        """Return an empty string for empty input."""
        assert _mask_account("") == ""


# ── SGML-to-XML conversion ───────────────────────────────────────────


class TestSgmlToXml:
    """Tests for OFX SGML-to-XML conversion."""

    def test_closes_unclosed_tags(self) -> None:
        """Add closing tags for bare OFX value elements."""
        sgml = "<ACCTID>12345\n<ACCTTYPE>CHECKING\n"
        xml = _sgml_to_xml(sgml)
        assert "</ACCTID>" in xml
        assert "</ACCTTYPE>" in xml

    def test_strips_headers(self) -> None:
        """Remove OFX header lines from SGML content."""
        sgml = (
            "OFXHEADER:100\n"
            "DATA:OFXSGML\n"
            "VERSION:102\n"
            "<OFX><ACCTID>999</OFX>\n"
        )
        xml = _sgml_to_xml(sgml)
        assert "OFXHEADER" not in xml
        assert "<OFX>" in xml


# ── Full OFX import ───────────────────────────────────────────────────


class TestImportOfx:
    """Tests for end-to-end OFX file import."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Return a warning when the OFX file does not exist."""
        result = import_ofx(tmp_path / "missing.ofx")
        assert len(result.warnings) == 1
        assert "not found" in result.warnings[0].lower()

    def test_wrong_extension(self, tmp_path: Path) -> None:
        """Return a warning for a file with an unsupported extension."""
        p = tmp_path / "data.csv"
        p.write_text("not ofx")
        result = import_ofx(p)
        assert len(result.warnings) == 1
        assert "extension" in result.warnings[0].lower()

    def test_bank_ofx_xml(self, tmp_path: Path) -> None:
        """Parse a minimal OFX XML file with two bank transactions."""
        ofx_content = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<OFX>"
            "<SIGNONMSGSRSV1><SONRS><STATUS><CODE>0</CODE></STATUS></SONRS></SIGNONMSGSRSV1>"
            "<BANKMSGSRSV1><STMTTRNRS><STMTRS>"
            "<BANKACCTFROM><ACCTID>123456789</ACCTID><ACCTTYPE>CHECKING</ACCTTYPE></BANKACCTFROM>"
            "<BANKTRANLIST>"
            "<DTSTART>20250101</DTSTART><DTEND>20250131</DTEND>"
            "<STMTTRN><TRNTYPE>INT</TRNTYPE><DTPOSTED>20250115</DTPOSTED>"
            "<TRNAMT>12.50</TRNAMT><FITID>T001</FITID><NAME>INTEREST PAYMENT</NAME></STMTTRN>"
            "<STMTTRN><TRNTYPE>DEBIT</TRNTYPE><DTPOSTED>20250120</DTPOSTED>"
            "<TRNAMT>-85.00</TRNAMT><FITID>T002</FITID><NAME>GROCERY STORE</NAME></STMTTRN>"
            "</BANKTRANLIST>"
            "</STMTRS></STMTTRNRS></BANKMSGSRSV1>"
            "</OFX>"
        )
        p = tmp_path / "bank.ofx"
        p.write_text(ofx_content)
        result = import_ofx(p)

        assert len(result.transactions) == 2
        assert result.account_id == "****6789"
        assert result.account_type == "CHECKING"
        assert result.date_start == "2025-01-01"
        assert result.date_end == "2025-01-31"

        interest = result.transactions[0]
        assert interest.tran_type == "INT"
        assert interest.date == "2025-01-15"
        assert interest.amount == 12.50
        assert interest.name == "INTEREST PAYMENT"

        debit = result.transactions[1]
        assert debit.tran_type == "DEBIT"
        assert debit.amount == -85.00

    def test_empty_result_for_malformed(self, tmp_path: Path) -> None:
        """Return an empty result with a warning for a malformed OFX file."""
        p = tmp_path / "bad.ofx"
        p.write_text("<<<this is not valid xml or sgml>>>")
        result = import_ofx(p)
        assert len(result.transactions) == 0
        assert len(result.warnings) >= 1
