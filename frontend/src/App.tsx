import { TaxForm } from './components/TaxForm';
import { TaxResultDisplay } from './components/TaxResultDisplay';
import { useTaxCalculator } from './hooks/useTaxCalculator';

function App() {
  const { result, loading, error, calculate } = useTaxCalculator();

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="text-2xl">&#x1f3e6;</div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Financial Manager</h1>
            <p className="text-xs text-gray-500">US Federal Tax Calculator</p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
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
      </main>

      <footer className="border-t border-gray-200 mt-12">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center text-xs text-gray-400">
          For estimation purposes only. Not tax advice. Consult a qualified tax professional.
        </div>
      </footer>
    </div>
  );
}

export default App;
