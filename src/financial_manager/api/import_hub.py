"""API routes for the financial data import hub.

Handles:
- Listing configured accounts and their iCloud destination folders
- Uploading files to the organized iCloud folder structure
- Scanning existing files already in iCloud
- Assessing uploaded/imported files (format detection, schema validation)
- User overrides for auto-detected fields

The iCloud folder structure is organized as::

    {icloud_base}/Tax/{year}/
    ├── Joint/
    │   ├── Banking/        ← Wells Fargo, etc.
    │   └── Brokerage/      ← Fidelity, etc.
    ├── Chris/
    │   ├── Employment/     ← W-2, pay stubs
    │   └── Retirement/     ← 401k, IRA
    ├── Sarah/
    │   ├── Employment/
    │   └── Retirement/
    ├── Property/
    │   ├── House/
    │   └── Condo/
    └── Exports/            ← Raw CSV/OFX/QFX imports
        ├── Fidelity/
        ├── Wells Fargo/
        └── State Farm/
"""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, UploadFile

from financial_manager.connectors.csv_importer import (
    CsvImportResult,
    import_csv,
)
from financial_manager.connectors.data_mapper import (
    ImportSummary,
    map_csv_results,
    map_ofx_results,
    merge_summaries,
)
from financial_manager.connectors.ofx_importer import (
    OfxImportResult,
    import_ofx,
)
from financial_manager.user_config import UserConfig, load_user_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/import", tags=["import"])


# ── iCloud folder structure ───────────────────────────────────────────

_ICLOUD_BASE = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Family"


@dataclass
class FolderNode:
    """A node in the iCloud destination folder tree.

    Attributes:
        name: Folder display name.
        path: Full filesystem path.
        category: Organizational category (owner/property/exports).
        children: Sub-folders.
        file_count: Number of files already present.
    """

    name: str = ""
    path: str = ""
    category: str = ""
    children: list[FolderNode] = field(default_factory=list)
    file_count: int = 0


def _build_folder_tree(config: UserConfig) -> list[FolderNode]:
    """Build the organized iCloud folder tree from user config.

    Args:
        config: Loaded user configuration.

    Returns:
        List of top-level folder nodes.
    """
    year = str(config.tax_year)
    base = _ICLOUD_BASE / "Tax" / year
    nodes: list[FolderNode] = []

    # ── Owner-based folders ───────────────────────────────────────
    owner_map: dict[str, str] = {}
    if config.primary_filer.first_name:
        owner_map["primary"] = config.primary_filer.first_name
    if config.spouse.first_name:
        owner_map["spouse"] = config.spouse.first_name

    # Joint
    joint_path = base / "Joint"
    joint_children = [
        FolderNode(name="Banking", path=str(joint_path / "Banking"), category="banking"),
        FolderNode(name="Brokerage", path=str(joint_path / "Brokerage"), category="brokerage"),
        FolderNode(name="Insurance", path=str(joint_path / "Insurance"), category="insurance"),
    ]
    for child in joint_children:
        child.file_count = _count_files(Path(child.path))
    nodes.append(FolderNode(
        name="Joint",
        path=str(joint_path),
        category="joint",
        children=joint_children,
        file_count=_count_files(joint_path),
    ))

    # Per-filer
    for role, name in owner_map.items():
        filer_path = base / name
        filer_children = [
            FolderNode(name="Employment", path=str(filer_path / "Employment"), category="employment"),
            FolderNode(name="Retirement", path=str(filer_path / "Retirement"), category="retirement"),
        ]
        for child in filer_children:
            child.file_count = _count_files(Path(child.path))
        nodes.append(FolderNode(
            name=name,
            path=str(filer_path),
            category=role,
            children=filer_children,
            file_count=_count_files(filer_path),
        ))

    # ── Property folders ──────────────────────────────────────────
    if config.properties:
        prop_path = base / "Property"
        prop_children = []
        for prop in config.properties:
            label = prop.label or prop.address
            child_path = prop_path / label
            prop_children.append(FolderNode(
                name=label,
                path=str(child_path),
                category="property",
                file_count=_count_files(child_path),
            ))
        nodes.append(FolderNode(
            name="Property",
            path=str(prop_path),
            category="property",
            children=prop_children,
            file_count=_count_files(prop_path),
        ))

    # ── Exports folder (raw institution files) ────────────────────
    exports_path = base / "Exports"
    export_children = []
    for acct in config.accounts:
        inst_path = exports_path / acct.institution
        export_children.append(FolderNode(
            name=acct.institution,
            path=str(inst_path),
            category="exports",
            file_count=_count_files(inst_path),
        ))
    nodes.append(FolderNode(
        name="Exports",
        path=str(exports_path),
        category="exports",
        children=export_children,
        file_count=_count_files(exports_path),
    ))

    return nodes


