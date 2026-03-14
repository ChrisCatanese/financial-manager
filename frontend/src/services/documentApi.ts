/** API functions for profile, checklist, and document management. */

import type {
  DocumentChecklist,
  ScanResult,
  TaxProfile,
  UploadResult,
} from '../types/documents';

const API_BASE = '/api/v1';

/** Create or update the tax profile. */
export async function createProfile(profile: TaxProfile): Promise<TaxProfile> {
  const response = await fetch(`${API_BASE}/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  });
  if (!response.ok) {
    throw new Error(`Failed to create profile (${response.status})`);
  }
  return response.json();
}

/** Get the current tax profile. */
export async function getProfile(): Promise<TaxProfile | null> {
  const response = await fetch(`${API_BASE}/profile`);
  if (!response.ok) return null;
  const data = await response.json();
  if ('error' in data) return null;
  return data;
}

/** Get the document checklist. */
export async function getChecklist(): Promise<DocumentChecklist | null> {
  const response = await fetch(`${API_BASE}/checklist`);
  if (!response.ok) return null;
  const data = await response.json();
  if ('error' in data) return null;
  return data;
}

/** Scan a local folder for tax documents. */
export async function scanDocuments(folderPath?: string): Promise<ScanResult> {
  const response = await fetch(`${API_BASE}/documents/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(folderPath ? { folder_path: folderPath } : {}),
  });
  if (!response.ok) {
    throw new Error(`Scan failed (${response.status})`);
  }
  return response.json();
}

/** Upload a document file. */
export async function uploadDocument(
  file: File,
  docType: string,
): Promise<UploadResult> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(
    `${API_BASE}/documents/upload?doc_type=${encodeURIComponent(docType)}`,
    {
      method: 'POST',
      body: formData,
    },
  );
  if (!response.ok) {
    throw new Error(`Upload failed (${response.status})`);
  }
  return response.json();
}

/** Get all extracted data from processed documents. */
export async function getExtractedData(): Promise<{
  tax_year: number;
  documents_with_data: number;
  data: Record<string, Record<string, string | number | null>>;
}> {
  const response = await fetch(`${API_BASE}/documents/extracted`);
  if (!response.ok) {
    throw new Error(`Failed to get extracted data (${response.status})`);
  }
  return response.json();
}
