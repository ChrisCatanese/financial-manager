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
| `src/financial_manager/api/__init__.py` | — (package init) |
| `src/financial_manager/api/main.py` | TR-007 |

## Reverse Traceability (BR → FR → TR)

| BR | FRs | TRs |
|----|-----|-----|
| BR-001 | FR-001, FR-005 | TR-001, TR-005 |
| BR-002 | FR-002 | TR-002 |
| BR-003 | FR-003 | TR-003 |
| BR-004 | FR-011, FR-012, FR-013 | TR-007, TR-008, TR-009 |
| BR-005 | FR-006, FR-013 | TR-006, TR-009 |
| BR-006 | FR-004 | TR-004 |

## Coverage Summary

| Metric | Count |
|--------|-------|
| Total TRs | 9 |
| Draft | 0 |
| Implemented | 9 |
| Validated | 0 |
| Coverage | 100% (implemented) |

---

## Maintenance

- **Add module** → add a row to Forward Traceability above.
- **Rename test** → update the Tests column.
- **Delete module** → remove the row.
