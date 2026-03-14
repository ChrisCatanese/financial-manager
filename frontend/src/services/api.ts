import type { TaxInput, TaxResult } from '../types/tax';

const API_BASE = '/api/v1';

/** Calculate federal income tax via the backend API. */
export async function calculateTax(input: TaxInput): Promise<TaxResult> {
  const response = await fetch(`${API_BASE}/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Tax calculation failed (${response.status}): ${detail}`);
  }

  return response.json();
}

/** Health check for the backend API. */
export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return response.json();
}
