/** API client for the financial data import hub. */

import type {
  FileAssessment,
  ImportConfig,
  ProcessResult,
  ScannedFile,
  ScanExportsResult,
  UploadResult,
} from '../types/imports';

const API_BASE = '/api/v1/import';

/** Get import configuration: accounts, folder tree, filers. */
export async function getImportConfig(): Promise<ImportConfig> {
  const res = await fetch(`${API_BASE}/config`);
  if (!res.ok) throw new Error(`Failed to load import config (${res.status})`);
  return res.json();
}

/** List all files already in the iCloud tax folder structure. */
export async function listExistingFiles(): Promise<{
  base_path: string;
  exists: boolean;
  files: ScannedFile[];
  total: number;
}> {
  const res = await fetch(`${API_BASE}/files`);
  if (!res.ok) throw new Error(`Failed to list files (${res.status})`);
  return res.json();
}

/** Assess a file without saving — get format detection and preview. */
export async function assessFile(file: File): Promise<{ assessment: FileAssessment }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API_BASE}/assess`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`Assessment failed (${res.status})`);
  return res.json();
}

/** Upload a file to the iCloud folder structure. */
export async function uploadToICloud(
  file: File,
  opts?: { destination?: string; owner?: string; category?: string },
): Promise<UploadResult> {
  const form = new FormData();
  form.append('file', file);
  const params = new URLSearchParams();
  if (opts?.destination) params.set('destination', opts.destination);
  if (opts?.owner) params.set('owner', opts.owner);
  if (opts?.category) params.set('category', opts.category);
  const qs = params.toString() ? `?${params}` : '';
  const res = await fetch(`${API_BASE}/upload${qs}`, { method: 'POST', body: form });
  if (!res.ok) throw new Error(`Upload failed (${res.status})`);
  return res.json();
}

/** Scan configured export folders (~/Downloads/Fidelity, etc.) for new files. */
export async function scanExportFolders(): Promise<ScanExportsResult> {
  const res = await fetch(`${API_BASE}/scan-exports`, { method: 'POST' });
  if (!res.ok) throw new Error(`Export scan failed (${res.status})`);
  return res.json();
}

/** Process all imports in the Exports folder and generate tax summary. */
export async function processImports(taxYear?: number): Promise<ProcessResult> {
  const params = taxYear ? `?tax_year=${taxYear}` : '';
  const res = await fetch(`${API_BASE}/process${params}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Processing failed (${res.status})`);
  return res.json();
}

/** Move a file from an export folder into the organized iCloud structure. */
export async function moveToICloud(
  sourcePath: string,
  opts?: { destination?: string; owner?: string; category?: string },
): Promise<{ status: string; final_path: string; assessment: FileAssessment }> {
  const params = new URLSearchParams({ source_path: sourcePath });
  if (opts?.destination) params.set('destination', opts.destination);
  if (opts?.owner) params.set('owner', opts.owner);
  if (opts?.category) params.set('category', opts.category);
  const res = await fetch(`${API_BASE}/move-to-icloud?${params}`, { method: 'POST' });
  if (!res.ok) throw new Error(`Move failed (${res.status})`);
  return res.json();
}