def _count_files(path: Path) -> int:
    """Count files in a directory (non-recursive).

    Args:
        path: Directory to count.

    Returns:
        Number of files, or 0 if directory doesn't exist.
    """
    if not path.is_dir():
        return 0
    return sum(1 for f in path.iterdir() if f.is_file() and not f.name.startswith("."))


# ── File assessment ───────────────────────────────────────────────────


@dataclass
class FileAssessment:
    """Assessment result for an uploaded/scanned file.

    Attributes:
        filename: Original filename.
        file_path: Current filesystem path.
        file_size: File size in bytes.
        file_type: Detected file type (csv, ofx, qfx, pdf, image, other).
        detected_format: Auto-detected institution/format (e.g. "Fidelity positions").
        detected_institution: Detected institution name.
        detected_owner: Suggested owner (joint, primary, spouse).
        suggested_destination: Suggested iCloud destination folder path.
        suggested_category: Suggested category (banking, brokerage, employment, etc.).
        record_count: Number of parsed records (transactions/holdings).
        date_range: Date range of transactions (if applicable).
        preview_data: First few records for user review.
        warnings: Any issues found.
        can_import: Whether the file can be fully imported.
    """

    filename: str = ""
    file_path: str = ""
    file_size: int = 0
    file_type: str = "other"
    detected_format: str = ""
    detected_institution: str = ""
    detected_owner: str = "joint"
    suggested_destination: str = ""
    suggested_category: str = ""
    record_count: int = 0
    date_range: str = ""
    preview_data: list[dict[str, object]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    can_import: bool = True


def _detect_file_type(path: Path) -> str:
    """Detect file type from extension.

    Args:
        path: File path.

    Returns:
        File type string.
    """
    ext = path.suffix.lower()
    type_map = {
        ".csv": "csv",
        ".ofx": "ofx",
        ".qfx": "qfx",
        ".pdf": "pdf",
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".heic": "image",
        ".tif": "image",
        ".tiff": "image",
    }
    return type_map.get(ext, "other")


def _assess_csv(path: Path, config: UserConfig) -> FileAssessment:
    """Assess a CSV file for import readiness.

    Args:
        path: Path to the CSV file.
        config: User configuration.

    Returns:
        FileAssessment with detected format and preview.
    """
    assessment = FileAssessment(
        filename=path.name,
        file_path=str(path),
        file_size=path.stat().st_size,
        file_type="csv",
    )

    try:
        result = import_csv(path)
        assessment.detected_format = result.format_type
        assessment.detected_institution = result.institution
        assessment.warnings = list(result.warnings)

        if result.holdings:
            assessment.record_count = len(result.holdings)
            assessment.preview_data = [
                {
                    "symbol": h.symbol,
                    "description": h.description,
                    "quantity": h.quantity,
                    "value": h.current_value,
                    "cost_basis": h.cost_basis_total,
                }
                for h in result.holdings[:5]
            ]

        if result.transactions:
            assessment.record_count += len(result.transactions)
            dates = [t.date for t in result.transactions if t.date]
            if dates:
                assessment.date_range = f"{min(dates)} to {max(dates)}"
            assessment.preview_data = [
                {
                    "date": t.date,
                    "description": t.description,
                    "action": t.action,
                    "amount": t.amount,
                    "symbol": t.symbol,
                }
                for t in result.transactions[:5]
            ]

        # Match institution to configured account
        _match_to_account(assessment, config)

    except Exception as exc:
        assessment.warnings.append(str(exc))
        assessment.can_import = False
        logger.warning("CSV assessment failed for %s: %s", path.name, exc)

    return assessment


def _assess_ofx(path: Path, config: UserConfig) -> FileAssessment:
    """Assess an OFX/QFX file for import readiness.

    Args:
        path: Path to the OFX/QFX file.
        config: User configuration.

    Returns:
        FileAssessment with detected format and preview.
    """
    assessment = FileAssessment(
        filename=path.name,
        file_path=str(path),
        file_size=path.stat().st_size,
        file_type=path.suffix.lower().lstrip("."),
    )

    try:
        result = import_ofx(path)
        assessment.detected_institution = result.institution
        assessment.detected_format = f"OFX ({result.institution or 'unknown'})"
        assessment.warnings = list(result.warnings)

        total_records = len(result.transactions) + len(result.investment_transactions)
        assessment.record_count = total_records

        if result.transactions:
            dates = [t.date for t in result.transactions if t.date]
            if dates:
                assessment.date_range = f"{min(dates)} to {max(dates)}"
            assessment.preview_data = [
                {
                    "date": t.date,
                    "name": t.name,
                    "amount": t.amount,
                    "type": t.tran_type,
                }
                for t in result.transactions[:5]
            ]
        elif result.investment_transactions:
            dates = [t.date for t in result.investment_transactions if t.date]
            if dates:
                assessment.date_range = f"{min(dates)} to {max(dates)}"
            assessment.preview_data = [
                {
                    "date": t.date,
                    "security": t.security_id,
                    "type": t.tran_type,
                    "total": t.total,
                }
                for t in result.investment_transactions[:5]
            ]

        _match_to_account(assessment, config)

    except Exception as exc:
        assessment.warnings.append(str(exc))
        assessment.can_import = False
        logger.warning("OFX assessment failed for %s: %s", path.name, exc)

    return assessment


def _assess_document(path: Path, _config: UserConfig) -> FileAssessment:
    """Assess a PDF or image for import (no parsing, just metadata).

    Args:
        path: Path to the file.
        _config: User configuration (unused for now).

    Returns:
        FileAssessment with basic metadata.
    """
    return FileAssessment(
        filename=path.name,
        file_path=str(path),
        file_size=path.stat().st_size,
        file_type=_detect_file_type(path),
        detected_format="document",
        can_import=True,
    )


def _match_to_account(assessment: FileAssessment, config: UserConfig) -> None:
    """Match a detected institution to a configured account.

    Sets the owner, suggested destination, and category on the assessment.

    Args:
        assessment: Assessment to update.
        config: User configuration.
    """
    institution = assessment.detected_institution.lower()
    year = str(config.tax_year)
    base = _ICLOUD_BASE / "Tax" / year

    for acct in config.accounts:
        if acct.institution.lower() in institution or institution in acct.institution.lower():
            assessment.detected_owner = acct.owner
            assessment.suggested_category = acct.account_type

            # Route to Exports/{Institution}/
            dest = base / "Exports" / acct.institution
            assessment.suggested_destination = str(dest)
            return

    # Fallback: put in Exports/Other/
    assessment.suggested_destination = str(base / "Exports" / "Other")


# ── Scanned file record ──────────────────────────────────────────────


@dataclass
class ScannedFile:
    """A file already present in the iCloud folder structure.

    Attributes:
        filename: File name.
        path: Full path.
        folder: Parent folder name.
        category: Folder category.
        owner: Detected owner.
        file_type: csv/ofx/qfx/pdf/image/other.
        file_size: Size in bytes.
        modified: Last modified timestamp.
    """

    filename: str = ""
    path: str = ""
    folder: str = ""
    category: str = ""
    owner: str = ""
    file_type: str = ""
    file_size: int = 0
    modified: str = ""


# ── In-memory state ──────────────────────────────────────────────────

_cached_config: UserConfig | None = None


def _get_config() -> UserConfig:
    """Load or return cached user config.

    Returns:
        UserConfig instance.
    """
    global _cached_config
    if _cached_config is None:
        _cached_config = load_user_config()
    return _cached_config


# ── API Routes ────────────────────────────────────────────────────────


@router.get("/config")
def get_import_config() -> dict[str, object]:
    """Get the import configuration: accounts, folder tree, tax year.

    Returns:
        Configuration summary for the import UI.
    """
    config = _get_config()
    tree = _build_folder_tree(config)

    accounts = []
    for acct in config.accounts:
        accounts.append({
            "institution": acct.institution,
            "account_type": acct.account_type,
            "owner": acct.owner,
            "expected_forms": acct.expected_forms,
            "export_path": acct.export_path,
        })

    filers = []
    if config.primary_filer.first_name:
        filers.append({
            "name": f"{config.primary_filer.first_name} {config.primary_filer.last_name}",
            "role": "primary",
        })
    if config.spouse.first_name:
        filers.append({
            "name": f"{config.spouse.first_name} {config.spouse.last_name}",
            "role": "spouse",
        })

    properties = [
        {"label": p.label, "address": p.address, "role": p.role}
        for p in config.properties
    ]

    return {
        "tax_year": config.tax_year,
        "filing_status": config.filing_status,
        "filers": filers,
        "accounts": accounts,
        "properties": properties,
        "folder_tree": [asdict(n) for n in tree],
        "icloud_base": str(_ICLOUD_BASE / "Tax" / str(config.tax_year)),
    }


@router.get("/files")
def list_existing_files() -> dict[str, object]:
    """Scan the iCloud tax folder tree and list all existing files.

    Returns:
        List of ScannedFile records grouped by category.
    """
    config = _get_config()
    year = str(config.tax_year)
    base = _ICLOUD_BASE / "Tax" / year
    files: list[dict[str, object]] = []

    if not base.is_dir():
        return {"base_path": str(base), "exists": False, "files": [], "total": 0}

    for item in sorted(base.rglob("*")):
        if not item.is_file() or item.name.startswith("."):
            continue

        rel = item.relative_to(base)
        parts = rel.parts
        folder = parts[0] if parts else ""
        subfolder = parts[1] if len(parts) > 1 else ""

        # Determine owner / category from folder structure
        owner = "joint"
        category = folder.lower()

        if config.primary_filer.first_name and folder == config.primary_filer.first_name:
            owner = "primary"
            category = subfolder.lower() if subfolder else "general"
        elif config.spouse.first_name and folder == config.spouse.first_name:
            owner = "spouse"
            category = subfolder.lower() if subfolder else "general"
        elif folder == "Joint":
            category = subfolder.lower() if subfolder else "joint"
        elif folder == "Property":
            category = "property"
        elif folder == "Exports":
            category = "exports"

        stat = item.stat()
        files.append(asdict(ScannedFile(
            filename=item.name,
            path=str(item),
            folder=str(rel.parent),
            category=category,
            owner=owner,
            file_type=_detect_file_type(item),
            file_size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime).isoformat(),
        )))

    return {
        "base_path": str(base),
        "exists": True,
        "files": files,
        "total": len(files),
    }


