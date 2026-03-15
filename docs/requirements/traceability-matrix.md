# Traceability Matrix

> **Standard:** See [traceability-standard.md](../standards/traceability-standard.md)
> for core-boundary, exploratory-carve-out, and enforcement rules.
>
> **Scope:** This matrix links every Technical Requirement (TR) through its
> parent Functional Requirement (FR) to its governing Business Requirement
> (BR), and maps each to code and tests.
>
> Every `src/` module must appear in this matrix. Commits are blocked
> if a source module is not mapped to a requirement.

## Forward Traceability (TR → FR → BR → Code → Tests)

| TR | FR | BR | Code | Tests | Status |
|----|----|----|------|-------|--------|
| TR-001 | FR-001 | BR-001 | `src/financial_manager/engine/calculator.py` | `tests/test_calculator.py` | Implemented |
| TR-002 | FR-002 | BR-002 | `src/financial_manager/models/filing_status.py` | `tests/test_models.py` | Implemented |
| TR-003 | FR-003 | BR-003 | `src/financial_manager/data/tax_brackets.py` | `tests/test_tax_data.py` | Implemented |
| TR-004 | FR-004 | BR-006 | `src/financial_manager/engine/deductions.py` | `tests/test_deductions.py` | Implemented |
| TR-005 | FR-005 | BR-001 | `src/financial_manager/engine/calculator.py` | `tests/test_calculator.py` | Implemented |
| TR-006 | FR-006 | BR-005 | `src/financial_manager/models/tax_result.py` | `tests/test_calculator.py` | Implemented |
| TR-007 | FR-011 | BR-004 | `src/financial_manager/api/main.py` | `tests/test_api.py` | Implemented |
| TR-008 | FR-011, FR-012 | BR-004 | `src/financial_manager/models/tax_input.py` | `tests/test_models.py` | Implemented |
| TR-009 | FR-011, FR-013 | BR-004, BR-005 | `src/financial_manager/models/tax_result.py` | `tests/test_models.py` | Implemented |
| TR-010 | FR-014 | BR-010 | `src/financial_manager/models/tax_profile.py` | `tests/test_profile_and_documents.py` | Implemented |
| TR-011 | FR-018 | BR-010 | `src/financial_manager/models/tax_document.py` | `tests/test_profile_and_documents.py` | Implemented |
| TR-012 | FR-015 | BR-010 | `src/financial_manager/engine/checklist.py` | `tests/test_checklist.py` | Implemented |
| TR-013 | FR-016 | BR-010 | `src/financial_manager/engine/scanner.py` | `tests/test_scanner.py` | Implemented |
| TR-014 | FR-017 | BR-010 | `src/financial_manager/engine/extractor.py` | `tests/test_api_documents.py` | Implemented |
| TR-015 | FR-019 | BR-011 | `src/financial_manager/engine/itemized.py` | `tests/test_itemized.py` | Implemented |
| TR-016 | FR-014 | BR-010 | `src/financial_manager/config.py` | `tests/test_api_documents.py` | Implemented |
| TR-018 | FR-020 | BR-010 | `src/financial_manager/engine/intake.py` | `tests/test_intake_pipeline.py` | Implemented |
| TR-019 | FR-021 | BR-010 | `src/financial_manager/engine/extractors.py` | `tests/test_intake_pipeline.py` | Implemented |
| TR-020 | FR-022 | BR-010 | `src/financial_manager/engine/assembler.py` | `tests/test_intake_pipeline.py` | Implemented |
| TR-021 | FR-020 | BR-010 | `src/financial_manager/user_config.py` | `tests/test_user_config.py` | Implemented |

## Module Index (all src/ modules)

| Module | TR(s) |
|--------|-------|
| `src/financial_manager/__init__.py` | — (package init) |
| `src/financial_manager/engine/__init__.py` | — (package init) |
| `src/financial_manager/engine/calculator.py` | TR-001, TR-005 |
| `src/financial_manager/engine/deductions.py` | TR-004 |
| `src/financial_manager/models/__init__.py` | — (package init) |
| `src/financial_manager/models/filing_status.py` | TR-002 |
| `src/financial_manager/models/tax_input.py` | TR-008 |
| `src/financial_manager/models/tax_result.py` | TR-006, TR-009 |
| `src/financial_manager/data/__init__.py` | — (package init) |
| `src/financial_manager/data/tax_brackets.py` | TR-003 |
| `src/financial_manager/data/standard_deductions.py` | TR-004 |
| `src/financial_manager/data/capital_gains_rates.py` | TR-017 |
| `src/financial_manager/api/__init__.py` | — (package init) |
| `src/financial_manager/api/main.py` | TR-007 |
| `src/financial_manager/config.py` | TR-016 |
| `src/financial_manager/engine/checklist.py` | TR-012 |
| `src/financial_manager/engine/extractor.py` | TR-014 |
| `src/financial_manager/engine/itemized.py` | TR-015 |
| `src/financial_manager/engine/scanner.py` | TR-013 |
| `src/financial_manager/engine/intake.py` | TR-018 |
| `src/financial_manager/engine/extractors.py` | TR-019 |
| `src/financial_manager/engine/assembler.py` | TR-020 |
| `src/financial_manager/user_config.py` | TR-021 |
| `src/financial_manager/models/tax_document.py` | TR-011 |
| `src/financial_manager/models/tax_profile.py` | TR-010 |

## Reverse Traceability (BR → FR → TR)

| BR | FRs | TRs |
|----|-----|-----|
| BR-001 | FR-001, FR-005 | TR-001, TR-005 |
| BR-002 | FR-002 | TR-002 |
| BR-003 | FR-003 | TR-003 |
| BR-004 | FR-011, FR-012, FR-013 | TR-007, TR-008, TR-009 |
| BR-005 | FR-006, FR-013 | TR-006, TR-009 |
| BR-006 | FR-004 | TR-004 |
| BR-010 | FR-014, FR-015, FR-016, FR-017, FR-018, FR-020, FR-021, FR-022 | TR-010, TR-011, TR-012, TR-013, TR-014, TR-016, TR-018, TR-019, TR-020 |
| BR-011 | FR-019 | TR-015 |

## Coverage Summary

| Metric | Count |
|--------|-------|
| Total TRs | 16 |
| Draft | 0 |
| Implemented | 16 |
| Validated | 0 |
| Coverage | 100% (implemented) |

---

## Maintenance

- **Add module** → add a row to Forward Traceability above.
- **Rename test** → update the Tests column.
- **Delete module** → remove the row.
