/** Types for the pipeline API — full tax picture + calculation results. */

export interface PipelineIncome {
  wages: number;
  interest: number;
  interest_from_docs: number;
  interest_from_imports: number;
  ordinary_dividends: number;
  qualified_dividends: number;
  st_capital_gains: number;
  lt_capital_gains: number;
  home_sale_gain: number;
  retirement_distributions: number;
  total_gross: number;
}

export interface PipelineDeductions {
  mortgage_interest: number;
  mortgage_points: number;
  salt_deduction: number;
  property_tax: number;
  charitable: number;
  medical: number;
  standard_deduction: number;
  deduction_used: number;
  method: 'standard' | 'itemized';
}

export interface PipelineCredits {
  solar_credit: number;
  solar_cost: number;
  child_tax_credit: number;
}

export interface PipelineWithholding {
  w2: number;
  form_1099: number;
  total: number;
}

export interface PipelineBracket {
  rate: number;
  range_low: number;
  range_high: number;
  taxable_in_bracket: number;
  tax_in_bracket: number;
}

export interface PipelineCalculation {
  agi: number;
  taxable_income: number;
  income_tax: number;
  additional_medicare_tax: number;
  total_tax: number;
  total_withholding: number;
  refund_or_owed: number;
  effective_rate: number;
  marginal_rate: number;
  brackets: PipelineBracket[];
}

export interface PipelineRealEstate {
  sold: boolean;
  sale_price: number;
  sale_address: string;
  purchased: boolean;
  purchase_price: number;
  purchase_address: string;
}

export interface PipelineDocument {
  type: string;
  filename: string;
  fields: number;
}

export interface PipelineGap {
  category: string;
  description: string;
  impact: string;
  action: string;
}

export interface PipelineSources {
  documents_scanned: number;
  documents_extracted: number;
  financial_files_imported: number;
  gap_count: number;
}

/** Full pipeline response from POST /api/v1/pipeline/full */
export interface PipelineResult {
  tax_year: number;
  filing_status: string;
  income: PipelineIncome;
  deductions: PipelineDeductions;
  credits: PipelineCredits;
  withholding: PipelineWithholding;
  calculation: PipelineCalculation;
  real_estate: PipelineRealEstate;
  documents: PipelineDocument[];
  gaps: PipelineGap[];
  sources: PipelineSources;
}