@router.post("/upload")
async def upload_file(
    file: UploadFile,
    destination: str = "",
    owner: str = "joint",
    category: str = "",
) -> dict[str, object]:
    """Upload a file to the iCloud folder structure.

    The file is saved to the organized iCloud tree, NOT into this project.
    If no destination is specified, the file is assessed and a destination
    is auto-suggested.

    Args:
        file: The uploaded file.
        destination: Override destination folder path.
        owner: Override owner (joint/primary/spouse).
        category: Override category.

    Returns:
        Assessment of the uploaded file and its final destination.
    """
    config = _get_config()
    year = str(config.tax_year)
    base = _ICLOUD_BASE / "Tax" / year

    # Save upload to a staging area first
    staging = base / ".staging"
    staging.mkdir(parents=True, exist_ok=True)
    staging_path = staging / (file.filename or "upload")

    content = await file.read()
    staging_path.write_bytes(content)

    # Assess the file
    file_type = _detect_file_type(staging_path)
    if file_type == "csv":
        assessment = _assess_csv(staging_path, config)
    elif file_type in ("ofx", "qfx"):
        assessment = _assess_ofx(staging_path, config)
    else:
        assessment = _assess_document(staging_path, config)

    # Apply user overrides
    if destination:
        assessment.suggested_destination = destination
    if owner != "joint" or not assessment.detected_owner:
        assessment.detected_owner = owner
    if category:
        assessment.suggested_category = category

    # Move file to final destination
    dest_path = Path(assessment.suggested_destination)
    dest_path.mkdir(parents=True, exist_ok=True)
    final_path = dest_path / staging_path.name
    if final_path.exists():
        # Add timestamp to avoid overwriting
        stem = final_path.stem
        suffix = final_path.suffix
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_path = dest_path / f"{stem}_{ts}{suffix}"
    shutil.move(str(staging_path), str(final_path))
    assessment.file_path = str(final_path)

    # Clean staging
    with contextlib.suppress(OSError):
        staging.rmdir()

    return {
        "status": "uploaded",
        "assessment": asdict(assessment),
        "final_path": str(final_path),
        "icloud_relative": str(final_path.relative_to(_ICLOUD_BASE)),
    }


