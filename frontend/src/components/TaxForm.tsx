import { useState } from 'react';
import type { FilingStatus, TaxInput } from '../types/tax';
import { FILING_STATUS_LABELS } from '../types/tax';

interface TaxFormProps {
  onSubmit: (input: TaxInput) => void;
  loading: boolean;
}

const DEFAULT_INPUT: TaxInput = {
  gross_income: 75000,
  filing_status: 'single',
  tax_year: 2024,
  above_the_line_deductions: 0,
  itemized_deductions: 0,
  num_dependents: 0,
  num_qualifying_children: 0,
};

export function TaxForm({ onSubmit, loading }: TaxFormProps) {
  const [input, setInput] = useState<TaxInput>(DEFAULT_INPUT);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(input);
  };

  const update = <K extends keyof TaxInput>(key: K, value: TaxInput[K]) => {
    setInput((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Income */}
      <div>
        <label htmlFor="gross_income" className="block text-sm font-semibold text-gray-700">
          Gross Income
        </label>
        <div className="mt-1 relative rounded-md shadow-sm">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <span className="text-gray-500 sm:text-sm">$</span>
          </div>
          <input
            id="gross_income"
            type="number"
            min={0}
            step={100}
            value={input.gross_income}
            onChange={(e) => update('gross_income', Number(e.target.value))}
            className="block w-full pl-7 pr-3 py-2.5 border border-gray-300 rounded-lg
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                       text-gray-900 text-sm"
          />
        </div>
      </div>

      {/* Filing Status & Tax Year row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="filing_status" className="block text-sm font-semibold text-gray-700">
            Filing Status
          </label>
          <select
            id="filing_status"
            value={input.filing_status}
            onChange={(e) => update('filing_status', e.target.value as FilingStatus)}
            className="mt-1 block w-full py-2.5 px-3 border border-gray-300 rounded-lg
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                       text-gray-900 text-sm"
          >
            {Object.entries(FILING_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="tax_year" className="block text-sm font-semibold text-gray-700">
            Tax Year
          </label>
          <select
            id="tax_year"
            value={input.tax_year}
            onChange={(e) => update('tax_year', Number(e.target.value))}
            className="mt-1 block w-full py-2.5 px-3 border border-gray-300 rounded-lg
                       focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                       text-gray-900 text-sm"
          >
            <option value={2024}>2024</option>
            <option value={2025}>2025</option>
          </select>
        </div>
      </div>

      {/* Deductions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label htmlFor="above_the_line" className="block text-sm font-semibold text-gray-700">
            Above-the-Line Deductions
          </label>
          <div className="mt-1 relative rounded-md shadow-sm">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span className="text-gray-500 sm:text-sm">$</span>
            </div>
            <input
              id="above_the_line"
              type="number"
              min={0}
              step={100}
              value={input.above_the_line_deductions}
              onChange={(e) => update('above_the_line_deductions', Number(e.target.value))}
              className="block w-full pl-7 pr-3 py-2.5 border border-gray-300 rounded-lg
                         focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                         text-gray-900 text-sm"
            />
          </div>
        </div>

        <div>
          <label htmlFor="itemized" className="block text-sm font-semibold text-gray-700">
            Itemized Deductions
          </label>
          <div className="mt-1 relative rounded-md shadow-sm">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <span className="text-gray-500 sm:text-sm">$</span>
            </div>
            <input
              id="itemized"
              type="number"
              min={0}
              step={100}
              value={input.itemized_deductions}
              onChange={(e) => update('itemized_deductions', Number(e.target.value))}
              className="block w-full pl-7 pr-3 py-2.5 border border-gray-300 rounded-lg
                         focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                         text-gray-900 text-sm"
            />
          </div>
          <p className="mt-1 text-xs text-gray-500">Leave at $0 to use the standard deduction</p>
        </div>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 px-4 bg-blue-600 text-white font-semibold rounded-lg
                   hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 transition-colors
                   disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Calculating…' : 'Calculate Tax'}
      </button>
    </form>
  );
}
