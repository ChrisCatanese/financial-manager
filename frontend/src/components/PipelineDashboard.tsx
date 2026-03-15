/** Pipeline Dashboard — comprehensive tax picture + calculation results.
 *
 * Runs the full backend pipeline (scan → extract → import → calculate)
 * and displays every section: income, deductions, credits, withholding,
 * real estate, bracket breakdown, refund/owed, and gap analysis.
 */

import { useState } from 'react';
import { runFullPipeline } from '../services/pipelineApi';
import type {
  PipelineResult,
  PipelineBracket,
  PipelineGap,
} from '../types/pipeline';

/* ── Formatting helpers ──────────────────────────────────────────── */

function $(n: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

function pct(n: number): string {
  return `${(n * 100).toFixed(2)}%`;
}

const BRACKET_COLORS = [
  'bg-emerald-200 text-emerald-900',
  'bg-teal-200 text-teal-900',
  'bg-cyan-200 text-cyan-900',
  'bg-blue-200 text-blue-900',
  'bg-indigo-200 text-indigo-900',
  'bg-violet-200 text-violet-900',
  'bg-purple-200 text-purple-900',
];

const IMPACT_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-800 border-red-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
};

/* ── Sub-components ──────────────────────────────────────────────── */

function MetricCard({ label, value, sub, accent }: {
  label: string; value: string; sub?: string; accent?: boolean;
}) {
  return (
    <div className={`rounded-xl p-4 ${accent ? 'bg-blue-600 text-white' : 'bg-gray-50'}`}>
      <p className={`text-xs font-medium ${accent ? 'text-blue-100' : 'text-gray-500'}`}>{label}</p>
      <p className={`text-xl font-bold mt-1 ${accent ? '' : 'text-gray-900'}`}>{value}</p>
      {sub && <p className={`text-xs mt-0.5 ${accent ? 'text-blue-200' : 'text-gray-400'}`}>{sub}</p>}
    </div>
  );
}

function Row({ label, value, bold, indent }: {
  label: string; value: string; bold?: boolean; indent?: boolean;
}) {
  return (
    <div className={`flex justify-between py-1 ${indent ? 'pl-4' : ''}`}>
      <span className={`text-sm ${bold ? 'font-semibold text-gray-900' : 'text-gray-500'}`}>{label}</span>
      <span className={`text-sm ${bold ? 'font-bold text-gray-900' : 'text-gray-700'}`}>{value}</span>
    </div>
  );
}

function SectionHeader({ icon, title }: { icon: string; title: string }) {
  return (
    <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
      <span>{icon}</span>{title}
    </h3>
  );
}

function BracketBar({ brackets, totalTax }: { brackets: PipelineBracket[]; totalTax: number }) {
  if (!brackets.length || totalTax <= 0) return null;
  return (
    <div className="flex rounded-lg overflow-hidden h-7 mt-3">
      {brackets.map((b, i) => {
        const w = (b.tax_in_bracket / totalTax) * 100;
        return (
          <div
            key={i}
            className={`${BRACKET_COLORS[i % BRACKET_COLORS.length]} flex items-center justify-center text-xs font-bold`}
            style={{ width: `${w}%` }}
            title={`${pct(b.rate)}: ${$(b.tax_in_bracket)}`}
          >
            {w > 8 ? pct(b.rate) : ''}
          </div>
        );
      })}
    </div>
  );
}

