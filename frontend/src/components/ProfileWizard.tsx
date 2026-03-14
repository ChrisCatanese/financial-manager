import { useState } from 'react';
import type { FilingStatus } from '../types/tax';
import { FILING_STATUS_LABELS } from '../types/tax';
import type {
  EmploymentType,
  InvestmentAccountType,
  TaxProfile,
} from '../types/documents';
import { EMPLOYMENT_LABELS, INVESTMENT_LABELS } from '../types/documents';

interface ProfileWizardProps {
  onComplete: (profile: TaxProfile) => void;
}

const STEPS = [
  'Filing Info',
  'Employment',
  'Real Estate',
  'Investments',
  'Deductions',
  'Review',
] as const;

const DEFAULT_PROFILE: TaxProfile = {
  tax_year: 2025,
  filing_status: 'married_filing_jointly',
  filer_name: '',
  spouse_name: '',
  filer_employment: 'w2_employee',
  spouse_employment: 'w2_employee',
  num_dependents: 0,
  num_qualifying_children: 0,
  has_mortgage: false,
  purchased_home: false,
  sold_home: false,
  has_property_tax: false,
  has_solar: false,
  investment_accounts: [],
  has_capital_gains: false,
  has_bank_interest: false,
  has_dividends: false,
  has_retirement_distributions: false,
  has_freelance_income: false,
  has_marketplace_income: false,
  has_unemployment: false,
  has_social_security: false,
  has_student_loans: false,
  has_education_expenses: false,
  has_charitable_donations: false,
  has_medical_expenses: false,
  has_prior_year_return: false,
  document_source_path: null,
};

