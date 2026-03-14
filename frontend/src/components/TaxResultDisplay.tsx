import type { TaxResult } from '../types/tax';
import { FILING_STATUS_LABELS } from '../types/tax';

interface TaxResultDisplayProps {
  result: TaxResult;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

const BRACKET_COLORS = [
  'bg-emerald-100 text-emerald-800',
  'bg-teal-100 text-teal-800',
  'bg-cyan-100 text-cyan-800',
  'bg-blue-100 text-blue-800',
  'bg-indigo-100 text-indigo-800',
  'bg-violet-100 text-violet-800',
  'bg-purple-100 text-purple-800',
];

export function TaxResultDisplay({ result }: TaxResultDisplayProps) {
  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <SummaryCard label="Total Tax" value={formatCurrency(result.total_tax)} accent />
        <SummaryCard label="Effective Rate" value={formatPercent(result.effective_rate)} />
        <SummaryCard label="Marginal Rate" value={formatPercent(result.marginal_rate)} />
        <SummaryCard label="Taxable Income" value={formatCurrency(result.taxable_income)} />
      </div>

      {/* Calculation Details */}
      <div className="bg-gray-50 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Calculation Details
        </h3>
        <dl className="space-y-2 text-sm">
          <DetailRow label="Filing Status" value={FILING_STATUS_LABELS[result.filing_status]} />
          <DetailRow label="Tax Year" value={String(result.tax_year)} />
          <DetailRow label="Gross Income" value={formatCurrency(result.gross_income)} />
          <DetailRow label="Adjusted Gross Income" value={formatCurrency(result.agi)} />
          <DetailRow label="Standard Deduction" value={formatCurrency(result.standard_deduction)} />
          <DetailRow label="Deduction Used" value={formatCurrency(result.deduction_used)} />
          <DetailRow label="Taxable Income" value={formatCurrency(result.taxable_income)} bold />
        </dl>
      </div>

      {/* Bracket Breakdown */}
      {result.brackets.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Bracket Breakdown
          </h3>
          <div className="space-y-2">
            {result.brackets.map((bracket, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-lg bg-white border border-gray-200"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold
                      ${BRACKET_COLORS[idx % BRACKET_COLORS.length]}`}
                  >
                    {formatPercent(bracket.rate)}
                  </span>
                  <span className="text-sm text-gray-600">
                    {formatCurrency(bracket.range_low)} — {formatCurrency(bracket.range_high)}
                  </span>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold text-gray-900">
                    {formatCurrency(bracket.tax_in_bracket)}
                  </div>
                  <div className="text-xs text-gray-500">
                    on {formatCurrency(bracket.taxable_in_bracket)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Visual Bar */}
      {result.brackets.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Tax Distribution
          </h3>
          <div className="flex rounded-lg overflow-hidden h-6">
            {result.brackets.map((bracket, idx) => {
              const widthPct = result.total_tax > 0
                ? (bracket.tax_in_bracket / result.total_tax) * 100
                : 0;
              return (
                <div
                  key={idx}
                  className={`${BRACKET_COLORS[idx % BRACKET_COLORS.length]} flex items-center justify-center text-xs font-bold`}
                  style={{ width: `${widthPct}%` }}
                  title={`${formatPercent(bracket.rate)}: ${formatCurrency(bracket.tax_in_bracket)}`}
                >
                  {widthPct > 10 ? formatPercent(bracket.rate) : ''}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value, accent = false }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`rounded-xl p-4 ${accent ? 'bg-blue-600 text-white' : 'bg-gray-50 text-gray-900'}`}>
      <p className={`text-xs font-medium ${accent ? 'text-blue-100' : 'text-gray-500'}`}>{label}</p>
      <p className="text-xl font-bold mt-1">{value}</p>
    </div>
  );
}

function DetailRow({ label, value, bold = false }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex justify-between">
      <dt className="text-gray-500">{label}</dt>
      <dd className={`text-gray-900 ${bold ? 'font-bold' : ''}`}>{value}</dd>
    </div>
  );
}