function GapCard({ gap }: { gap: PipelineGap }) {
  const colors = IMPACT_COLORS[gap.impact.toLowerCase()] ?? IMPACT_COLORS.low;
  return (
    <div className={`rounded-lg border p-3 ${colors}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-bold uppercase">{gap.category}</span>
        <span className="text-xs font-semibold">{gap.impact}</span>
      </div>
      <p className="text-sm font-medium">{gap.description}</p>
      <p className="text-xs mt-1 opacity-80">🔧 {gap.action}</p>
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────────────── */

export function PipelineDashboard() {
  const [data, setData] = useState<PipelineResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await runFullPipeline();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pipeline failed');
    } finally {
      setLoading(false);
    }
  };

  /* ── Empty state ── */
  if (!data && !loading) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-12 text-center">
          <div className="text-6xl mb-4">⚡</div>
          <h2 className="text-2xl font-bold text-gray-900">Pipeline Dashboard</h2>
          <p className="text-gray-500 mt-2 max-w-md mx-auto">
            Run the full tax pipeline to scan documents, import financial data,
            calculate your taxes, and see everything in one place.
          </p>
          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 text-sm">
              {error}
            </div>
          )}
          <button
            onClick={run}
            disabled={loading}
            className="mt-6 inline-flex items-center gap-2 px-8 py-3 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            <span className="text-lg">▶</span> Run Full Pipeline
          </button>
        </div>
      </div>
    );
  }

  /* ── Loading state ── */
  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-12 text-center">
        <div className="text-5xl mb-4 animate-pulse">⏳</div>
        <h3 className="text-lg font-semibold text-gray-700">Running Pipeline…</h3>
        <p className="text-sm text-gray-500 mt-2">Scanning documents, importing financial data, calculating taxes.</p>
      </div>
    );
  }

  if (!data) return null;

  const d = data;
  const calc = d.calculation;
  const isRefund = calc.refund_or_owed < 0;

  return (
    <div className="space-y-6">
      {/* ── Header + Re-run ── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            {d.tax_year} Tax Dashboard
          </h2>
          <p className="text-sm text-gray-500">
            {d.filing_status.replace(/_/g, ' ')} · {d.sources.documents_extracted} docs · {d.sources.financial_files_imported} imports
          </p>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="flex items-center gap-2 px-5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          🔄 Re-run Pipeline
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">{error}</div>
      )}

      {/* ── Top-line Metrics ── */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <MetricCard
          label={isRefund ? '💰 Refund' : '💸 Amount Owed'}
          value={$(Math.abs(calc.refund_or_owed))}
          accent
        />
        <MetricCard label="Total Tax" value={$(calc.total_tax)} />
        <MetricCard label="Effective Rate" value={pct(calc.effective_rate)} />
        <MetricCard label="Marginal Rate" value={pct(calc.marginal_rate)} />
        <MetricCard label="AGI" value={$(calc.agi)} />
      </div>

      {/* ── Two-column layout ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* ── Income ── */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
          <SectionHeader icon="💵" title="Income Breakdown" />
          <Row label="Wages (W-2)" value={$(d.income.wages)} />
          <Row label="Interest Income" value={$(d.income.interest)} />
          {d.income.interest_from_imports > 0 && (
            <Row label="↳ From bank imports" value={$(d.income.interest_from_imports)} indent />
          )}
          <Row label="Ordinary Dividends" value={$(d.income.ordinary_dividends)} />
          <Row label="Qualified Dividends" value={$(d.income.qualified_dividends)} indent />
          {(d.income.st_capital_gains !== 0 || d.income.lt_capital_gains !== 0) && (
            <>
              <Row label="Short-Term Gains" value={$(d.income.st_capital_gains)} />
              <Row label="Long-Term Gains" value={$(d.income.lt_capital_gains)} />
            </>
          )}
          {d.income.home_sale_gain > 0 && (
            <Row label="Home Sale Gain" value={$(d.income.home_sale_gain)} />
          )}
          {d.income.retirement_distributions > 0 && (
            <Row label="Retirement Distributions" value={$(d.income.retirement_distributions)} />
          )}
          <div className="border-t border-gray-200 mt-2 pt-2">
            <Row label="Total Gross Income" value={$(d.income.total_gross)} bold />
          </div>
        </div>

        {/* ── Deductions ── */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
          <SectionHeader icon="📝" title="Deductions" />
          <div className="mb-2">
            <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold ${
              d.deductions.method === 'itemized'
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-600'
            }`}>
              {d.deductions.method === 'itemized' ? '✅ Itemizing' : 'Standard Deduction'}
            </span>
          </div>
          {d.deductions.mortgage_interest > 0 && (
            <Row label="Mortgage Interest" value={$(d.deductions.mortgage_interest)} />
          )}
          {d.deductions.mortgage_points > 0 && (
            <Row label="Mortgage Points" value={$(d.deductions.mortgage_points)} />
          )}
          {d.deductions.salt_deduction > 0 && (
            <Row label="SALT Deduction" value={$(d.deductions.salt_deduction)} />
          )}
          {d.deductions.property_tax > 0 && (
            <Row label="Property Tax (actual)" value={$(d.deductions.property_tax)} indent />
          )}
          {d.deductions.charitable > 0 && (
            <Row label="Charitable" value={$(d.deductions.charitable)} />
          )}
          {d.deductions.medical > 0 && (
            <Row label="Medical" value={$(d.deductions.medical)} />
          )}
          <div className="border-t border-gray-200 mt-2 pt-2">
            <Row label="Standard Deduction" value={$(d.deductions.standard_deduction)} />
            <Row label="Deduction Used" value={$(d.deductions.deduction_used)} bold />
          </div>
        </div>

        {/* ── Credits ── */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
          <SectionHeader icon="🏷️" title="Credits" />
          {d.credits.solar_credit > 0 ? (
            <>
              <Row label="Solar Investment Credit" value={$(d.credits.solar_credit)} />
              <Row label="System Cost" value={$(d.credits.solar_cost)} indent />
            </>
          ) : (
            <p className="text-sm text-gray-400">No solar credit detected.</p>
          )}
          {d.credits.child_tax_credit > 0 && (
            <Row label="Child Tax Credit" value={$(d.credits.child_tax_credit)} />
          )}
          {d.credits.solar_credit === 0 && d.credits.child_tax_credit === 0 && (
            <p className="text-sm text-gray-400 mt-1">No credits detected from scanned documents.</p>
          )}
        </div>

        {/* ── Withholding ── */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
          <SectionHeader icon="🏦" title="Withholding & Payments" />
          <Row label="W-2 Federal Withholding" value={$(d.withholding.w2)} />
          {d.withholding.form_1099 > 0 && (
            <Row label="1099 Withholding" value={$(d.withholding.form_1099)} />
          )}
          <div className="border-t border-gray-200 mt-2 pt-2">
            <Row label="Total Withheld" value={$(d.withholding.total)} bold />
          </div>
        </div>
      </div>

      {/* ── Real Estate ── */}
      {(d.real_estate.sold || d.real_estate.purchased) && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
          <SectionHeader icon="🏠" title="Real Estate Transactions" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {d.real_estate.sold && (
              <div className="bg-red-50 rounded-lg p-3">
                <p className="text-xs font-bold text-red-600 uppercase">Sold</p>
                <p className="text-sm font-semibold mt-1">{d.real_estate.sale_address || 'Property sold'}</p>
                <p className="text-sm text-gray-600">{$(d.real_estate.sale_price)}</p>
              </div>
            )}
            {d.real_estate.purchased && (
              <div className="bg-green-50 rounded-lg p-3">
                <p className="text-xs font-bold text-green-600 uppercase">Purchased</p>
                <p className="text-sm font-semibold mt-1">{d.real_estate.purchase_address || 'Property purchased'}</p>
                <p className="text-sm text-gray-600">{$(d.real_estate.purchase_price)}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Tax Calculation Detail ── */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
        <SectionHeader icon="🧮" title="Tax Calculation" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8">
          <div>
            <Row label="Adjusted Gross Income" value={$(calc.agi)} />
            <Row label="Taxable Income" value={$(calc.taxable_income)} bold />
            <Row label="Income Tax (Line 16)" value={$(calc.income_tax)} />
            {calc.additional_medicare_tax > 0 && (
              <Row label="Additional Medicare Tax" value={$(calc.additional_medicare_tax)} />
            )}
            <Row label="Total Tax" value={$(calc.total_tax)} bold />
          </div>
          <div>
            <Row label="Total Withholding" value={$(calc.total_withholding)} />
            <div className="border-t border-gray-200 mt-2 pt-2">
              <Row
                label={isRefund ? '💰 Refund' : '💸 Amount Owed'}
                value={$(Math.abs(calc.refund_or_owed))}
                bold
              />
            </div>
          </div>
        </div>

        {/* Bracket breakdown */}
        {calc.brackets.length > 0 && (
          <div className="mt-5">
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Bracket Breakdown</h4>
            <div className="space-y-1.5">
              {calc.brackets.map((b: PipelineBracket, i: number) => (
                <div key={i} className="flex items-center justify-between p-2.5 rounded-lg bg-gray-50 border border-gray-100">
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${
                      BRACKET_COLORS[i % BRACKET_COLORS.length]
                    }`}>
                      {pct(b.rate)}
                    </span>
                    <span className="text-xs text-gray-500">
                      {$(b.range_low)} — {$(b.range_high)}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-semibold text-gray-900">{$(b.tax_in_bracket)}</span>
                    <span className="text-xs text-gray-400 ml-2">on {$(b.taxable_in_bracket)}</span>
                  </div>
                </div>
              ))}
            </div>
            <BracketBar brackets={calc.brackets} totalTax={calc.total_tax} />
          </div>
        )}
      </div>

      {/* ── Documents Processed ── */}
      {d.documents.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
          <SectionHeader icon="📄" title={`Documents (${d.documents.length})`} />
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {d.documents.map((doc, i) => (
              <div key={i} className="bg-gray-50 rounded-lg p-3 text-center">
                <p className="text-xs font-bold text-gray-500 uppercase">{doc.type.replace(/_/g, ' ')}</p>
                <p className="text-xs text-gray-400 truncate mt-1" title={doc.filename}>{doc.filename}</p>
                <p className="text-xs text-gray-400">{doc.fields} fields</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Gap Analysis ── */}
      {d.gaps.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
          <SectionHeader icon="⚠️" title={`Action Items (${d.gaps.length})`} />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {d.gaps.map((gap: PipelineGap, i: number) => (
              <GapCard key={i} gap={gap} />
            ))}
          </div>
        </div>
      )}

      {/* ── Source Summary Footer ── */}
      <div className="bg-gray-50 rounded-xl p-4 text-center text-xs text-gray-400 space-x-4">
        <span>📄 {d.sources.documents_scanned} scanned</span>
        <span>✅ {d.sources.documents_extracted} extracted</span>
        <span>📥 {d.sources.financial_files_imported} imported</span>
        <span>⚠️ {d.sources.gap_count} gaps</span>
      </div>
    </div>
  );
}
