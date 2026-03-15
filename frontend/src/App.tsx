import { useState } from 'react';
import { TaxForm } from './components/TaxForm';
import { TaxResultDisplay } from './components/TaxResultDisplay';
import { ProfileWizard } from './components/ProfileWizard';
import { ChecklistDashboard } from './components/ChecklistDashboard';
import { ImportHub } from './components/ImportHub';
import { PipelineDashboard } from './components/PipelineDashboard';
import { useTaxCalculator } from './hooks/useTaxCalculator';
import { createProfile, getChecklist } from './services/documentApi';
import type { TaxProfile, DocumentChecklist } from './types/documents';

type AppView = 'dashboard' | 'setup' | 'checklist' | 'import' | 'calculator';

function App() {
  const { result, loading, error, calculate } = useTaxCalculator();
  const [view, setView] = useState<AppView>('dashboard');
  const [profile, setProfile] = useState<TaxProfile | null>(null);
  const [checklist, setChecklist] = useState<DocumentChecklist | null>(null);
  const [setupError, setSetupError] = useState<string | null>(null);

  const handleProfileComplete = async (newProfile: TaxProfile) => {
    setSetupError(null);
    try {
      await createProfile(newProfile);
      setProfile(newProfile);
      const cl = await getChecklist();
      if (cl) {
        setChecklist(cl);
        setView('checklist');
      }
    } catch (err) {
      setSetupError(err instanceof Error ? err.message : 'Failed to create profile');
    }
  };

  const navItems: { key: AppView; label: string; icon: string }[] = [
    { key: 'dashboard', label: 'Dashboard', icon: '⚡' },
    { key: 'setup', label: 'Profile', icon: '👤' },
    { key: 'checklist', label: 'Documents', icon: '📋' },
    { key: 'import', label: 'Import', icon: '📥' },
    { key: 'calculator', label: 'Calculator', icon: '🧮' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-2xl">&#x1f3e6;</div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Financial Manager</h1>
              <p className="text-xs text-gray-500">US Federal Tax Calculator</p>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex items-center gap-1">
            {navItems.map(({ key, label, icon }) => (
              <button
                key={key}
                onClick={() => setView(key)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  view === key
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                <span>{icon}</span>
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {setupError && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 mb-6">
            <p className="text-sm">{setupError}</p>
          </div>
        )}

        {/* Pipeline Dashboard */}
        {view === 'dashboard' && <PipelineDashboard />}

        {/* Setup / Profile Wizard */}
        {view === 'setup' && (
          <div className="max-w-2xl mx-auto">
            <ProfileWizard onComplete={handleProfileComplete} />
          </div>
        )}

        {/* Document Checklist */}
        {view === 'checklist' && checklist ? (
          <ChecklistDashboard
            checklist={checklist}
            documentPath={profile?.document_source_path ?? null}
            onChecklistUpdate={setChecklist}
          />
        ) : view === 'checklist' && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-12 text-center">
            <div className="text-5xl mb-4">📋</div>
            <h3 className="text-lg font-semibold text-gray-700">No Checklist Yet</h3>
            <p className="text-sm text-gray-500 mt-2">
              Complete the profile setup first to generate your document checklist.
            </p>
            <button
              onClick={() => setView('setup')}
              className="mt-4 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700"
            >
              Go to Setup
            </button>
          </div>
        )}

        {/* Import Hub */}
        {view === 'import' && <ImportHub />}

        {/* Calculator */}
        {view === 'calculator' && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
            <div className="lg:col-span-2">
              <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-4">Tax Information</h2>
                <TaxForm onSubmit={calculate} loading={loading} />
              </div>
            </div>

            <div className="lg:col-span-3">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 mb-4">
                  <p className="text-sm font-medium">Calculation Error</p>
                  <p className="text-sm mt-1">{error}</p>
                </div>
              )}

              {result ? (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
                  <h2 className="text-lg font-bold text-gray-900 mb-4">Tax Results</h2>
                  <TaxResultDisplay result={result} />
                </div>
              ) : (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-12 text-center">
                  <div className="text-5xl mb-4">&#x1f4ca;</div>
                  <h3 className="text-lg font-semibold text-gray-700">Enter your information</h3>
                  <p className="text-sm text-gray-500 mt-2">
                    Fill out the form and click Calculate to see your federal tax breakdown.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <footer className="border-t border-gray-200 mt-12">
        <div className="max-w-5xl mx-auto px-4 py-6 text-center text-xs text-gray-400">
          For estimation purposes only. Not tax advice. Consult a qualified tax professional.
        </div>
      </footer>
    </div>
  );
}

export default App;
