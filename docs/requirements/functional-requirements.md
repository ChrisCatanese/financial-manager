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
