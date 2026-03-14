/** Types for the tax profile, document checklist, and document management. */

// ── Enums ────────────────────────────────────────────────────────────

export type EmploymentType = 'w2_employee' | 'self_employed' | 'retired' | 'unemployed';

export type InvestmentAccountType =
  | 'brokerage'
  | 'traditional_ira'
  | 'roth_ira'
  | '401k'
  | 'hsa'
  | '529'
  | 'crypto';

export type DocumentStatus = 'missing' | 'found' | 'uploaded' | 'extracted' | 'confirmed';

export type TaxDocumentType =
  | 'w2' | 'w2_spouse'
  | '1099_int' | '1099_div' | '1099_b' | '1099_r' | '1099_k'
  | '1099_nec' | '1099_misc' | '1099_g' | '1099_ssa' | '1099_consolidated'
  | '1098' | '1098_t'
  | 'property_tax_bill' | 'charitable_receipts' | 'medical_expenses'
  | 'solar_agreement' | 'solar_receipt' | 'energy_credit_cert'
  | 'closing_disclosure_purchase' | 'closing_disclosure_sale'
  | 'settlement_statement' | '1099_s'
  | '5498' | '5498_sa' | '1099_sa'
  | 'prior_year_return' | 'identity_document' | 'pay_stub' | 'bank_statement'
  | 'other';

// ── Tax Profile ──────────────────────────────────────────────────────

export interface TaxProfile {
  tax_year: number;
  filing_status: import('./tax').FilingStatus;
  filer_name: string;
  spouse_name: string;
  filer_employment: EmploymentType;
  spouse_employment: EmploymentType | null;
  num_dependents: number;
  num_qualifying_children: number;
  has_mortgage: boolean;
  purchased_home: boolean;
  sold_home: boolean;
  has_property_tax: boolean;
  has_solar: boolean;
  investment_accounts: InvestmentAccountType[];
  has_capital_gains: boolean;
  has_bank_interest: boolean;
  has_dividends: boolean;
  has_retirement_distributions: boolean;
  has_freelance_income: boolean;
  has_marketplace_income: boolean;
  has_unemployment: boolean;
  has_social_security: boolean;
  has_student_loans: boolean;
  has_education_expenses: boolean;
  has_charitable_donations: boolean;
  has_medical_expenses: boolean;
  has_prior_year_return: boolean;
  document_source_path: string | null;
}

// ── Document Checklist ───────────────────────────────────────────────

export interface DocumentItem {
  doc_type: TaxDocumentType;
  label: string;
  description: string;
  required: boolean;
  status: DocumentStatus;
  source_path: string | null;
  extracted_data: Record<string, string | number | null>;
  matched_at: string | null;
}

export interface DocumentChecklist {
  tax_year: number;
  items: DocumentItem[];
  generated_at: string;
}

// ── Scan Result ──────────────────────────────────────────────────────

export interface ScanResult {
  scanned_path: string;
  files_found: number;
  checklist_matched: number;
  checklist_total: number;
  still_missing: string[];
}

// ── Upload Result ────────────────────────────────────────────────────

export interface UploadResult {
  filename: string;
  doc_type: string;
  status: string;
  extracted_fields: number;
  data: Record<string, string | number | null>;
}

// ── Human-readable labels ────────────────────────────────────────────

export const EMPLOYMENT_LABELS: Record<EmploymentType, string> = {
  w2_employee: 'W-2 Employee',
  self_employed: 'Self-Employed',
  retired: 'Retired',
  unemployed: 'Unemployed / Not Working',
};

export const INVESTMENT_LABELS: Record<InvestmentAccountType, string> = {
  brokerage: 'Brokerage Account',
  traditional_ira: 'Traditional IRA',
  roth_ira: 'Roth IRA',
  '401k': '401(k)',
  hsa: 'HSA (Health Savings Account)',
  '529': '529 College Savings',
  crypto: 'Cryptocurrency',
};

export const DOCUMENT_STATUS_LABELS: Record<DocumentStatus, string> = {
  missing: 'Missing',
  found: 'Found',
  uploaded: 'Uploaded',
  extracted: 'Extracted',
  confirmed: 'Confirmed',
};

export const DOCUMENT_STATUS_COLORS: Record<DocumentStatus, string> = {
  missing: 'text-red-500 bg-red-50',
  found: 'text-blue-600 bg-blue-50',
  uploaded: 'text-yellow-600 bg-yellow-50',
  extracted: 'text-green-600 bg-green-50',
  confirmed: 'text-emerald-700 bg-emerald-50',
};
