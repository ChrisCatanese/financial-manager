import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  FileAssessment,
  FolderNode,
  ImportConfig,
  ProcessResult,
  ScannedFile,
  ScanExportsResult,
} from '../types/imports';
import {
  CATEGORY_ICONS,
  FILE_TYPE_ICONS,
  OWNER_LABELS,
} from '../types/imports';
import {
  assessFile,
  getImportConfig,
  listExistingFiles,
  processImports,
  scanExportFolders,
  uploadToICloud,
} from '../services/importApi';

// ── Sub-components ───────────────────────────────────────────────────

function FolderTree({ nodes }: { nodes: FolderNode[] }) {
  return (
    <div className="space-y-1">
      {nodes.map((node) => (
        <FolderTreeNode key={node.path} node={node} depth={0} />
      ))}
    </div>
  );
}

function FolderTreeNode({ node, depth }: { node: FolderNode; depth: number }) {
  const [open, setOpen] = useState(depth < 1);
  const hasChildren = node.children.length > 0;
  const icon = CATEGORY_ICONS[node.category] ?? '📁';

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className={`flex items-center gap-2 w-full text-left px-2 py-1.5 rounded-lg text-sm hover:bg-gray-50 transition-colors ${
          depth === 0 ? 'font-semibold text-gray-800' : 'text-gray-600'
        }`}
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
      >
        {hasChildren && (
          <span className={`text-xs text-gray-400 transition-transform ${open ? 'rotate-90' : ''}`}>▶</span>
        )}
        {!hasChildren && <span className="w-3" />}
        <span>{icon}</span>
        <span className="flex-1">{node.name}</span>
        {node.file_count > 0 && (
          <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
            {node.file_count}
          </span>
        )}
      </button>
      {open && hasChildren && (
        <div>
          {node.children.map((child) => (
            <FolderTreeNode key={child.path} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatCurrency(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n);
}

// ── Assessment card for a single file ────────────────────────────────

function AssessmentCard({
  assessment,
  filerNames,
  onUpload,
  uploading,
}: {
  assessment: FileAssessment;
  filerNames: { primary?: string; spouse?: string };
  onUpload: (a: FileAssessment, overrides: { owner: string; destination: string }) => void;
  uploading: boolean;
}) {
  const [owner, setOwner] = useState(assessment.detected_owner || 'joint');
  const [destination, setDestination] = useState(assessment.suggested_destination || '');

  const ownerLabel = (role: string) => {
    if (role === 'primary') return filerNames.primary ?? 'Primary';
    if (role === 'spouse') return filerNames.spouse ?? 'Spouse';
    return 'Joint';
  };

  return (
    <div className={`border rounded-xl p-4 ${assessment.can_import ? 'border-gray-200 bg-white' : 'border-amber-200 bg-amber-50'}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-xl">{FILE_TYPE_ICONS[assessment.file_type] ?? '📁'}</span>
          <div className="min-w-0">
            <p className="font-semibold text-gray-800 text-sm truncate">{assessment.filename}</p>
            <p className="text-xs text-gray-500">
              {formatBytes(assessment.file_size)} · {assessment.detected_format || assessment.file_type.toUpperCase()}
            </p>
          </div>
        </div>
        {assessment.detected_institution && (
          <span className="text-xs font-medium bg-blue-50 text-blue-700 px-2 py-1 rounded-lg whitespace-nowrap">
            {assessment.detected_institution}
          </span>
        )}
      </div>

      {/* Stats row */}
      {(assessment.record_count > 0 || assessment.date_range) && (
        <div className="flex gap-4 mt-3 text-xs text-gray-600">
          {assessment.record_count > 0 && (
            <span>📋 {assessment.record_count} records</span>
          )}
          {assessment.date_range && (
            <span>📅 {assessment.date_range}</span>
          )}
        </div>
      )}

      {/* Preview table */}
      {assessment.preview_data.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100">
                {Object.keys(assessment.preview_data[0]).map((key) => (
                  <th key={key} className="text-left py-1 px-2 font-medium text-gray-500 capitalize">
                    {key.replace(/_/g, ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {assessment.preview_data.map((row, i) => (
                <tr key={i} className="border-b border-gray-50">
                  {Object.values(row).map((val, j) => (
                    <td key={j} className="py-1 px-2 text-gray-700 truncate max-w-[140px]">
                      {typeof val === 'number' ? val.toLocaleString() : String(val ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Warnings */}
      {assessment.warnings.length > 0 && (
        <div className="mt-3 space-y-1">
          {assessment.warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-700 flex items-center gap-1">
              <span>⚠️</span> {w}
            </p>
          ))}
        </div>
      )}

      {/* Override controls */}
      <div className="mt-4 flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Owner</label>
          <select
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="joint">{ownerLabel('joint')}</option>
            <option value="primary">{ownerLabel('primary')}</option>
            <option value="spouse">{ownerLabel('spouse')}</option>
          </select>
        </div>

        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">Destination</label>
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Auto-detected iCloud folder"
          />
        </div>

        <button
          onClick={() => onUpload(assessment, { owner, destination })}
          disabled={uploading || !assessment.can_import}
          className="px-4 py-1.5 text-sm font-semibold rounded-lg transition-colors disabled:opacity-50
            bg-blue-600 text-white hover:bg-blue-700"
        >
          {uploading ? '⏳ Saving…' : '☁️ Save to iCloud'}
        </button>
      </div>
    </div>
  );
}

// ── Main Import Hub component ────────────────────────────────────────

type HubTab = 'upload' | 'files' | 'exports' | 'summary';

export function ImportHub() {
  const [tab, setTab] = useState<HubTab>('upload');
  const [config, setConfig] = useState<ImportConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload state
  const [assessments, setAssessments] = useState<FileAssessment[]>([]);
  const [assessing, setAssessing] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const [uploadResults, setUploadResults] = useState<string[]>([]);
  const dropRef = useRef<HTMLDivElement>(null);
  const [dragOver, setDragOver] = useState(false);

  // Files state
  const [files, setFiles] = useState<ScannedFile[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);

  // Exports state
  const [exportScan, setExportScan] = useState<ScanExportsResult | null>(null);
  const [scanningExports, setScanningExports] = useState(false);

  // Summary state
  const [summary, setSummary] = useState<ProcessResult | null>(null);
  const [processing, setProcessing] = useState(false);

  // Load config on mount
  useEffect(() => {
    getImportConfig()
      .then((c) => { setConfig(c); setLoading(false); })
      .catch((e) => { setError(e.message); setLoading(false); });
  }, []);

  // Derived filer names
  const filerNames = {
    primary: config?.filers.find((f) => f.role === 'primary')?.name.split(' ')[0],
    spouse: config?.filers.find((f) => f.role === 'spouse')?.name.split(' ')[0],
  };

  // ── Handlers ───────────────────────────────────────────────────

  const handleFiles = useCallback(async (fileList: FileList | File[]) => {
    setAssessing(true);
    setError(null);
    const newAssessments: FileAssessment[] = [];

    for (const file of Array.from(fileList)) {
      try {
        const result = await assessFile(file);
        // Stash the File object on the assessment for later upload
        const a = { ...result.assessment, _file: file } as FileAssessment & { _file: File };
        newAssessments.push(a);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Assessment failed');
      }
    }

    setAssessments((prev) => [...prev, ...newAssessments]);
    setAssessing(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  }, [handleFiles]);

  const handleUpload = useCallback(async (
    assessment: FileAssessment & { _file?: File },
    overrides: { owner: string; destination: string },
  ) => {
    if (!assessment._file) return;
    setUploading(assessment.filename);
    try {
      const result = await uploadToICloud(assessment._file, {
        destination: overrides.destination,
        owner: overrides.owner,
      });
      setUploadResults((prev) => [...prev, `✅ ${assessment.filename} → ${result.icloud_relative}`]);
      setAssessments((prev) => prev.filter((a) => a.filename !== assessment.filename));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(null);
    }
  }, []);

  const handleLoadFiles = useCallback(async () => {
    setFilesLoading(true);
    try {
      const result = await listExistingFiles();
      setFiles(result.files);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to list files');
    } finally {
      setFilesLoading(false);
    }
  }, []);

  const handleScanExports = useCallback(async () => {
    setScanningExports(true);
    try {
      const result = await scanExportFolders();
      setExportScan(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export scan failed');
    } finally {
      setScanningExports(false);
    }
  }, []);

  const handleProcess = useCallback(async () => {
    setProcessing(true);
    try {
      const result = await processImports(config?.tax_year);
      setSummary(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
    } finally {
      setProcessing(false);
    }
  }, [config?.tax_year]);

  // ── Loading state ──────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="text-4xl mb-3 animate-pulse">📥</div>
          <p className="text-gray-500 text-sm">Loading import configuration…</p>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-6 text-center">
        <p className="font-medium">Import configuration not available</p>
        <p className="text-sm mt-1">{error ?? 'Check config/user-config.yaml'}</p>
      </div>
    );
  }

  // ── Tab definitions ────────────────────────────────────────────

  const tabs: { key: HubTab; label: string; icon: string }[] = [
    { key: 'upload', label: 'Upload', icon: '⬆️' },
    { key: 'files', label: 'My Files', icon: '📂' },
    { key: 'exports', label: 'Scan Downloads', icon: '🔍' },
    { key: 'summary', label: 'Tax Summary', icon: '📊' },
  ];

  return (
    <div className="space-y-6">
      {/* Header card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-800">
              Financial Data Import — {config.tax_year}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Upload documents to iCloud · {config.filers.map((f) => f.name).join(' & ')}
            </p>
          </div>
          <div className="text-sm text-gray-500">
            <span className="font-medium">{config.accounts.length}</span> accounts ·{' '}
            <span className="font-medium">{config.properties.length}</span> properties
          </div>
        </div>

        {/* Sub-navigation */}
        <div className="flex gap-1 mt-5 border-b border-gray-100 -mx-6 px-6">
          {tabs.map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => {
                setTab(key);
                if (key === 'files') handleLoadFiles();
              }}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <span>{icon}</span>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 flex items-center justify-between">
          <p className="text-sm">{error}</p>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 text-lg">×</button>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════ */}
      {/* Upload tab                                                 */}
      {/* ══════════════════════════════════════════════════════════ */}
      {tab === 'upload' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: Upload + assessments */}
          <div className="lg:col-span-2 space-y-4">
            {/* Drop zone */}
            <div
              ref={dropRef}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-2xl p-8 text-center transition-colors cursor-pointer ${
                dragOver
                  ? 'border-blue-400 bg-blue-50'
                  : 'border-gray-300 bg-white hover:border-blue-300 hover:bg-blue-50/30'
              }`}
              onClick={() => {
                const input = document.createElement('input');
                input.type = 'file';
                input.multiple = true;
                input.accept = '.csv,.ofx,.qfx,.pdf,.jpg,.jpeg,.png,.heic,.tif,.tiff';
                input.onchange = () => { if (input.files) handleFiles(input.files); };
                input.click();
              }}
            >
              {assessing ? (
                <>
                  <div className="text-4xl mb-3 animate-pulse">🔍</div>
                  <p className="text-gray-600 font-medium">Analyzing files…</p>
                </>
              ) : (
                <>
                  <div className="text-4xl mb-3">☁️</div>
                  <p className="text-gray-700 font-semibold">Drop files here or click to browse</p>
                  <p className="text-sm text-gray-500 mt-1">
                    CSV, OFX, QFX, PDF, images — auto-detected and organized into iCloud
                  </p>
                </>
              )}
            </div>

            {/* Upload success messages */}
            {uploadResults.length > 0 && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                <p className="text-sm font-medium text-emerald-700 mb-2">Recent uploads</p>
                {uploadResults.map((msg, i) => (
                  <p key={i} className="text-xs text-emerald-600">{msg}</p>
                ))}
              </div>
            )}

            {/* Assessment cards */}
            {assessments.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-700">
                    {assessments.length} file{assessments.length > 1 ? 's' : ''} ready to organize
                  </h3>
                  <button
                    onClick={() => setAssessments([])}
                    className="text-xs text-gray-400 hover:text-gray-600"
                  >
                    Clear all
                  </button>
                </div>
                {assessments.map((a) => (
                  <AssessmentCard
                    key={a.filename}
                    assessment={a}
                    filerNames={filerNames}
                    onUpload={handleUpload}
                    uploading={uploading === a.filename}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Right: iCloud folder structure */}
          <div className="space-y-4">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2 mb-3">
                <span>☁️</span> iCloud Folder Structure
              </h3>
              <p className="text-xs text-gray-500 mb-3">
                Files are organized here automatically
              </p>
              <FolderTree nodes={config.folder_tree} />
            </div>

            {/* Accounts quick reference */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-800 mb-3">📋 Configured Accounts</h3>
              <div className="space-y-2">
                {config.accounts.map((acct) => (
                  <div key={acct.institution} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <span>{CATEGORY_ICONS[acct.account_type] ?? '🏦'}</span>
                      <span className="font-medium text-gray-700">{acct.institution}</span>
                    </div>
                    <span className="text-xs text-gray-400">
                      {OWNER_LABELS[acct.owner] ?? acct.owner}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════ */}
      {/* My Files tab — what's already in iCloud                    */}
      {/* ══════════════════════════════════════════════════════════ */}
      {tab === 'files' && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-5 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-800">Files in iCloud</h3>
              <p className="text-xs text-gray-500 mt-0.5">{files.length} files found</p>
            </div>
            <button
              onClick={handleLoadFiles}
              disabled={filesLoading}
              className="px-4 py-2 text-sm font-semibold rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors disabled:opacity-50"
            >
              {filesLoading ? '⏳ Scanning…' : '🔄 Refresh'}
            </button>
          </div>

          {files.length === 0 ? (
            <div className="p-12 text-center">
              <div className="text-4xl mb-3">📂</div>
              <p className="text-gray-500 text-sm">
                {filesLoading ? 'Loading files…' : 'No files found in iCloud tax folder yet'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 text-left">
                    <th className="px-5 py-3 font-medium text-gray-500">File</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Folder</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Owner</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Type</th>
                    <th className="px-5 py-3 font-medium text-gray-500 text-right">Size</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Modified</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((f, i) => (
                    <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-2">
                          <span>{FILE_TYPE_ICONS[f.file_type] ?? '📁'}</span>
                          <span className="font-medium text-gray-800 truncate max-w-[200px]">{f.filename}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3 text-gray-600">{f.folder}</td>
                      <td className="px-5 py-3">
                        <span className="text-xs font-medium bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                          {OWNER_LABELS[f.owner] ?? f.owner}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-gray-500 uppercase text-xs">{f.file_type}</td>
                      <td className="px-5 py-3 text-gray-500 text-right">{formatBytes(f.file_size)}</td>
                      <td className="px-5 py-3 text-gray-500 text-xs">
                        {new Date(f.modified).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════ */}
      {/* Scan Downloads tab — find exports from configured paths    */}
      {/* ══════════════════════════════════════════════════════════ */}
      {tab === 'exports' && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">Scan Download Folders</h3>
                <p className="text-sm text-gray-500 mt-0.5">
                  Check your configured export paths for new financial data files
                </p>
              </div>
              <button
                onClick={handleScanExports}
                disabled={scanningExports}
                className="px-5 py-2.5 text-sm font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {scanningExports ? '⏳ Scanning…' : '🔍 Scan Downloads'}
              </button>
            </div>

            {/* Show configured paths */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {config.accounts.filter((a) => a.export_path).map((acct) => (
                <div key={acct.institution} className="bg-gray-50 rounded-xl p-3">
                  <div className="flex items-center gap-2 mb-1">
                    <span>{CATEGORY_ICONS[acct.account_type] ?? '🏦'}</span>
                    <span className="text-sm font-medium text-gray-700">{acct.institution}</span>
                  </div>
                  <p className="text-xs text-gray-500 font-mono truncate">{acct.export_path}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Scan results */}
          {exportScan && (
            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="text-2xl">📥</div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">
                    Found {exportScan.files_found} file{exportScan.files_found !== 1 ? 's' : ''}
                  </h3>
                  <p className="text-xs text-gray-500">
                    Scanned {exportScan.accounts_scanned} account folder{exportScan.accounts_scanned !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>

              {exportScan.files_found === 0 ? (
                <p className="text-sm text-gray-500 py-4 text-center">
                  No supported files found. Download CSV or OFX/QFX exports from your institutions first.
                </p>
              ) : (
                <div className="space-y-3">
                  {exportScan.assessments.map((a) => (
                    <AssessmentCard
                      key={a.file_path}
                      assessment={a}
                      filerNames={filerNames}
                      onUpload={handleUpload}
                      uploading={uploading === a.filename}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════ */}
      {/* Tax Summary tab — process and show totals                  */}
      {/* ══════════════════════════════════════════════════════════ */}
      {tab === 'summary' && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">Tax Summary</h3>
                <p className="text-sm text-gray-500 mt-0.5">
                  Process all imported financial data into tax-relevant totals
                </p>
              </div>
              <button
                onClick={handleProcess}
                disabled={processing}
                className="px-5 py-2.5 text-sm font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-colors disabled:opacity-50"
              >
                {processing ? '⏳ Processing…' : '⚡ Generate Summary'}
              </button>
            </div>
          </div>

          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Sources */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Sources</p>
                <p className="text-3xl font-bold text-gray-800 mt-1">{summary.sources_imported}</p>
                <p className="text-xs text-gray-500 mt-1">files processed</p>
              </div>

              {/* Interest */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Interest Income</p>
                <p className="text-3xl font-bold text-blue-600 mt-1">{formatCurrency(summary.total_interest)}</p>
                <p className="text-xs text-gray-500 mt-1">→ Form 1099-INT</p>
              </div>

              {/* Dividends */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Ordinary Dividends</p>
                <p className="text-3xl font-bold text-emerald-600 mt-1">{formatCurrency(summary.total_ordinary_dividends)}</p>
                <p className="text-xs text-gray-500 mt-1">
                  Qualified: {formatCurrency(summary.total_qualified_dividends)} → Form 1099-DIV
                </p>
              </div>

              {/* Short-term gains */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Short-Term Gains</p>
                <p className={`text-3xl font-bold mt-1 ${summary.total_short_term_gains >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(summary.total_short_term_gains)}
                </p>
                <p className="text-xs text-gray-500 mt-1">→ Schedule D</p>
              </div>

              {/* Long-term gains */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-5">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wider">Long-Term Gains</p>
                <p className={`text-3xl font-bold mt-1 ${summary.total_long_term_gains >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(summary.total_long_term_gains)}
                </p>
                <p className="text-xs text-gray-500 mt-1">→ Schedule D (preferential rates)</p>
              </div>

              {/* Total net investment income */}
              <div className="bg-gradient-to-br from-blue-50 to-emerald-50 rounded-2xl shadow-sm border border-blue-200 p-5">
                <p className="text-xs font-medium text-blue-600 uppercase tracking-wider">Net Investment Income</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">
                  {formatCurrency(
                    summary.total_interest +
                    summary.total_ordinary_dividends +
                    summary.total_short_term_gains +
                    summary.total_long_term_gains
                  )}
                </p>
                <p className="text-xs text-gray-500 mt-1">Combined from all sources</p>
              </div>
            </div>
          )}

          {summary && summary.warnings.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <p className="text-sm font-medium text-amber-700 mb-2">⚠️ Warnings</p>
              {summary.warnings.map((w, i) => (
                <p key={i} className="text-xs text-amber-600">• {w}</p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
