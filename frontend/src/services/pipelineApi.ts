/** API client for the pipeline endpoints. */

import type { PipelineResult } from '../types/pipeline';

const API_BASE = '/api/v1/pipeline';

/** Run the full pipeline: assemble → import → calculate. */
export async function runFullPipeline(): Promise<PipelineResult> {
  const response = await fetch(`${API_BASE}/full`, {
    method: 'POST',
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Pipeline failed (${response.status}): ${detail}`);
  }
  return response.json();
}

/** Run only the document assembler. */
export async function runAssemble(): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/assemble`, {
    method: 'POST',
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Assemble failed (${response.status}): ${detail}`);
  }
  return response.json();
}

/** Run assembler + importer + calculator. */
export async function runCalculate(): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/calculate`, {
    method: 'POST',
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Calculate failed (${response.status}): ${detail}`);
  }
  return response.json();
}
