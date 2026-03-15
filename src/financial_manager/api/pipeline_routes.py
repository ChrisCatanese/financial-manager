"""API routes for running the tax pipeline and viewing results.

Provides endpoints to:
- Run the document assembler (scan → extract → assemble tax picture)
- Run the financial data importer (CSV/OFX → tax summaries)
- Run the full tax calculation from assembled data
- Get a combined pipeline view for the dashboard
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter

from financial_manager.connectors.csv_importer import import_csv
from financial_manager.connectors.data_mapper import (
    ImportSummary,
    map_csv_results,
    map_ofx_results,
    merge_summaries,
)
from financial_manager.connectors.ofx_importer import import_ofx
from financial_manager.engine.assembler import TaxPicture, assemble_tax_picture
from financial_manager.engine.calculator import TaxCalculator
from financial_manager.engine.intake import get_folder_configs, scan_multiple_folders
from financial_manager.models.filing_status import FilingStatus
from financial_manager.models.tax_input import TaxInput
from financial_manager.user_config import UserConfig, load_user_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

_calculator = TaxCalculator()
_ICLOUD_BASE = Path.home() / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Family"


def _build_tax_input_from_picture(
    picture: TaxPicture,
    import_summary: ImportSummary | None = None,
) -> TaxInput:
    """Build a TaxInput from the assembled TaxPicture + import data.

    Merges document-extracted data with financial import data to produce
    the most complete tax input possible.

    Args:
        picture: Assembled tax picture from documents.
        import_summary: Optional financial data import summary.

    Returns:
        TaxInput ready for the calculator.
    """
    inc = picture.income
    ded = picture.deductions
    wh = picture.withholding

    # Merge financial import data if available
    extra_interest = 0.0
    extra_dividends = 0.0
    extra_qualified_dividends = 0.0
    extra_st_gains = 0.0
    extra_lt_gains = 0.0

    if import_summary:
        extra_interest = import_summary.total_interest
        extra_dividends = import_summary.total_ordinary_dividends
        extra_qualified_dividends = import_summary.total_qualified_dividends
        extra_st_gains = import_summary.total_short_term_gains
        extra_lt_gains = import_summary.total_long_term_gains

    # Total gross income
    total_interest = inc.taxable_interest + extra_interest
    total_dividends = inc.ordinary_dividends + extra_dividends
    total_qualified = inc.qualified_dividends + extra_qualified_dividends
    total_st = inc.st_capital_gains + extra_st_gains
    total_lt = inc.lt_capital_gains + extra_lt_gains
    net_cap_gains = total_st + total_lt

    gross_income = (
        inc.wages
        + total_interest
        + total_dividends
        + net_cap_gains
        + inc.home_sale_gain
        + inc.retirement_distributions
        + inc.other_income
    )

    # Itemized deductions
    itemized = (
        ded.mortgage_interest
        + ded.mortgage_points
        + ded.salt_deduction
        + ded.charitable_donations
        + ded.medical_expenses
    )

    try:
        status = FilingStatus(picture.filing_status)
    except ValueError:
        status = FilingStatus.MARRIED_FILING_JOINTLY

    return TaxInput(
        gross_income=round(gross_income, 2),
        filing_status=status,
        tax_year=picture.tax_year,
        itemized_deductions=round(itemized, 2),
        qualified_dividends=round(total_qualified, 2),
        net_capital_gains=round(max(0, total_lt), 2),
        w2_medicare_wages=round(wh.total_medicare_wages, 2),
        total_withholding=round(wh.w2_withholding + wh.form_1099_withholding, 2),
    )


def _run_imports(config: UserConfig) -> ImportSummary:
    """Run financial data imports from the Exports folder.

    Args:
        config: User configuration.

    Returns:
        Merged import summary.
    """
    year = config.tax_year
    exports_path = _ICLOUD_BASE / "Tax" / str(year) / "Exports"

    csv_results = []
    ofx_results = []

    if exports_path.is_dir():
        for item in sorted(exports_path.rglob("*")):
            if not item.is_file() or item.name.startswith("."):
                continue
            ext = item.suffix.lower()
            try:
                if ext == ".csv":
                    csv_results.append(import_csv(item))
                elif ext in (".ofx", ".qfx"):
                    ofx_results.append(import_ofx(item))
            except Exception:
                logger.warning("Failed to import %s", item.name, exc_info=True)

    csv_summary = map_csv_results(csv_results, tax_year=year) if csv_results else ImportSummary(tax_year=year)
    ofx_summary = map_ofx_results(ofx_results, tax_year=year) if ofx_results else ImportSummary(tax_year=year)
    return merge_summaries(csv_summary, ofx_summary)


# ── API Routes ────────────────────────────────────────────────────────


@router.post("/assemble")
def run_assemble() -> dict[str, object]:
    """Run the document assembler: scan → extract → assemble tax picture.

    Returns:
        Complete tax picture as a structured dict.
    """
    config = load_user_config()
    folder_configs = get_folder_configs(config)
    scanned = scan_multiple_folders(folder_configs)
    picture = assemble_tax_picture(scanned, config)

    return {
        "tax_year": picture.tax_year,
        "filing_status": picture.filing_status,
        "income": {
            "wages": picture.income.wages,
            "taxable_interest": picture.income.taxable_interest,
            "ordinary_dividends": picture.income.ordinary_dividends,
            "qualified_dividends": picture.income.qualified_dividends,
            "capital_gain_distributions": picture.income.capital_gain_distributions,
            "st_capital_gains": picture.income.st_capital_gains,
            "lt_capital_gains": picture.income.lt_capital_gains,
            "net_capital_gains": picture.income.net_capital_gains,
            "home_sale_proceeds": picture.income.home_sale_proceeds,
            "home_sale_gain": picture.income.home_sale_gain,
            "marketplace_gross": picture.income.marketplace_gross,
            "retirement_distributions": picture.income.retirement_distributions,
            "total_income": picture.income.total_income,
        },
        "deductions": {
            "mortgage_interest": picture.deductions.mortgage_interest,
            "mortgage_points": picture.deductions.mortgage_points,
            "property_tax_paid": picture.deductions.property_tax_paid,
            "salt_deduction": picture.deductions.salt_deduction,
            "charitable_donations": picture.deductions.charitable_donations,
            "medical_expenses": picture.deductions.medical_expenses,
            "standard_deduction": picture.deductions.standard_deduction,
        },
        "credits": {
            "solar_cost": picture.credits.solar_cost,
            "solar_credit": picture.credits.solar_credit,
            "solar_system_kw": picture.credits.solar_system_kw,
            "child_tax_credit": picture.credits.child_tax_credit,
        },
        "withholding": {
            "w2_withholding": picture.withholding.w2_withholding,
            "form_1099_withholding": picture.withholding.form_1099_withholding,
            "total": picture.withholding.w2_withholding + picture.withholding.form_1099_withholding,
        },
        "real_estate": {
            "sold_property": picture.real_estate.sold_property,
            "sale_price": picture.real_estate.sale_price,
            "sale_address": picture.real_estate.sale_address,
            "selling_expenses": picture.real_estate.selling_expenses,
            "purchased_property": picture.real_estate.purchased_property,
            "purchase_price": picture.real_estate.purchase_price,
            "purchase_address": picture.real_estate.purchase_address,
            "loan_amount": picture.real_estate.loan_amount,
        },
        "documents_extracted": len(picture.documents),
        "documents": [
            {
                "type": d.scan.doc_type.value,
                "filename": d.scan.path.name,
                "fields_extracted": len(d.data),
                "data": {k: v for k, v in d.data.items() if v is not None},
            }
            for d in picture.documents
        ],
        "gaps": [
            {
                "category": g.category,
                "description": g.description,
                "impact": g.impact,
                "action": g.action,
            }
            for g in picture.gaps
        ],
    }


@router.post("/calculate")
def run_calculate() -> dict[str, object]:
    """Run full pipeline: assemble → import → calculate tax.

    Returns:
        Tax calculation result with full bracket breakdown.
    """
    config = load_user_config()

    # Step 1: Assemble from documents
    folder_configs = get_folder_configs(config)
    scanned = scan_multiple_folders(folder_configs)
    picture = assemble_tax_picture(scanned, config)

    # Step 2: Import financial data
    import_summary = _run_imports(config)

    # Step 3: Build tax input and calculate
    tax_input = _build_tax_input_from_picture(picture, import_summary)
    result = _calculator.calculate(tax_input)

    return {
        "tax_input": tax_input.model_dump(),
        "result": result.model_dump(),
        "picture_summary": {
            "documents_extracted": len(picture.documents),
            "gaps_count": len(picture.gaps),
            "imports_processed": import_summary.sources_imported,
        },
    }


@router.post("/full")
def run_full_pipeline() -> dict[str, object]:
    """Run the complete pipeline and return everything for the dashboard.

    Returns:
        Combined result with tax picture, import summary, calculation, and gaps.
    """
    config = load_user_config()

    # Step 1: Assemble tax picture from documents
    folder_configs = get_folder_configs(config)
    scanned = scan_multiple_folders(folder_configs)
    picture = assemble_tax_picture(scanned, config)

    # Step 2: Import financial data from exports
    import_summary = _run_imports(config)

    # Step 3: Calculate
    tax_input = _build_tax_input_from_picture(picture, import_summary)
    result = _calculator.calculate(tax_input)

    return {
        "tax_year": picture.tax_year,
        "filing_status": picture.filing_status,

        # Income breakdown
        "income": {
            "wages": picture.income.wages,
            "interest": picture.income.taxable_interest + import_summary.total_interest,
            "interest_from_docs": picture.income.taxable_interest,
            "interest_from_imports": import_summary.total_interest,
            "ordinary_dividends": picture.income.ordinary_dividends + import_summary.total_ordinary_dividends,
            "qualified_dividends": picture.income.qualified_dividends + import_summary.total_qualified_dividends,
            "st_capital_gains": picture.income.st_capital_gains + import_summary.total_short_term_gains,
            "lt_capital_gains": picture.income.lt_capital_gains + import_summary.total_long_term_gains,
            "home_sale_gain": picture.income.home_sale_gain,
            "retirement_distributions": picture.income.retirement_distributions,
            "total_gross": tax_input.gross_income,
        },

        # Deductions
        "deductions": {
            "mortgage_interest": picture.deductions.mortgage_interest,
            "mortgage_points": picture.deductions.mortgage_points,
            "salt_deduction": picture.deductions.salt_deduction,
            "property_tax": picture.deductions.property_tax_paid,
            "charitable": picture.deductions.charitable_donations,
            "medical": picture.deductions.medical_expenses,
            "standard_deduction": result.standard_deduction,
            "deduction_used": result.deduction_used,
            "method": "itemized" if result.deduction_used > result.standard_deduction else "standard",
        },

        # Credits
        "credits": {
            "solar_credit": picture.credits.solar_credit,
            "solar_cost": picture.credits.solar_cost,
            "child_tax_credit": picture.credits.child_tax_credit,
        },

        # Withholding
        "withholding": {
            "w2": picture.withholding.w2_withholding,
            "form_1099": picture.withholding.form_1099_withholding,
            "total": result.total_withholding,
        },

        # Calculation result
        "calculation": {
            "agi": result.agi,
            "taxable_income": result.taxable_income,
            "income_tax": result.income_tax,
            "additional_medicare_tax": result.additional_medicare_tax,
            "total_tax": result.total_tax,
            "total_withholding": result.total_withholding,
            "refund_or_owed": result.refund_or_owed,
            "effective_rate": result.effective_rate,
            "marginal_rate": result.marginal_rate,
            "brackets": [b.model_dump() for b in result.brackets],
        },

        # Real estate
        "real_estate": {
            "sold": picture.real_estate.sold_property,
            "sale_price": picture.real_estate.sale_price,
            "sale_address": picture.real_estate.sale_address,
            "purchased": picture.real_estate.purchased_property,
            "purchase_price": picture.real_estate.purchase_price,
            "purchase_address": picture.real_estate.purchase_address,
        },

        # Documents & gaps
        "documents": [
            {
                "type": d.scan.doc_type.value,
                "filename": d.scan.path.name,
                "fields": len(d.data),
            }
            for d in picture.documents
        ],
        "gaps": [
            {
                "category": g.category,
                "description": g.description,
                "impact": g.impact,
                "action": g.action,
            }
            for g in picture.gaps
        ],

        # Metadata
        "sources": {
            "documents_scanned": len(scanned),
            "documents_extracted": len(picture.documents),
            "financial_files_imported": import_summary.sources_imported,
            "gap_count": len(picture.gaps),
        },
    }
