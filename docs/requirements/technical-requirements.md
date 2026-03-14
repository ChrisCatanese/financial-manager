# Technical Requirements

> **Requirement type:** Technical (TR) — *How* the system is built
>
> **Standard:** See [requirements-standard.md](../standards/requirements-standard.md)
> for field definitions, naming conventions, and lifecycle rules.
>
> **Traceability:** Each TR traces to ≥ 1 Functional Requirement (FR).
> See [traceability-matrix.md](traceability-matrix.md) for full chain.

---

## Tax Engine

| ID | Parent FR | Requirement | Code Reference | Test Reference | Status |
|----|-----------|-------------|---------------|----------------|--------|
| TR-001 | FR-001 | Implement progressive tax calculation using ordered bracket list and cumulative sum. | `src/financial_manager/engine/calculator.py::TaxCalculator` | `tests/test_calculator.py::TestProgressiveTax` | Implemented |
| TR-002 | FR-002 | Define FilingStatus enum with all 5 IRS filing statuses. | `src/financial_manager/models/filing_status.py::FilingStatus` | `tests/test_models.py::TestFilingStatus` | Implemented |
| TR-003 | FR-003 | Store tax bracket data as Python dictionaries keyed by (year, filing_status). | `src/financial_manager/data/tax_brackets.py` | `tests/test_tax_data.py::TestBracketData` | Implemented |
| TR-004 | FR-004 | Implement standard deduction lookup by filing status and year; support itemized override. | `src/financial_manager/engine/deductions.py::apply_deductions` | `tests/test_deductions.py::TestDeductions` | Implemented |
| TR-005 | FR-005 | Compute AGI as gross_income minus above-the-line adjustments. | `src/financial_manager/engine/calculator.py::TaxCalculator.compute_agi` | `tests/test_calculator.py::TestAGI` | Implemented |
| TR-006 | FR-006 | Return bracket breakdown as list of BracketResult Pydantic models. | `src/financial_manager/models/tax_result.py::BracketResult` | `tests/test_calculator.py::TestBracketBreakdown` | Implemented |

## API Layer

| ID | Parent FR | Requirement | Code Reference | Test Reference | Status |
|----|-----------|-------------|---------------|----------------|--------|
| TR-007 | FR-011 | Implement POST /api/v1/calculate endpoint using FastAPI with Pydantic request/response models. | `src/financial_manager/api/main.py::calculate_tax` | `tests/test_api.py::TestCalculateEndpoint` | Implemented |

## Data Models

| ID | Parent FR | Requirement | Code Reference | Test Reference | Status |
|----|-----------|-------------|---------------|----------------|--------|
| TR-008 | FR-011, FR-012 | Define TaxInput Pydantic model with income, filing_status, tax_year, deductions. | `src/financial_manager/models/tax_input.py::TaxInput` | `tests/test_models.py::TestTaxInput` | Implemented |
| TR-009 | FR-011, FR-013 | Define TaxResult Pydantic model with total_tax, effective_rate, marginal_rate, brackets. | `src/financial_manager/models/tax_result.py::TaxResult` | `tests/test_models.py::TestTaxResult` | Implemented |