@router.post("/assess")
async def assess_file(file: UploadFile) -> dict[str, object]:
    """Assess a file without saving it — preview format detection and mapping.

    Args:
        file: The file to assess.

    Returns:
        FileAssessment with detected format, institution, preview data.
    """
    config = _get_config()

    # Write to temp for assessment
    import tempfile

    suffix = Path(file.filename or "upload").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    file_type = _detect_file_type(tmp_path)
    if file_type == "csv":
        assessment = _assess_csv(tmp_path, config)
    elif file_type in ("ofx", "qfx"):
        assessment = _assess_ofx(tmp_path, config)
    else:
        assessment = _assess_document(tmp_path, config)

    # Clean up temp file
    with contextlib.suppress(OSError):
        tmp_path.unlink()

    return {"assessment": asdict(assessment)}


@router.post("/scan-exports")
def scan_export_folders() -> dict[str, object]:
    """Scan all configured export_path folders for new files.

    Returns:
        List of assessments for files found in export folders.
    """
    config = _get_config()
    assessments: list[dict[str, object]] = []

    for acct in config.accounts:
        if not acct.export_path:
            continue

        export_dir = Path(os.path.expanduser(acct.export_path))
        if not export_dir.is_dir():
            logger.info("Export path does not exist: %s", export_dir)
            continue

        for item in sorted(export_dir.iterdir()):
            if not item.is_file() or item.name.startswith("."):
                continue

            file_type = _detect_file_type(item)
            if file_type in ("csv", "ofx", "qfx"):
                assessment = _assess_csv(item, config) if file_type == "csv" else _assess_ofx(item, config)
                assessment.detected_owner = acct.owner
                assessments.append(asdict(assessment))

    return {
        "accounts_scanned": len([a for a in config.accounts if a.export_path]),
        "files_found": len(assessments),
        "assessments": assessments,
    }


