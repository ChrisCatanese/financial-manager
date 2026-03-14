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

## Document Intake Pipeline

| ID | Parent FR | Requirement | Code Reference | Test Reference | Status |
|----|-----------|-------------|---------------|----------------|--------|
| TR-010 | FR-014 | Implement TaxProfile Pydantic model with ~30 situation flags for filing, employment, real estate, investments, deductions. | `src/financial_manager/models/tax_profile.py::TaxProfile` | `tests/test_profile_and_documents.py` | Implemented |
| TR-011 | FR-018 | Implement TaxDocumentType enum (30+ types), DocumentStatus enum, DocumentItem and DocumentChecklist Pydantic models. | `src/financial_manager/models/tax_document.py` | `tests/test_profile_and_documents.py` | Implemented |
| TR-012 | FR-015 | Implement checklist generation engine mapping TaxProfile flags to required DocumentItems. | `src/financial_manager/engine/checklist.py::generate_checklist` | `tests/test_checklist.py` | Implemented |
| TR-013 | FR-016 | Implement document scanner with 30+ regex classification rules, folder scanning, and checklist matching. | `src/financial_manager/engine/scanner.py` | `tests/test_scanner.py` | Implemented |
| TR-014 | FR-017 | Implement PDF text extraction with type-specific parsers for W-2, 1099-INT, 1099-DIV, 1099-R, 1098, Closing Disclosure. | `src/financial_manager/engine/extractor.py` | `tests/test_api_documents.py` | Implemented |
| TR-015 | FR-019 | Implement itemized deduction engine with SALT cap ($10K/$5K MFS), medical 7.5% AGI threshold, and 30% solar credit. | `src/financial_manager/engine/itemized.py` | `tests/test_itemized.py` | Implemented |
| TR-016 | FR-014 | Implement secure configuration layer with gitignored local.json and macOS Keychain via keyring. | `src/financial_manager/config.py` | `tests/test_api_documents.py` | Implemented |
