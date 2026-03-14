"""Models for tax document types, classification, and checklist tracking."""

from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field


class TaxDocumentType(str, enum.Enum):
    """IRS form types and common tax-related documents.

    Each value corresponds to a standard IRS form or supporting document
    commonly needed for US federal tax filing.
    """

    # ── Income ────────────────────────────────────────────────────────
    W2 = "w2"
    W2_SPOUSE = "w2_spouse"
    FORM_1099_INT = "1099_int"
    FORM_1099_DIV = "1099_div"
    FORM_1099_B = "1099_b"
    FORM_1099_R = "1099_r"
    FORM_1099_K = "1099_k"
    FORM_1099_MISC = "1099_misc"
    FORM_1099_NEC = "1099_nec"
    FORM_1099_G = "1099_g"
    FORM_1099_SSA = "1099_ssa"
    FORM_1099_CONSOLIDATED = "1099_consolidated"

    # ── Deductions / Credits ──────────────────────────────────────────
    FORM_1098 = "1098"
    FORM_1098_T = "1098_t"
    PROPERTY_TAX_BILL = "property_tax_bill"
    CHARITABLE_RECEIPTS = "charitable_receipts"
    MEDICAL_EXPENSES = "medical_expenses"
    SOLAR_AGREEMENT = "solar_agreement"
    SOLAR_RECEIPT = "solar_receipt"
    ENERGY_CREDIT_CERT = "energy_credit_cert"

    # ── Real Estate ───────────────────────────────────────────────────
    CLOSING_DISCLOSURE_PURCHASE = "closing_disclosure_purchase"
    CLOSING_DISCLOSURE_SALE = "closing_disclosure_sale"
    SETTLEMENT_STATEMENT = "settlement_statement"
    HOME_SALE_1099S = "1099_s"

    # ── Retirement / HSA ──────────────────────────────────────────────
    FORM_5498 = "5498"
    FORM_5498_SA = "5498_sa"
    FORM_1099_SA = "1099_sa"

    # ── Supporting / Prior Year ───────────────────────────────────────
    PRIOR_YEAR_RETURN = "prior_year_return"
    IDENTITY_DOCUMENT = "identity_document"
    PAY_STUB = "pay_stub"
    BANK_STATEMENT = "bank_statement"

    # ── Catch-all ─────────────────────────────────────────────────────
    OTHER = "other"


class DocumentStatus(str, enum.Enum):
    """Tracking status for a single checklist item."""

    MISSING = "missing"
    FOUND = "found"
    UPLOADED = "uploaded"
    EXTRACTED = "extracted"
    CONFIRMED = "confirmed"


class DocumentItem(BaseModel):
    """A single item on the tax document checklist.

    Attributes:
        doc_type: The IRS form or document type expected.
        label: Human-readable name for display.
        description: Why this document is needed and where to get it.
        required: Whether the filer must provide this document.
        status: Current tracking status.
        source_path: Path to the discovered or uploaded file.
        extracted_data: Key-value pairs extracted from the document.
        matched_at: When the document was found or uploaded.
    """

    doc_type: TaxDocumentType
    label: str
    description: str = ""
    required: bool = True
    status: DocumentStatus = DocumentStatus.MISSING
    source_path: str | None = None
    extracted_data: dict[str, str | float | None] = Field(default_factory=dict)
    matched_at: datetime | None = None


class DocumentChecklist(BaseModel):
    """Complete checklist of documents needed for a tax filing.

    Attributes:
        tax_year: The tax year being filed.
        items: Ordered list of document checklist items.
        generated_at: When the checklist was created.
    """

    tax_year: int
    items: list[DocumentItem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)

    @property
    def total(self) -> int:
        """Total number of checklist items."""
        return len(self.items)

    @property
    def found_count(self) -> int:
        """Number of items with status beyond MISSING."""
        return sum(1 for item in self.items if item.status != DocumentStatus.MISSING)

    @property
    def required_missing(self) -> list[DocumentItem]:
        """Required items still missing."""
        return [item for item in self.items if item.required and item.status == DocumentStatus.MISSING]

    def get_item(self, doc_type: TaxDocumentType) -> DocumentItem | None:
        """Find a checklist item by document type.

        Args:
            doc_type: The document type to look up.

        Returns:
            The matching DocumentItem, or None.
        """
        for item in self.items:
            if item.doc_type == doc_type:
                return item
        return None

    def update_status(
        self,
        doc_type: TaxDocumentType,
        status: DocumentStatus,
        source_path: str | None = None,
        extracted_data: dict[str, str | float | None] | None = None,
    ) -> bool:
        """Update the status of a checklist item.

        Args:
            doc_type: The document type to update.
            status: New status.
            source_path: Path to the file, if applicable.
            extracted_data: Extracted key-value data, if applicable.

        Returns:
            True if the item was found and updated.
        """
        item = self.get_item(doc_type)
        if item is None:
            return False
        item.status = status
        if source_path is not None:
            item.source_path = source_path
        if extracted_data is not None:
            item.extracted_data.update(extracted_data)
        if status != DocumentStatus.MISSING:
            item.matched_at = datetime.now()
        return True
