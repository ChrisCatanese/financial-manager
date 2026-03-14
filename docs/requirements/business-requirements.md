# Business Requirements

> **Requirement type:** Business (BR) — *Why* the capability exists
>
> **Standard:** See [requirements-standard.md](../standards/requirements-standard.md)
> for field definitions, naming conventions, and lifecycle rules.

---

## Requirements

| ID | Requirement | Rationale | Priority | Status |
|----|-------------|-----------|----------|--------|
| BR-001 | The system SHALL calculate US federal income tax for individuals. | Users need an accurate, accessible tool to estimate their federal tax liability without expensive software. | Must | Approved |
| BR-002 | The system SHALL support all IRS filing statuses. | Tax liability varies by filing status; all statuses must be supported to serve all filers. | Must | Approved |
| BR-003 | The system SHALL support multiple tax years (2024, 2025). | Tax brackets and rules change annually; users need to calculate for current and prior years. | Must | Approved |
| BR-004 | The system SHALL provide a modern, responsive web interface. | Users expect a clean, intuitive UI accessible from desktop and mobile devices. | Must | Approved |
| BR-005 | The system SHALL display a detailed breakdown of the tax calculation. | Transparency in calculation builds trust and helps users understand their tax situation. | Should | Approved |
| BR-006 | The system SHALL support standard and itemized deductions. | Deduction type significantly impacts tax liability; users need both options. | Must | Approved |
| BR-007 | The system SHALL support common tax credits (Child Tax Credit, EITC). | Credits reduce tax liability and are critical for accurate calculations. | Should | Approved |
| BR-008 | The system SHALL support capital gains tax calculations. | Many taxpayers have investment income requiring different tax rate treatment. | Should | Draft |
| BR-009 | The system SHALL calculate Alternative Minimum Tax (AMT). | Higher-income taxpayers may be subject to AMT; this is needed for complete calculations. | Could | Draft |
