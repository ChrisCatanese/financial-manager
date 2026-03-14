"""FastAPI application — US Federal Tax Calculator API."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from financial_manager.engine.calculator import TaxCalculator
from financial_manager.engine.checklist import generate_checklist
from financial_manager.engine.extractor import extract_document
from financial_manager.engine.scanner import (
    match_scan_to_checklist,
    scan_folder,
)
from financial_manager.models.tax_document import (
    DocumentChecklist,
    DocumentStatus,
    TaxDocumentType,
)
from financial_manager.models.tax_input import TaxInput
from financial_manager.models.tax_profile import TaxProfile
from financial_manager.models.tax_result import TaxResult

logger = logging.getLogger(__name__)

app = FastAPI(
    title="US Federal Tax Calculator",
    description="Calculate US federal income tax with progressive brackets, deductions, and credits.",
    version="0.2.0",
)

# CORS — allow the Vite dev server and production frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_calculator = TaxCalculator()

# ── In-memory state (per-session) ─────────────────────────────────────
# In production this would be persisted; for now we keep it in memory.
_current_profile: TaxProfile | None = None
_current_checklist: DocumentChecklist | None = None


# ── Health ────────────────────────────────────────────────────────────


@app.get("/api/v1/health")
def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Simple status dict.
    """
    return {"status": "ok"}


# ── Tax Calculation ───────────────────────────────────────────────────


@app.post("/api/v1/calculate", response_model=TaxResult)
def calculate_tax(tax_input: TaxInput) -> TaxResult:
    """Calculate federal income tax for the given input.

    Args:
        tax_input: Income, filing status, deductions, and other parameters.

    Returns:
        Complete tax calculation result with bracket breakdown.
    """
    logger.info("API: /api/v1/calculate called")
    return _calculator.calculate(tax_input)


# ── Tax Profile ───────────────────────────────────────────────────────


@app.post("/api/v1/profile", response_model=TaxProfile)
def create_profile(profile: TaxProfile) -> TaxProfile:
    """Create or update the tax profile and regenerate the checklist.

    Args:
        profile: The filer's tax situation.

    Returns:
        The saved profile.
    """
    global _current_profile, _current_checklist
    _current_profile = profile
    _current_checklist = generate_checklist(profile)
    logger.info("Profile created: %s/%d", profile.filing_status.value, profile.tax_year)
    return profile


@app.get("/api/v1/profile")
def get_profile() -> TaxProfile | dict[str, str]:
    """Get the current tax profile.

    Returns:
        The current profile, or an error message.
    """
    if _current_profile is None:
        return {"error": "No profile created yet. POST to /api/v1/profile first."}
    return _current_profile


# ── Document Checklist ────────────────────────────────────────────────


@app.get("/api/v1/checklist")
def get_checklist() -> DocumentChecklist | dict[str, str]:
    """Get the current document checklist.

    Returns:
        The checklist, or an error if no profile exists.
    """
    if _current_checklist is None:
        return {"error": "No checklist generated. Create a profile first."}  # type: ignore[return-value]
    return _current_checklist


# ── Document Scanning ─────────────────────────────────────────────────


@app.post("/api/v1/documents/scan")
def scan_documents(folder_path: str | None = None) -> dict[str, object]:
    """Scan a local folder for tax documents and match to checklist.

    Args:
        folder_path: Override path to scan. Defaults to profile's document_source_path.

    Returns:
        Summary of scan results.
    """
    if _current_checklist is None:
        return {"error": "No checklist generated. Create a profile first."}

    path = folder_path
    if path is None and _current_profile is not None:
        path = _current_profile.document_source_path

    if path is None:
        return {"error": "No folder path provided and none configured in profile."}

    scan_results = scan_folder(path, tax_year=_current_checklist.tax_year)
    match_scan_to_checklist(scan_results, _current_checklist)

    return {
        "scanned_path": path,
        "files_found": len(scan_results),
        "checklist_matched": _current_checklist.found_count,
        "checklist_total": _current_checklist.total,
        "still_missing": [item.label for item in _current_checklist.required_missing],
    }


# ── Document Upload & Extraction ──────────────────────────────────────


@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile, doc_type: str) -> dict[str, object]:
    """Upload a tax document, extract data, and update the checklist.

    Args:
        file: The uploaded file.
        doc_type: The TaxDocumentType value string.

    Returns:
        Extraction results and updated checklist status.
    """
    if _current_checklist is None:
        return {"error": "No checklist generated. Create a profile first."}

    try:
        dtype = TaxDocumentType(doc_type)
    except ValueError:
        return {"error": "Invalid document type", "valid_types": [t.value for t in TaxDocumentType]}

    # Save to temp file for extraction
    suffix = Path(file.filename or "upload.pdf").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Extract data
    extracted = extract_document(tmp_path, dtype)

    # Update checklist
    _current_checklist.update_status(
        doc_type=dtype,
        status=DocumentStatus.EXTRACTED if extracted else DocumentStatus.UPLOADED,
        source_path=tmp_path,
        extracted_data=extracted,
    )

    return {
        "filename": file.filename,
        "doc_type": dtype.value,
        "status": "extracted" if extracted else "uploaded",
        "extracted_fields": len(extracted),
        "data": extracted,
    }


# ── Extracted Data Summary ────────────────────────────────────────────


@app.get("/api/v1/documents/extracted")
def get_extracted_data() -> dict[str, object]:
    """Get all extracted data from processed documents.

    Returns:
        Aggregated extracted data organized by document type.
    """
    if _current_checklist is None:
        return {"error": "No checklist generated. Create a profile first."}

    extracted: dict[str, dict[str, str | float | None]] = {}
    for item in _current_checklist.items:
        if item.extracted_data:
            extracted[item.doc_type.value] = item.extracted_data

    return {
        "tax_year": _current_checklist.tax_year,
        "documents_with_data": len(extracted),
        "data": extracted,
    }
