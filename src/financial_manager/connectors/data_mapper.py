"""Map imported financial data to tax-relevant structures.

Takes the raw parsed output from CSV and OFX importers and produces
tax-oriented summaries that feed directly into the assembler pipeline:

- **Interest income** (→ Form 1099-INT)
- **Dividend income** (→ Form 1099-DIV)
- **Capital gains/losses** (→ Form 1099-B / Schedule D)
- **Investment summary** (cost basis, unrealized gains for reference)
- **Transaction categories** (tax-deductible expenses, estimated payments, etc.)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from financial_manager.connectors.csv_importer import CsvImportResult, CsvTransaction
from financial_manager.connectors.ofx_importer import (
    OfxImportResult,
    OfxInvestmentTransaction,
    OfxTransaction,
)

logger = logging.getLogger(__name__)


# ── Tax-relevant output structures ────────────────────────────────────


@dataclass
class InterestIncome:
    """Interest income summary for a single institution (→ 1099-INT).

    Attributes:
        institution: Bank or brokerage name.
        account_id: Masked account identifier.
        total_interest: Total interest earned during the tax year.
        tax_exempt_interest: Tax-exempt interest (e.g. municipal bonds).
        transactions: Individual interest transactions for audit trail.
    """

    institution: str = ""
    account_id: str = ""
    total_interest: float = 0.0
    tax_exempt_interest: float = 0.0
    transactions: list[dict[str, object]] = field(default_factory=list)


@dataclass
class DividendIncome:
    """Dividend income summary for a single institution (→ 1099-DIV).

    Attributes:
        institution: Brokerage name.
        account_id: Masked account identifier.
        ordinary_dividends: Total ordinary dividends (Box 1a).
        qualified_dividends: Qualified dividends (Box 1b, lower tax rate).
        total_capital_gain_distributions: Capital gain distributions (Box 2a).
        foreign_tax_paid: Foreign tax paid (Box 7).
        transactions: Individual dividend transactions.
    """

    institution: str = ""
    account_id: str = ""
    ordinary_dividends: float = 0.0
    qualified_dividends: float = 0.0
    total_capital_gain_distributions: float = 0.0
    foreign_tax_paid: float = 0.0
    transactions: list[dict[str, object]] = field(default_factory=list)


@dataclass
class CapitalGainLoss:
    """A single capital gain or loss event (→ 1099-B / Schedule D).

    Attributes:
        security: Security name or symbol.
        date_acquired: Acquisition date.
        date_sold: Sale date.
        proceeds: Sale proceeds.
        cost_basis: Cost basis.
        gain_loss: Gain or loss amount (proceeds - cost_basis).
        holding_period: ``short_term`` (<1 year) or ``long_term`` (≥1 year).
        wash_sale: Whether this is a wash sale (for reference only).
    """

    security: str = ""
    date_acquired: str = ""
    date_sold: str = ""
    proceeds: float = 0.0
    cost_basis: float = 0.0
    gain_loss: float = 0.0
    holding_period: str = "short_term"
    wash_sale: bool = False


@dataclass
class CapitalGainsSummary:
    """Aggregate capital gains/losses for a brokerage (→ Schedule D summary).

    Attributes:
        institution: Brokerage name.
        short_term_gain: Net short-term capital gain (or loss if negative).
        long_term_gain: Net long-term capital gain (or loss if negative).
        total_gain: Total net gain/loss.
        transactions: Individual gain/loss events.
    """

    institution: str = ""
    short_term_gain: float = 0.0
    long_term_gain: float = 0.0
    total_gain: float = 0.0
    transactions: list[CapitalGainLoss] = field(default_factory=list)


@dataclass
class TaxableTransaction:
    """A transaction that may be tax-relevant (deduction, credit, estimated payment).

    Attributes:
        date: Transaction date.
        description: Description.
        amount: Dollar amount (positive = expense/payment).
        category: Tax category (e.g. ``charitable``, ``medical``, ``estimated_tax``).
        institution: Source institution.
    """

    date: str = ""
    description: str = ""
    amount: float = 0.0
    category: str = ""
    institution: str = ""


@dataclass
class ImportSummary:
    """Complete tax-relevant summary from all imported financial data.

    Attributes:
        tax_year: Target tax year.
        interest_income: Per-institution interest summaries.
        dividend_income: Per-institution dividend summaries.
        capital_gains: Per-institution capital gains summaries.
        taxable_transactions: Individual tax-relevant transactions.
        total_interest: Grand total interest income.
        total_ordinary_dividends: Grand total ordinary dividends.
        total_qualified_dividends: Grand total qualified dividends.
        total_short_term_gains: Grand total net short-term gains.
        total_long_term_gains: Grand total net long-term gains.
        sources_imported: Number of files processed.
        warnings: Aggregated warnings.
    """

    tax_year: int = 0
    interest_income: list[InterestIncome] = field(default_factory=list)
    dividend_income: list[DividendIncome] = field(default_factory=list)
    capital_gains: list[CapitalGainsSummary] = field(default_factory=list)
    taxable_transactions: list[TaxableTransaction] = field(default_factory=list)
    total_interest: float = 0.0
    total_ordinary_dividends: float = 0.0
    total_qualified_dividends: float = 0.0
    total_short_term_gains: float = 0.0
    total_long_term_gains: float = 0.0
    sources_imported: int = 0
    warnings: list[str] = field(default_factory=list)


# ── Tax category detection ────────────────────────────────────────────

_TAX_CATEGORY_PATTERNS: list[tuple[list[str], str]] = [
    # Interest
    (["interest earned", "interest payment", "interest paid"], "interest"),
    # Charitable
    (["donation", "charitable", "church", "temple", "synagogue", "united way", "red cross"], "charitable"),
    # Medical
    (["doctor", "hospital", "pharmacy", "medical", "dental", "vision", "copay"], "medical"),
    # Estimated tax payments
    (["estimated tax", "irs payment", "tax payment", "eftps"], "estimated_tax"),
    # State/local tax
    (["state tax", "nj tax", "income tax"], "state_tax"),
    # Property tax
    (["property tax", "real estate tax", "township tax", "county tax"], "property_tax"),
    # Mortgage
    (["mortgage", "escrow"], "mortgage"),
    # Education
    (["tuition", "student loan", "education"], "education"),
    # Childcare
    (["daycare", "childcare", "child care", "dependent care"], "childcare"),
]


def _categorize_transaction(description: str, category: str = "") -> str:
    """Categorize a transaction as tax-relevant based on description.

    Args:
        description: Transaction description.
        category: Existing category from institution (if any).

    Returns:
        Tax category string, or empty string if not tax-relevant.
    """
    combined = f"{description} {category}".lower()

    for patterns, tax_cat in _TAX_CATEGORY_PATTERNS:
        for pattern in patterns:
            if pattern in combined:
                return tax_cat

    return ""


# ── CSV mapping ───────────────────────────────────────────────────────


def map_csv_results(
    results: list[CsvImportResult],
    *,
    tax_year: int = 0,
) -> ImportSummary:
    """Map CSV import results to tax-relevant structures.

    Args:
        results: List of CsvImportResult from csv_importer.
        tax_year: Target tax year (for filtering).

    Returns:
        Aggregated ImportSummary.
    """
    summary = ImportSummary(tax_year=tax_year)

    for result in results:
        if result.warnings:
            summary.warnings.extend(result.warnings)

        if result.transactions:
            _map_csv_transactions(result, summary)

        if result.holdings:
            # Holdings are for reference — no direct 1099 mapping
            logger.info(
                "Imported %d holdings from %s (%s)",
                len(result.holdings),
                result.institution,
                result.source_path,
            )

        summary.sources_imported += 1

    _compute_totals(summary)
    return summary


def _map_csv_transactions(result: CsvImportResult, summary: ImportSummary) -> None:
    """Map CSV transactions to interest/dividend/capital gains/taxable buckets.

    Args:
        result: Single CsvImportResult.
        summary: ImportSummary to populate.
    """
    institution = result.institution

    # Group by tax relevance
    interest_txns: list[CsvTransaction] = []
    dividend_txns: list[CsvTransaction] = []
    gain_txns: list[CsvTransaction] = []
    other_tax_txns: list[CsvTransaction] = []

    for txn in result.transactions:
        action = txn.action.lower()

        if action == "interest":
            interest_txns.append(txn)
        elif action in ("dividend", "reinvestment"):
            dividend_txns.append(txn)
        elif action in ("sell", "short_term_gain", "long_term_gain", "capital_gain"):
            gain_txns.append(txn)
        else:
            # Check for other tax-relevant transactions
            cat = _categorize_transaction(txn.description, txn.category)
            if cat:
                txn.category = cat
                other_tax_txns.append(txn)

    # Interest income
    if interest_txns:
        interest = InterestIncome(
            institution=institution,
            total_interest=sum(abs(t.amount) for t in interest_txns),
            transactions=[
                {"date": t.date, "description": t.description, "amount": abs(t.amount)}
                for t in interest_txns
            ],
        )
        summary.interest_income.append(interest)

    # Dividend income
    if dividend_txns:
        dividends = DividendIncome(
            institution=institution,
            ordinary_dividends=sum(abs(t.amount) for t in dividend_txns),
            transactions=[
                {
                    "date": t.date,
                    "symbol": t.symbol,
                    "description": t.description,
                    "amount": abs(t.amount),
                    "action": t.action,
                }
                for t in dividend_txns
            ],
        )
        summary.dividend_income.append(dividends)

    # Capital gains
    if gain_txns:
        gains = CapitalGainsSummary(institution=institution)
        for txn in gain_txns:
            period = "long_term" if txn.action == "long_term_gain" else "short_term"
            cgl = CapitalGainLoss(
                security=txn.symbol or txn.description,
                date_sold=txn.date,
                proceeds=abs(txn.amount) if txn.action == "sell" else 0.0,
                gain_loss=txn.amount,
                holding_period=period,
            )
            gains.transactions.append(cgl)

            if period == "short_term":
                gains.short_term_gain += txn.amount
            else:
                gains.long_term_gain += txn.amount

        gains.total_gain = gains.short_term_gain + gains.long_term_gain
        summary.capital_gains.append(gains)

    # Other tax-relevant transactions
    for txn in other_tax_txns:
        summary.taxable_transactions.append(
            TaxableTransaction(
                date=txn.date,
                description=txn.description,
                amount=abs(txn.amount),
                category=txn.category,
                institution=institution,
            )
        )


# ── OFX mapping ───────────────────────────────────────────────────────


def map_ofx_results(
    results: list[OfxImportResult],
    *,
    tax_year: int = 0,
) -> ImportSummary:
    """Map OFX import results to tax-relevant structures.

    Args:
        results: List of OfxImportResult from ofx_importer.
        tax_year: Target tax year (for filtering).

    Returns:
        Aggregated ImportSummary.
    """
    summary = ImportSummary(tax_year=tax_year)

    for result in results:
        if result.warnings:
            summary.warnings.extend(result.warnings)

        if result.transactions:
            _map_ofx_bank_transactions(result, summary)

        if result.investment_transactions:
            _map_ofx_investment_transactions(result, summary)

        summary.sources_imported += 1

    _compute_totals(summary)
    return summary


def _map_ofx_bank_transactions(result: OfxImportResult, summary: ImportSummary) -> None:
    """Map OFX bank transactions to tax-relevant buckets.

    Args:
        result: Single OfxImportResult.
        summary: ImportSummary to populate.
    """
    institution = result.institution or "Unknown"

    interest_txns: list[OfxTransaction] = []
    other_tax_txns: list[OfxTransaction] = []

    for txn in result.transactions:
        if txn.tran_type == "INT" or "interest" in txn.name.lower():
            interest_txns.append(txn)
        else:
            cat = _categorize_transaction(txn.name, txn.memo)
            if cat:
                other_tax_txns.append(txn)

    if interest_txns:
        interest = InterestIncome(
            institution=institution,
            account_id=result.account_id,
            total_interest=sum(abs(t.amount) for t in interest_txns),
            transactions=[
                {"date": t.date, "name": t.name, "amount": abs(t.amount)}
                for t in interest_txns
            ],
        )
        summary.interest_income.append(interest)

    for txn in other_tax_txns:
        cat = _categorize_transaction(txn.name, txn.memo)
        summary.taxable_transactions.append(
            TaxableTransaction(
                date=txn.date,
                description=txn.name,
                amount=abs(txn.amount),
                category=cat,
                institution=institution,
            )
        )


def _map_ofx_investment_transactions(result: OfxImportResult, summary: ImportSummary) -> None:
    """Map OFX investment transactions to tax-relevant buckets.

    Args:
        result: Single OfxImportResult.
        summary: ImportSummary to populate.
    """
    institution = result.institution or "Unknown"

    dividend_txns: list[OfxInvestmentTransaction] = []
    interest_txns: list[OfxInvestmentTransaction] = []
    gain_txns: list[OfxInvestmentTransaction] = []

    for txn in result.investment_transactions:
        if txn.tran_type == "INCOME":
            income_type = txn.income_type.upper()
            if income_type in ("DIV", "MISC"):
                dividend_txns.append(txn)
            elif income_type == "INTEREST":
                interest_txns.append(txn)
            elif income_type in ("CGLONG", "CGSHORT"):
                gain_txns.append(txn)
            else:
                dividend_txns.append(txn)
        elif txn.tran_type == "REINVEST":
            dividend_txns.append(txn)
        elif txn.buy_sell == "SELL":
            gain_txns.append(txn)

    # Interest from investment accounts
    if interest_txns:
        interest = InterestIncome(
            institution=institution,
            total_interest=sum(abs(t.total) for t in interest_txns),
            transactions=[
                {"date": t.date, "security": t.security_id, "amount": abs(t.total)}
                for t in interest_txns
            ],
        )
        summary.interest_income.append(interest)

    # Dividends
    if dividend_txns:
        dividends = DividendIncome(
            institution=institution,
            ordinary_dividends=sum(abs(t.total) for t in dividend_txns),
            transactions=[
                {
                    "date": t.date,
                    "security": t.security_id,
                    "amount": abs(t.total),
                    "type": t.income_type or t.tran_type,
                }
                for t in dividend_txns
            ],
        )
        summary.dividend_income.append(dividends)

    # Capital gains from sells / gain distributions
    if gain_txns:
        gains = CapitalGainsSummary(institution=institution)
        for txn in gain_txns:
            if txn.income_type == "CGLONG":
                period = "long_term"
            elif txn.income_type == "CGSHORT":
                period = "short_term"
            else:
                # For sells, we don't know the holding period from OFX alone
                period = "short_term"

            cgl = CapitalGainLoss(
                security=txn.security_id,
                date_sold=txn.date,
                proceeds=abs(txn.total) if txn.buy_sell == "SELL" else 0.0,
                gain_loss=txn.total,
                holding_period=period,
            )
            gains.transactions.append(cgl)

            if period == "short_term":
                gains.short_term_gain += txn.total
            else:
                gains.long_term_gain += txn.total

        gains.total_gain = gains.short_term_gain + gains.long_term_gain
        summary.capital_gains.append(gains)


# ── Combine + totals ──────────────────────────────────────────────────


def merge_summaries(*summaries: ImportSummary) -> ImportSummary:
    """Merge multiple ImportSummary objects into one.

    Args:
        summaries: ImportSummary objects to merge.

    Returns:
        Combined ImportSummary with recomputed totals.
    """
    merged = ImportSummary()

    for s in summaries:
        merged.interest_income.extend(s.interest_income)
        merged.dividend_income.extend(s.dividend_income)
        merged.capital_gains.extend(s.capital_gains)
        merged.taxable_transactions.extend(s.taxable_transactions)
        merged.warnings.extend(s.warnings)
        merged.sources_imported += s.sources_imported
        if s.tax_year:
            merged.tax_year = s.tax_year

    _compute_totals(merged)
    return merged


def _compute_totals(summary: ImportSummary) -> None:
    """Recompute aggregate totals from individual components.

    Args:
        summary: ImportSummary to update in place.
    """
    summary.total_interest = sum(i.total_interest for i in summary.interest_income)
    summary.total_ordinary_dividends = sum(d.ordinary_dividends for d in summary.dividend_income)
    summary.total_qualified_dividends = sum(d.qualified_dividends for d in summary.dividend_income)
    summary.total_short_term_gains = sum(g.short_term_gain for g in summary.capital_gains)
    summary.total_long_term_gains = sum(g.long_term_gain for g in summary.capital_gains)