@router.post("/process")
def process_imports(tax_year: int = 0) -> dict[str, object]:
    """Process all files in the Exports folder and generate a tax summary.

    Args:
        tax_year: Override tax year. Defaults to config value.

    Returns:
        ImportSummary as dict with tax-relevant totals.
    """
    config = _get_config()
    year = tax_year or config.tax_year
    exports_path = _ICLOUD_BASE / "Tax" / str(year) / "Exports"

    csv_results: list[CsvImportResult] = []
    ofx_results: list[OfxImportResult] = []

    if exports_path.is_dir():
        for item in sorted(exports_path.rglob("*")):
            if not item.is_file() or item.name.startswith("."):
                continue

            file_type = _detect_file_type(item)
            try:
                if file_type == "csv":
                    csv_results.append(import_csv(item))
                elif file_type in ("ofx", "qfx"):
                    ofx_results.append(import_ofx(item))
            except Exception as exc:
                logger.warning("Failed to process %s: %s", item.name, exc)

    csv_summary = map_csv_results(csv_results, tax_year=year) if csv_results else ImportSummary(tax_year=year)
    ofx_summary = map_ofx_results(ofx_results, tax_year=year) if ofx_results else ImportSummary(tax_year=year)
    combined = merge_summaries(csv_summary, ofx_summary)

    return {
        "tax_year": combined.tax_year,
        "sources_imported": combined.sources_imported,
        "total_interest": combined.total_interest,
        "total_ordinary_dividends": combined.total_ordinary_dividends,
        "total_qualified_dividends": combined.total_qualified_dividends,
        "total_short_term_gains": combined.total_short_term_gains,
        "total_long_term_gains": combined.total_long_term_gains,
        "interest_income": [asdict(i) for i in combined.interest_income],
        "dividend_income": [asdict(d) for d in combined.dividend_income],
        "capital_gains": [asdict(g) for g in combined.capital_gains],
        "taxable_transactions": [asdict(t) for t in combined.taxable_transactions],
        "warnings": combined.warnings,
    }


@router.post("/move-to-icloud")
def move_export_to_icloud(
    source_path: str,
    destination: str = "",
    owner: str = "",
    category: str = "",
) -> dict[str, object]:
    """Move a file from an export folder into the organized iCloud structure.

    Args:
        source_path: Full path to the source file.
        destination: Override destination folder. Auto-detected if empty.
        owner: Override owner.
        category: Override category.

    Returns:
        Result with final path and assessment.
    """
    config = _get_config()
    source = Path(source_path)

    if not source.is_file():
        return {"error": f"File not found: {source_path}"}

    # Assess
    file_type = _detect_file_type(source)
    if file_type == "csv":
        assessment = _assess_csv(source, config)
    elif file_type in ("ofx", "qfx"):
        assessment = _assess_ofx(source, config)
    else:
        assessment = _assess_document(source, config)

    # Apply overrides
    if destination:
        assessment.suggested_destination = destination
    if owner:
        assessment.detected_owner = owner
    if category:
        assessment.suggested_category = category

    # Copy (not move — keep original in Downloads)
    dest_path = Path(assessment.suggested_destination)
    dest_path.mkdir(parents=True, exist_ok=True)
    final_path = dest_path / source.name
    if final_path.exists():
        stem = final_path.stem
        suffix = final_path.suffix
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_path = dest_path / f"{stem}_{ts}{suffix}"
    shutil.copy2(str(source), str(final_path))

    return {
        "status": "copied",
        "source": str(source),
        "final_path": str(final_path),
        "assessment": asdict(assessment),
    }
