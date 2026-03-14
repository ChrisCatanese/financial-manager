# Functional Requirements

> **Requirement type:** Functional (FR) — *What* the system does
>
> **Standard:** See [requirements-standard.md](../standards/requirements-standard.md)
> for field definitions, naming conventions, and lifecycle rules.
>
> **Traceability:** Each FR traces to ≥ 1 Business Requirement (BR).
> See [traceability-matrix.md](traceability-matrix.md) for full chain.

---

## Tax Calculation Core

| ID | Parent BR | Requirement | Acceptance Criteria | Status |
|----|-----------|-------------|---------------------|--------|
| FR-001 | BR-001 | Given gross income and filing status, the system SHALL compute federal income tax using progressive bracket rates. | Tax matches IRS rate schedule for the selected year ±$0.01. | Approved |
| FR-002 | BR-002 | The system SHALL accept filing status as one of: Single, Married Filing Jointly, Married Filing Separately, Head of Household, Qualifying Surviving Spouse. | All 5 statuses selectable; each produces correct bracket thresholds. | Approved |
| FR-003 | BR-003 | The system SHALL support tax year 2024 and 2025 bracket data. | Selecting either year loads the correct IRS-published brackets. | Approved |
| FR-004 | BR-006 | Given income, the system SHALL apply the standard deduction for the selected filing status, or accept an itemized deduction amount. | Taxable income = AGI − max(standard, itemized). | Approved |
| FR-005 | BR-001 | The system SHALL compute Adjusted Gross Income (AGI) from gross income minus above-the-line deductions. | AGI = Gross Income − above-the-line deductions. | Approved |
| FR-006 | BR-005 | The system SHALL return a bracket-by-bracket breakdown showing income taxed at each rate. | Response includes array of {rate, range_low, range_high, tax_in_bracket}. | Approved |

## Tax Credits

| ID | Parent BR | Requirement | Acceptance Criteria | Status |
|----|-----------|-------------|---------------------|--------|
| FR-007 | BR-007 | The system SHALL calculate Child Tax Credit based on number of qualifying children and income phase-out. | Credit matches IRS CTC rules for 2024/2025. | Draft |
| FR-008 | BR-007 | The system SHALL calculate Earned Income Tax Credit (EITC) based on income, filing status, and qualifying children. | Credit matches IRS EITC tables. | Draft |

## Capital Gains & AMT

| ID | Parent BR | Requirement | Acceptance Criteria | Status |
|----|-----------|-------------|---------------------|--------|
| FR-009 | BR-008 | The system SHALL calculate long-term capital gains tax at preferential rates (0%, 15%, 20%). | LTCG tax matches IRS rate schedules. | Draft |
| FR-010 | BR-009 | The system SHALL compute AMT when applicable. | AMT calculation matches IRS Form 6251 logic. | Draft |

## API & Frontend

| ID | Parent BR | Requirement | Acceptance Criteria | Status |
|----|-----------|-------------|---------------------|--------|
| FR-011 | BR-004 | The system SHALL expose a REST API endpoint that accepts tax input and returns calculated results. | POST /api/v1/calculate returns 200 with correct JSON. | Approved |
| FR-012 | BR-004 | The frontend SHALL provide a form for entering income, filing status, deductions, and credits. | All input fields render, validate, and submit correctly. | Approved |
| FR-013 | BR-005 | The frontend SHALL display tax results with a visual bracket breakdown. | Results page shows total tax, effective rate, marginal rate, and per-bracket detail. | Approved |

## Document Intake Pipeline

| ID | Parent BR | Requirement | Acceptance Criteria | Status |
|----|-----------|-------------|---------------------|--------|
| FR-014 | BR-010 | The system SHALL accept a tax profile with filing status, employment, real estate, investment, and deduction situation flags. | Profile model stores ~30 situation flags; API accepts and returns profile. | Approved |
| FR-015 | BR-010 | The system SHALL generate a document checklist based on the tax profile. | Checklist includes all required document types given the profile flags. | Approved |
| FR-016 | BR-010 | The system SHALL scan a local folder and classify tax documents by filename patterns. | Scanner identifies 30+ document types via regex; matches to checklist items. | Approved |
| FR-017 | BR-010 | The system SHALL extract structured data from PDF tax documents (W-2, 1099s, 1098, Closing Disclosure). | Extracted amounts match source PDFs ±$0.01. | Approved |
| FR-018 | BR-010 | The system SHALL provide document type and status models for tracking collection progress. | DocumentItem tracks type, status, source path, extracted data. | Approved |
| FR-019 | BR-011 | The system SHALL compute itemized deductions with SALT cap, medical AGI threshold, and solar credit. | SALT capped at $10K/$5K MFS; medical net of 7.5% AGI; solar at 30%. | Approved |
| FR-020 | BR-010 | The system SHALL scan multiple iCloud folders with folder-specific classification rules and skip patterns. | Intake scanner finds tax-relevant documents across Tax/, House/, and Condo/ folders; skips non-tax files (floor plans, inspections, photos). | Approved |
| FR-021 | BR-010 | The system SHALL extract structured data from settlement statements, solar agreements, consolidated 1099s, 1099-K, and Roth 1099-R documents. | Extracted amounts match source PDFs ±$0.01 for all specialized document types. | Approved |
| FR-022 | BR-010 | The system SHALL assemble a unified tax picture from all extracted documents, routing data to income/deduction/credit/withholding sections and identifying gaps. | Tax picture correctly separates current-year from prior-year data; identifies missing W-2s, 1099s, and purchase records. | Approved |
