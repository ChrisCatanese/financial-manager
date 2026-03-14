"""Tests for TaxProfile, TaxDocumentType, DocumentChecklist, and DocumentItem models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from financial_manager.models.filing_status import FilingStatus
from financial_manager.models.tax_document import (
    DocumentChecklist,
    DocumentItem,
    DocumentStatus,
    TaxDocumentType,
)
from financial_manager.models.tax_profile import (
    EmploymentType,
    InvestmentAccountType,
    TaxProfile,
)


class TestTaxDocumentType:
    """Tests for the TaxDocumentType enum."""

    def test_w2_exists(self) -> None:
        """W-2 type should exist."""
        assert TaxDocumentType.W2 == "w2"

    def test_all_1099_variants(self) -> None:
        """All common 1099 variants should be defined."""
        variants = [
            TaxDocumentType.FORM_1099_INT,
            TaxDocumentType.FORM_1099_DIV,
            TaxDocumentType.FORM_1099_B,
            TaxDocumentType.FORM_1099_R,
            TaxDocumentType.FORM_1099_K,
        ]
        assert all(isinstance(v, TaxDocumentType) for v in variants)

    def test_real_estate_types(self) -> None:
        """Closing disclosure and settlement statement types should exist."""
        assert TaxDocumentType.CLOSING_DISCLOSURE_PURCHASE.value == "closing_disclosure_purchase"
        assert TaxDocumentType.SETTLEMENT_STATEMENT.value == "settlement_statement"

    def test_solar_types(self) -> None:
        """Solar-related document types should exist."""
        assert TaxDocumentType.SOLAR_AGREEMENT.value == "solar_agreement"
        assert TaxDocumentType.SOLAR_RECEIPT.value == "solar_receipt"


class TestDocumentStatus:
    """Tests for document status tracking."""

    def test_status_progression(self) -> None:
        """Status values should represent a logical progression."""
        statuses = [s.value for s in DocumentStatus]
        assert "missing" in statuses
        assert "found" in statuses
        assert "extracted" in statuses
        assert "confirmed" in statuses


class TestDocumentItem:
    """Tests for DocumentItem model."""

    def test_default_missing_status(self) -> None:
        """New items should default to MISSING status."""
        item = DocumentItem(doc_type=TaxDocumentType.W2, label="W-2")
        assert item.status == DocumentStatus.MISSING
        assert item.source_path is None
        assert item.extracted_data == {}

    def test_required_defaults_true(self) -> None:
        """Items should be required by default."""
        item = DocumentItem(doc_type=TaxDocumentType.W2, label="W-2")
        assert item.required is True

    def test_optional_item(self) -> None:
        """Items can be marked optional."""
        item = DocumentItem(doc_type=TaxDocumentType.FORM_5498, label="5498", required=False)
        assert item.required is False


class TestDocumentChecklist:
    """Tests for the DocumentChecklist model."""

    def test_empty_checklist(self) -> None:
        """Empty checklist should have zero counts."""
        cl = DocumentChecklist(tax_year=2025)
        assert cl.total == 0
        assert cl.found_count == 0
        assert cl.required_missing == []

    def test_counts_with_items(self) -> None:
        """Counts should reflect item statuses."""
        cl = DocumentChecklist(
            tax_year=2025,
            items=[
                DocumentItem(doc_type=TaxDocumentType.W2, label="W-2"),
                DocumentItem(doc_type=TaxDocumentType.W2_SPOUSE, label="W-2 Spouse", status=DocumentStatus.FOUND),
                DocumentItem(
                    doc_type=TaxDocumentType.FORM_5498,
                    label="5498",
                    required=False,
                ),
            ],
        )
        assert cl.total == 3
        assert cl.found_count == 1
        assert len(cl.required_missing) == 1

    def test_update_status(self) -> None:
        """update_status should modify the correct item."""
        cl = DocumentChecklist(
            tax_year=2025,
            items=[DocumentItem(doc_type=TaxDocumentType.W2, label="W-2")],
        )
        result = cl.update_status(TaxDocumentType.W2, DocumentStatus.FOUND, source_path="/tmp/w2.pdf")
        assert result is True
        assert cl.items[0].status == DocumentStatus.FOUND
        assert cl.items[0].source_path == "/tmp/w2.pdf"

    def test_update_nonexistent_type(self) -> None:
        """update_status should return False for missing doc_type."""
        cl = DocumentChecklist(tax_year=2025, items=[])
        assert cl.update_status(TaxDocumentType.W2, DocumentStatus.FOUND) is False

    def test_get_item(self) -> None:
        """get_item should find items by type."""
        cl = DocumentChecklist(
            tax_year=2025,
            items=[DocumentItem(doc_type=TaxDocumentType.FORM_1098, label="1098")],
        )
        assert cl.get_item(TaxDocumentType.FORM_1098) is not None
        assert cl.get_item(TaxDocumentType.W2) is None


class TestTaxProfile:
    """Tests for the TaxProfile model."""

    def test_defaults(self) -> None:
        """Default profile should be MFJ with W-2 employment."""
        profile = TaxProfile()
        assert profile.filing_status == FilingStatus.MARRIED_FILING_JOINTLY
        assert profile.filer_employment == EmploymentType.W2_EMPLOYEE
        assert profile.tax_year == 2025
        assert profile.is_joint is True

    def test_single_not_joint(self) -> None:
        """Single filer should not be joint."""
        profile = TaxProfile(filing_status=FilingStatus.SINGLE)
        assert profile.is_joint is False

    def test_mfs_is_joint(self) -> None:
        """MFS should be considered joint (has spouse)."""
        profile = TaxProfile(filing_status=FilingStatus.MARRIED_FILING_SEPARATELY)
        assert profile.is_joint is True

    def test_investment_accounts(self) -> None:
        """Profile should accept investment account types."""
        profile = TaxProfile(
            investment_accounts=[InvestmentAccountType.BROKERAGE, InvestmentAccountType.ROTH_IRA],
        )
        assert len(profile.investment_accounts) == 2

    def test_homeowner_flags(self) -> None:
        """Real estate flags should be settable."""
        profile = TaxProfile(
            has_mortgage=True,
            purchased_home=True,
            has_property_tax=True,
            has_solar=True,
        )
        assert profile.has_mortgage is True
        assert profile.purchased_home is True
        assert profile.has_solar is True

    def test_invalid_year(self) -> None:
        """Invalid tax year should raise validation error."""
        with pytest.raises(ValidationError):
            TaxProfile(tax_year=2020)
