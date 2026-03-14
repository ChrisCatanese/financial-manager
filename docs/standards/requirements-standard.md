# Requirements Standard

> Defines structure, naming conventions, approval workflows, and validation
> criteria for every requirement in this project.

---

## Requirement Types

| Type | Prefix | Definition |
|------|--------|------------|
| Business Requirement (BR) | `BR-NNN` | *Why* — stakeholder need or regulatory obligation |
| Functional Requirement (FR) | `FR-NNN` | *What* — observable system behaviour |
| Technical Requirement (TR) | `TR-NNN` | *How* — implementation design and constraints |

## Required Fields

### BR Fields

| Field | Required | Description |
|-------|----------|-------------|
| ID | ✅ | `BR-NNN` (zero-padded, sequential) |
| Requirement | ✅ | SHALL/SHOULD/MAY statement |
| Rationale | ✅ | Business justification or regulatory citation |
| Priority | ✅ | Must / Should / Could / Won't (MoSCoW) |
| Status | ✅ | Draft → Approved → Implemented → Validated → Retired |

### FR Fields

| Field | Required | Description |
|-------|----------|-------------|
| ID | ✅ | `FR-NNN` |
| Parent BR | ✅ | One or more BR IDs this FR satisfies |
| Requirement | ✅ | Given/When/Then or SHALL statement |
| Acceptance Criteria | ✅ | Observable, testable conditions |
| Status | ✅ | Same lifecycle as BR |

### TR Fields

| Field | Required | Description |
|-------|----------|-------------|
| ID | ✅ | `TR-NNN` |
| Parent FR | ✅ | One or more FR IDs this TR implements |
| Requirement | ✅ | Technical design statement |
| Code Reference | ✅ | Module path, class, function |
| Test Reference | ✅ | Test file and test function(s) |
| Status | ✅ | Draft → Implemented → Validated |

## Traceability Rules

1. Every TR must trace to ≥ 1 FR.
2. Every FR must trace to ≥ 1 BR.
3. Every `src/` module must be referenced by ≥ 1 TR.
4. Every TR with status *Validated* must have a passing test.

## Status Lifecycle

```
Draft → Approved → Implemented → Validated → Retired
                                    ↑
                            (test passes)
```
