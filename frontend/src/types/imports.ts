/** Types for the financial data import hub. */

// ── Folder tree ──────────────────────────────────────────────────────

export interface FolderNode {
  name: string;
  path: string;
  category: string;
  children: FolderNode[];
  file_count: number;
}

// ── Import configuration ─────────────────────────────────────────────

export interface ImportAccount {
  institution: string;
  account_type: string;
  owner: 'joint' | 'primary' | 'spouse';
  expected_forms: string[];
  export_path: string;
}

export interface ImportFiler {
  name: string;
  role: 'primary' | 'spouse';
}

export interface ImportProperty {
  label: string;
  address: string;
  role: string;
}

export interface ImportConfig {
  tax_year: number;
  filing_status: string;
  filers: ImportFiler[];
  accounts: ImportAccount[];
  properties: ImportProperty[];
  folder_tree: FolderNode[];
  icloud_base: string;
}

// ── File assessment ──────────────────────────────────────────────────

export interface FileAssessment {
  filename: string;
  file_path: string;
  file_size: number;
  file_type: string;
  detected_format: string;
  detected_institution: string;
  detected_owner: string;
  suggested_destination: string;
  suggested_category: string;
  record_count: number;
  date_range: string;
  preview_data: Record<string, unknown>[];
  warnings: string[];
  can_import: boolean;
}

// ── Scanned file ─────────────────────────────────────────────────────

export interface ScannedFile {
  filename: string;
  path: string;
  folder: string;
  category: string;
  owner: string;
  file_type: string;
  file_size: number;
  modified: string;
}

// ── Upload result ────────────────────────────────────────────────────

export interface UploadResult {
  status: string;
  assessment: FileAssessment;
  final_path: string;
  icloud_relative: string;
}

// ── Scan exports result ──────────────────────────────────────────────

export interface ScanExportsResult {
  accounts_scanned: number;
  files_found: number;
  assessments: FileAssessment[];
}

// ── Process result (tax summary) ─────────────────────────────────────

export interface ProcessResult {
  tax_year: number;
  sources_imported: number;
  total_interest: number;
  total_ordinary_dividends: number;
  total_qualified_dividends: number;
  total_short_term_gains: number;
  total_long_term_gains: number;
  warnings: string[];
}

// ── Display helpers ──────────────────────────────────────────────────

export const OWNER_LABELS: Record<string, string> = {
  joint: 'Joint',
  primary: 'Primary Filer',
  spouse: 'Spouse',
};

export const CATEGORY_LABELS: Record<string, string> = {
  banking: 'Banking',
  brokerage: 'Brokerage',
  insurance: 'Insurance',
  employment: 'Employment',
  retirement: 'Retirement',
  property: 'Property',
  exports: 'Exports',
  general: 'General',
};

export const FILE_TYPE_ICONS: Record<string, string> = {
  csv: '📊',
  ofx: '🏦',
  qfx: '🏦',
  pdf: '📄',
  image: '🖼️',
  other: '📁',
};

export const CATEGORY_ICONS: Record<string, string> = {
  banking: '🏦',
  brokerage: '📈',
  insurance: '🛡️',
  employment: '💼',
  retirement: '🏖️',
  property: '🏠',
  exports: '📥',
  joint: '👥',
  primary: '👤',
  spouse: '👤',
};
