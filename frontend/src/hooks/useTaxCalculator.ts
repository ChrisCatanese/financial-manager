import { useState } from 'react';
import type { TaxInput, TaxResult } from '../types/tax';
import { calculateTax } from '../services/api';

/** Hook for managing tax calculation state. */
export function useTaxCalculator() {
  const [result, setResult] = useState<TaxResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const calculate = async (input: TaxInput) => {
    setLoading(true);
    setError(null);
    try {
      const data = await calculateTax(input);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Calculation failed');
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setResult(null);
    setError(null);
  };

  return { result, loading, error, calculate, reset };
}