export function ProfileWizard({ onComplete }: ProfileWizardProps) {
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<TaxProfile>(DEFAULT_PROFILE);

  const update = <K extends keyof TaxProfile>(key: K, value: TaxProfile[K]) => {
    setProfile((prev) => ({ ...prev, [key]: value }));
  };

  const toggleInvestment = (acct: InvestmentAccountType) => {
    setProfile((prev) => ({
      ...prev,
      investment_accounts: prev.investment_accounts.includes(acct)
        ? prev.investment_accounts.filter((a) => a !== acct)
        : [...prev.investment_accounts, acct],
    }));
  };

  const isJoint =
    profile.filing_status === 'married_filing_jointly' ||
    profile.filing_status === 'married_filing_separately';

  const next = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));
  const prev = () => setStep((s) => Math.max(s - 1, 0));

  const renderStep = () => {
    switch (step) {
      case 0:
        return (
          <div className="space-y-5">
            <h3 className="text-lg font-bold text-gray-800">Filing Information</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Tax Year</label>
                <select
                  value={profile.tax_year}
                  onChange={(e) => update('tax_year', Number(e.target.value))}
                  className="w-full py-2.5 px-3 border border-gray-300 rounded-lg text-sm"
                >
                  <option value={2025}>2025</option>
                  <option value={2024}>2024</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Filing Status</label>
                <select
                  value={profile.filing_status}
                  onChange={(e) => update('filing_status', e.target.value as FilingStatus)}
                  className="w-full py-2.5 px-3 border border-gray-300 rounded-lg text-sm"
                >
                  {Object.entries(FILING_STATUS_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Your Name</label>
                <input
                  type="text"
                  value={profile.filer_name}
                  onChange={(e) => update('filer_name', e.target.value)}
                  placeholder="Primary filer"
                  className="w-full py-2.5 px-3 border border-gray-300 rounded-lg text-sm"
                />
              </div>
              {isJoint && (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-1">Spouse Name</label>
                  <input
                    type="text"
                    value={profile.spouse_name}
                    onChange={(e) => update('spouse_name', e.target.value)}
                    placeholder="Spouse"
                    className="w-full py-2.5 px-3 border border-gray-300 rounded-lg text-sm"
                  />
                </div>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Dependents</label>
                <input
                  type="number" min={0}
                  value={profile.num_dependents}
                  onChange={(e) => update('num_dependents', Number(e.target.value))}
                  className="w-full py-2.5 px-3 border border-gray-300 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Qualifying Children (CTC)</label>
                <input
                  type="number" min={0}
                  value={profile.num_qualifying_children}
                  onChange={(e) => update('num_qualifying_children', Number(e.target.value))}
                  className="w-full py-2.5 px-3 border border-gray-300 rounded-lg text-sm"
                />
              </div>
            </div>
          </div>
        );

      case 1:
        return (
          <div className="space-y-5">
            <h3 className="text-lg font-bold text-gray-800">Employment & Income</h3>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Your Employment</label>
              <select
                value={profile.filer_employment}
                onChange={(e) => update('filer_employment', e.target.value as EmploymentType)}
                className="w-full py-2.5 px-3 border border-gray-300 rounded-lg text-sm"
              >
                {Object.entries(EMPLOYMENT_LABELS).map(([val, label]) => (
                  <option key={val} value={val}>{label}</option>
                ))}
              </select>
            </div>
            {isJoint && (
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Spouse Employment</label>
                <select
                  value={profile.spouse_employment ?? 'w2_employee'}
                  onChange={(e) => update('spouse_employment', e.target.value as EmploymentType)}
                  className="w-full py-2.5 px-3 border border-gray-300 rounded-lg text-sm"
                >
                  {Object.entries(EMPLOYMENT_LABELS).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="space-y-3">
              <p className="text-sm font-semibold text-gray-700">Other Income Sources</p>
              {([
                ['has_freelance_income', 'Freelance / 1099-NEC income'],
                ['has_marketplace_income', '1099-K income (PayPal, Venmo, etc.)'],
                ['has_unemployment', 'Unemployment benefits'],
                ['has_social_security', 'Social Security benefits'],
              ] as const).map(([key, label]) => (
                <label key={key} className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={profile[key]}
                    onChange={(e) => update(key, e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600"
                  />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </div>
          </div>
        );

      case 2:
        return (
          <div className="space-y-5">
            <h3 className="text-lg font-bold text-gray-800">Real Estate</h3>
            <div className="space-y-3">
              {([
                ['has_mortgage', 'I have a mortgage (will receive 1098)'],
                ['purchased_home', 'I purchased a home during this tax year'],
                ['sold_home', 'I sold a home during this tax year'],
                ['has_property_tax', 'I pay property tax'],
                ['has_solar', 'I installed solar panels (Residential Clean Energy Credit)'],
              ] as const).map(([key, label]) => (
                <label key={key} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={profile[key]}
                    onChange={(e) => update(key, e.target.checked)}
                    className="h-5 w-5 rounded border-gray-300 text-blue-600"
                  />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-5">
            <h3 className="text-lg font-bold text-gray-800">Investments & Retirement</h3>
            <div className="space-y-3">
              <p className="text-sm font-semibold text-gray-700">Account Types</p>
              {(Object.entries(INVESTMENT_LABELS) as [InvestmentAccountType, string][]).map(
                ([acct, label]) => (
                  <label key={acct} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={profile.investment_accounts.includes(acct)}
                      onChange={() => toggleInvestment(acct)}
                      className="h-5 w-5 rounded border-gray-300 text-blue-600"
                    />
                    <span className="text-sm text-gray-700">{label}</span>
                  </label>
                ),
              )}
            </div>
            <div className="space-y-3">
              <p className="text-sm font-semibold text-gray-700">Investment Income</p>
              {([
                ['has_bank_interest', 'Earned bank/savings interest (1099-INT)'],
                ['has_dividends', 'Received dividends (1099-DIV)'],
                ['has_capital_gains', 'Sold stocks/bonds/crypto (capital gains/losses)'],
                ['has_retirement_distributions', 'Took retirement distributions (1099-R)'],
              ] as const).map(([key, label]) => (
                <label key={key} className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={profile[key]}
                    onChange={(e) => update(key, e.target.checked)}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600"
                  />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-5">
            <h3 className="text-lg font-bold text-gray-800">Deductions & Credits</h3>
            <div className="space-y-3">
              {([
                ['has_student_loans', 'Paid student loan interest'],
                ['has_education_expenses', 'Paid tuition (1098-T)'],
                ['has_charitable_donations', 'Made charitable donations'],
                ['has_medical_expenses', 'Significant unreimbursed medical expenses'],
                ['has_prior_year_return', 'I have access to last year\'s tax return'],
              ] as const).map(([key, label]) => (
                <label key={key} className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={profile[key]}
                    onChange={(e) => update(key, e.target.checked)}
                    className="h-5 w-5 rounded border-gray-300 text-blue-600"
                  />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">
                Tax Documents Folder (local path)
              </label>
              <input
                type="text"
                value={profile.document_source_path ?? ''}
                onChange={(e) => update('document_source_path', e.target.value || null)}
                placeholder="~/Library/Mobile Documents/com~apple~CloudDocs/Family/Tax/2025"
                className="w-full py-2.5 px-3 border border-gray-300 rounded-lg text-sm font-mono"
              />
              <p className="mt-1 text-xs text-gray-500">
                Path to your iCloud or local folder with tax PDFs. Used for automatic scanning.
              </p>
            </div>
          </div>
        );

      case 5:
        return (
          <div className="space-y-5">
            <h3 className="text-lg font-bold text-gray-800">Review Your Profile</h3>
            <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
              <p><span className="font-semibold">Tax Year:</span> {profile.tax_year}</p>
              <p><span className="font-semibold">Filing Status:</span> {FILING_STATUS_LABELS[profile.filing_status]}</p>
              {profile.filer_name && <p><span className="font-semibold">Filer:</span> {profile.filer_name}</p>}
              {isJoint && profile.spouse_name && (
                <p><span className="font-semibold">Spouse:</span> {profile.spouse_name}</p>
              )}
              <p><span className="font-semibold">Employment:</span> {EMPLOYMENT_LABELS[profile.filer_employment]}</p>
              {isJoint && profile.spouse_employment && (
                <p><span className="font-semibold">Spouse Employment:</span> {EMPLOYMENT_LABELS[profile.spouse_employment]}</p>
              )}
              {profile.num_dependents > 0 && (
                <p><span className="font-semibold">Dependents:</span> {profile.num_dependents}</p>
              )}
            </div>
            <div className="bg-gray-50 rounded-lg p-4 space-y-1 text-sm">
              <p className="font-semibold mb-2">Tax Situation:</p>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1">
                {profile.has_mortgage && <li>✓ Mortgage</li>}
                {profile.purchased_home && <li>✓ Purchased home</li>}
                {profile.sold_home && <li>✓ Sold home</li>}
                {profile.has_property_tax && <li>✓ Property tax</li>}
                {profile.has_solar && <li>✓ Solar installation</li>}
                {profile.has_capital_gains && <li>✓ Capital gains/losses</li>}
                {profile.has_bank_interest && <li>✓ Bank interest</li>}
                {profile.has_dividends && <li>✓ Dividends</li>}
                {profile.has_retirement_distributions && <li>✓ Retirement distributions</li>}
                {profile.has_freelance_income && <li>✓ Freelance income</li>}
                {profile.has_marketplace_income && <li>✓ 1099-K income</li>}
                {profile.has_charitable_donations && <li>✓ Charitable donations</li>}
                {profile.has_student_loans && <li>✓ Student loan interest</li>}
                {profile.has_prior_year_return && <li>✓ Prior year return</li>}
                {profile.investment_accounts.map((a) => (
                  <li key={a}>✓ {INVESTMENT_LABELS[a]}</li>
                ))}
              </ul>
            </div>
            {profile.document_source_path && (
              <div className="bg-blue-50 rounded-lg p-3 text-sm text-blue-700">
                <span className="font-semibold">Document folder:</span>{' '}
                <code className="text-xs">{profile.document_source_path}</code>
              </div>
            )}
          </div>
        );
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-lg p-6">
      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        {STEPS.map((label, i) => (
          <button
            key={label}
            onClick={() => setStep(i)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
              i === step
                ? 'bg-blue-600 text-white'
                : i < step
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-500'
            }`}
          >
            <span className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold border border-current">
              {i < step ? '✓' : i + 1}
            </span>
            {label}
          </button>
        ))}
      </div>

      {/* Step content */}
      <div className="min-h-[300px]">{renderStep()}</div>

      {/* Navigation */}
      <div className="flex justify-between mt-6 pt-4 border-t border-gray-100">
        <button
          onClick={prev}
          disabled={step === 0}
          className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 disabled:opacity-30"
        >
          ← Back
        </button>
        {step < STEPS.length - 1 ? (
          <button
            onClick={next}
            className="px-6 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors"
          >
            Continue →
          </button>
        ) : (
          <button
            onClick={() => onComplete(profile)}
            className="px-6 py-2.5 bg-emerald-600 text-white text-sm font-semibold rounded-lg hover:bg-emerald-700 transition-colors"
          >
            Generate Checklist →
          </button>
        )}
      </div>
    </div>
  );
}
