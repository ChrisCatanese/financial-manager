import { useState } from 'react';
import type {
  DocumentChecklist,
  DocumentItem,
  ScanResult,
} from '../types/documents';
import { DOCUMENT_STATUS_COLORS, DOCUMENT_STATUS_LABELS } from '../types/documents';
import { scanDocuments, uploadDocument } from '../services/documentApi';

interface ChecklistDashboardProps {
  checklist: DocumentChecklist;
  documentPath: string | null;
  onChecklistUpdate: (checklist: DocumentChecklist) => void;
}

export function ChecklistDashboard({
  checklist,
  documentPath,
  onChecklistUpdate,
}: ChecklistDashboardProps) {
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const foundCount = checklist.items.filter((i) => i.status !== 'missing').length;
  const requiredMissing = checklist.items.filter(
    (i) => i.required && i.status === 'missing',
  );
  const progress = checklist.items.length > 0
    ? Math.round((foundCount / checklist.items.length) * 100)
    : 0;

  const handleScan = async () => {
    setScanning(true);
    setError(null);
    try {
      const result = await scanDocuments(documentPath ?? undefined);
      setScanResult(result);
      // Refresh checklist from API
      const res = await fetch('/api/v1/checklist');
      const updated = await res.json();
      if (!('error' in updated)) {
        onChecklistUpdate(updated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Scan failed');
    } finally {
      setScanning(false);
    }
  };

  const handleFileUpload = async (item: DocumentItem, file: File) => {
    setError(null);
    try {
      await uploadDocument(file, item.doc_type);
      // Refresh checklist
      const res = await fetch('/api/v1/checklist');
      const updated = await res.json();
      if (!('error' in updated)) {
        onChecklistUpdate(updated);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    }
  };

  return (
    <div className="space-y-6">
      {/* Progress header */}
      <div className="bg-white rounded-2xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-800">
              Document Checklist — {checklist.tax_year}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {foundCount} of {checklist.items.length} documents collected
            </p>
          </div>
          <div className="text-right">
            <span className="text-3xl font-bold text-blue-600">{progress}%</span>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="h-3 rounded-full bg-gradient-to-r from-blue-500 to-emerald-500 transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>

        {requiredMissing.length > 0 && (
          <p className="mt-3 text-sm text-amber-600 font-medium">
            ⚠ {requiredMissing.length} required document{requiredMissing.length > 1 ? 's' : ''} still missing
          </p>
        )}

        {/* Scan button */}
        {documentPath && (
          <button
            onClick={handleScan}
            disabled={scanning}
            className="mt-4 px-5 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg
                       hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {scanning ? 'Scanning…' : '🔍 Scan Document Folder'}
          </button>
        )}

        {scanResult && (
          <div className="mt-3 p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
            Found {scanResult.files_found} files • Matched {scanResult.checklist_matched} to checklist
            {scanResult.still_missing.length > 0 && (
              <span className="block mt-1 text-amber-600">
                Still missing: {scanResult.still_missing.join(', ')}
              </span>
            )}
          </div>
        )}

        {error && (
          <div className="mt-3 p-3 bg-red-50 rounded-lg text-sm text-red-600">{error}</div>
        )}
      </div>

      {/* Checklist items */}
      <div className="space-y-3">
        {checklist.items.map((item) => (
          <ChecklistItemCard
            key={item.doc_type}
            item={item}
            onUpload={(file) => handleFileUpload(item, file)}
          />
        ))}
      </div>
    </div>
  );
}

function ChecklistItemCard({
  item,
  onUpload,
}: {
  item: DocumentItem;
  onUpload: (file: File) => void;
}) {
  const statusClass = DOCUMENT_STATUS_COLORS[item.status];
  const hasData = Object.keys(item.extracted_data).length > 0;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-gray-800 text-sm">{item.label}</h3>
            {item.required && (
              <span className="text-[10px] font-bold text-red-500 uppercase">Required</span>
            )}
          </div>
          <p className="text-xs text-gray-500 leading-relaxed">{item.description}</p>
          {item.source_path && (
            <p className="mt-1 text-xs text-gray-400 truncate font-mono">{item.source_path}</p>
          )}
          {hasData && (
            <div className="mt-2 p-2 bg-green-50 rounded-lg">
              <p className="text-xs font-semibold text-green-700 mb-1">Extracted Data:</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
                {Object.entries(item.extracted_data).map(([key, value]) => (
                  <p key={key} className="text-xs text-green-600">
                    <span className="font-medium">{key}:</span>{' '}
                    {typeof value === 'number' ? `$${value.toLocaleString()}` : String(value ?? '—')}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col items-end gap-2 shrink-0">
          <span className={`px-2.5 py-1 rounded-full text-xs font-semibold ${statusClass}`}>
            {DOCUMENT_STATUS_LABELS[item.status]}
          </span>

          {item.status === 'missing' && (
            <label className="cursor-pointer px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50
                              rounded-lg hover:bg-blue-100 transition-colors">
              Upload
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.heic"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onUpload(file);
                }}
              />
            </label>
          )}
        </div>
      </div>
    </div>
  );
}
