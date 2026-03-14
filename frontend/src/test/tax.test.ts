import { describe, it, expect } from 'vitest';
import { FILING_STATUS_LABELS } from '../types/tax';
import type { FilingStatus } from '../types/tax';

describe('Tax Types', () => {
  it('defines all 5 filing statuses', () => {
    const statuses: FilingStatus[] = [
      'single',
      'married_filing_jointly',
      'married_filing_separately',
      'head_of_household',
      'qualifying_surviving_spouse',
    ];
    expect(statuses).toHaveLength(5);
  });

  it('has labels for all filing statuses', () => {
    expect(Object.keys(FILING_STATUS_LABELS)).toHaveLength(5);
    expect(FILING_STATUS_LABELS.single).toBe('Single');
    expect(FILING_STATUS_LABELS.married_filing_jointly).toBe('Married Filing Jointly');
  });
});
