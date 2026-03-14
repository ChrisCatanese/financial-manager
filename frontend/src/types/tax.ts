/** Filing status options matching the backend enum. */
export type FilingStatus =
  | 'single'
  | 'married_filing_jointly'
  | 'married_filing_separately'
  | 'head_of_household'
  | 'qualifying_surviving_spouse';

/** Input payload for the /api/v1/calculate endpoint. */
export interface TaxInput {
  gross_income: number;
  filing_status: FilingStatus;
  tax_year: number;
  above_the_line_deductions: number;
  itemized_deductions: number;
  num_dependents: number;
  num_qualifying_children: number;
}

/** A single bracket in the tax breakdown. */
export interface BracketResult {
  rate: number;
  range_low: number;
  range_high: number;
  taxable_in_bracket: number;
  tax_in_bracket: number;
}

/** Full result from the /api/v1/calculate endpoint. */
export interface TaxResult {
  tax_year: number;
  filing_status: FilingStatus;
  gross_income: number;
  agi: number;
  standard_deduction: number;
  deduction_used: number;
  taxable_income: number;
  total_tax: number;
  effective_rate: number;
  marginal_rate: number;
  brackets: BracketResult[];
}

/** Human-readable labels for filing statuses. */
export const FILING_STATUS_LABELS: Record<FilingStatus, string> = {
  single: 'Single',
  married_filing_jointly: 'Married Filing Jointly',
  married_filing_separately: 'Married Filing Separately',
  head_of_household: 'Head of Household',
  qualifying_surviving_spouse: 'Qualifying Surviving Spouse',
};
