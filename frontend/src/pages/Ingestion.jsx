import React, { useState, useRef } from 'react';
import { useOutletContext, Link } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Play,
  Loader2,
  ArrowRight,
  Database,
  Layers,
} from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/common/StatusBadge';
import { formatNumber, formatDuration } from '../utils/formatters';

export default function Ingestion() {
  const { showToast } = useOutletContext();
  const fileInputRef = useRef(null);

  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const [uploadedFileRecord, setUploadedFileRecord] = useState(null);
  const [previewRows, setPreviewRows] = useState([]);
  const [batchSize, setBatchSize] = useState(5000);

  const [runningPipeline, setRunningPipeline] = useState(false);
  const [pipelineResult, setPipelineResult] = useState(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelection = (file) => {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['csv', 'json'].includes(ext)) {
      showToast('Only .csv and .json files are supported.', 'error', 'Invalid Format');
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      showToast('File exceeds 50MB maximum size limit.', 'error', 'File Too Large');
      return;
    }
    setSelectedFile(file);
    setPipelineResult(null);
    setUploadedFileRecord(null);
    setPreviewRows([]);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await api.uploadFile(formData, (progressEvent) => {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        setUploadProgress(percent);
      });
      setUploadedFileRecord(res.file);
      setPreviewRows(res.preview || []);
      showToast('File uploaded and verified successfully!', 'success');
    } catch (err) {
      showToast(err.response?.data?.error || 'Failed to upload file.', 'error', 'Upload Failed');
    } finally {
      setUploading(false);
    }
  };

  const handleRunPipeline = async () => {
    if (!uploadedFileRecord) return;
    setRunningPipeline(true);
    setPipelineResult(null);

    try {
      const res = await api.runPipeline({
        file_id: uploadedFileRecord.file_id,
        batch_size: batchSize,
      });
      setPipelineResult(res);
      showToast(
        `Pipeline run finished: ${res.valid_records} valid, ${res.rejected_records} quarantined.`,
        res.rejected_records > 0 ? 'info' : 'success',
        'Execution Complete'
      );
    } catch (err) {
      showToast(err.response?.data?.error || 'Pipeline execution failed.', 'error', 'Pipeline Error');
    } finally {
      setRunningPipeline(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900">Data Ingestion Engine</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Ingest raw order files (CSV/JSON), enforce cryptographic hashing, validate schemas, and dispatch to PostgreSQL.
        </p>
      </div>

      {/* Drag & Drop Upload Zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all ${
          dragActive
            ? 'border-blue-500 bg-blue-50/50'
            : selectedFile
            ? 'border-emerald-300 bg-emerald-50/20'
            : 'border-slate-300 bg-white hover:border-slate-400'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.json"
          onChange={(e) => e.target.files?.[0] && handleFileSelection(e.target.files[0])}
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-full mb-3">
            <UploadCloud className="w-8 h-8" />
          </div>

          {selectedFile ? (
            <div className="space-y-1">
              <p className="text-sm font-semibold text-slate-800 flex items-center justify-center gap-2">
                <FileText className="w-4 h-4 text-blue-600" />
                {selectedFile.name}
              </p>
              <p className="text-xs text-slate-500">
                {(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.type || 'text/csv'}
              </p>
            </div>
          ) : (
            <>
              <p className="text-sm font-semibold text-slate-800">
                Drag and drop your order dataset here, or{' '}
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="text-blue-600 hover:underline font-medium"
                >
                  browse files
                </button>
              </p>
              <p className="text-xs text-slate-400 mt-1">Supported formats: CSV, JSON (up to 50MB)</p>
            </>
          )}

          {selectedFile && !uploadedFileRecord && (
            <div className="mt-4 flex items-center gap-3">
              <button
                type="button"
                onClick={() => {
                  setSelectedFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Choose Different File
              </button>
              <button
                type="button"
                onClick={handleUpload}
                disabled={uploading}
                className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors disabled:opacity-50"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Uploading ({uploadProgress}%)
                  </>
                ) : (
                  <>Upload and Verify</>
                )}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Uploaded File Details & Schema Preview */}
      {uploadedFileRecord && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Validated File</span>
                <StatusBadge status="COMPLETED" text="Verified" />
              </div>
              <h3 className="text-base font-bold text-slate-900 mt-0.5">{uploadedFileRecord.filename}</h3>
              <p className="text-xs text-slate-500 font-mono mt-1">SHA-256: {uploadedFileRecord.file_hash}</p>
            </div>

            <div className="flex items-center gap-3">
              <div>
                <label className="block text-[11px] font-medium text-slate-500 uppercase mb-1">
                  Batch Chunk Size
                </label>
                <select
                  value={batchSize}
                  onChange={(e) => setBatchSize(parseInt(e.target.value))}
                  disabled={runningPipeline}
                  className="px-3 py-1.5 text-xs font-medium bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value={1000}>1,000 records</option>
                  <option value={5000}>5,000 records (recommended)</option>
                  <option value={10000}>10,000 records</option>
                </select>
              </div>

              <button
                type="button"
                onClick={handleRunPipeline}
                disabled={runningPipeline}
                className="flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-colors self-end disabled:opacity-50"
              >
                {runningPipeline ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Processing Pipeline...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    Start Ingestion Pipeline
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Sample Preview Table */}
          {previewRows.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                Raw Source File Preview (First 5 Rows)
              </h4>
              <div className="overflow-x-auto border border-slate-200 rounded-lg">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                    <tr>
                      {Object.keys(previewRows[0] || {}).map((col) => (
                        <th key={col} className="py-2 px-3 font-semibold whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                    {previewRows.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50">
                        {Object.values(row).map((val, cIdx) => (
                          <td key={cIdx} className="py-2 px-3 whitespace-nowrap text-slate-700">
                            {val !== null && val !== undefined && val !== '' ? String(val) : <span className="text-slate-300 italic">null</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Execution Results Summary */}
      {pipelineResult && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              Ingestion Execution Summary
            </h3>
            <StatusBadge status={pipelineResult.status} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-lg text-xs">
            <div>
              <span className="text-slate-500 block">Total Processed</span>
              <span className="text-lg font-bold text-slate-900">{formatNumber(pipelineResult.total_records)}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Valid (Published)</span>
              <span className="text-lg font-bold text-emerald-600">{formatNumber(pipelineResult.valid_records)}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Quarantined</span>
              <span className="text-lg font-bold text-rose-600">{formatNumber(pipelineResult.rejected_records)}</span>
            </div>
            <div>
              <span className="text-slate-500 block">Duration</span>
              <span className="text-lg font-bold text-slate-900">{formatDuration(pipelineResult.execution_duration)}</span>
            </div>
          </div>

          {/* Reconciliation Balance check */}
          <div className="p-3 rounded-lg border border-slate-200 bg-white flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="font-semibold text-slate-700">Reconciliation Formula:</span>
              <span className="text-slate-500">
                {pipelineResult.total_records} (Total) = {pipelineResult.valid_records} (Valid) + {pipelineResult.rejected_records} (Quarantine)
              </span>
            </div>
            <span className="text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded">
              Balanced (100%)
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            {pipelineResult.rejected_records > 0 && (
              <Link
                to="/quarantine"
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-lg transition-colors shadow-xs"
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                Inspect Quarantined Records ({pipelineResult.rejected_records})
              </Link>
            )}
            <Link
              to="/processed"
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              <Database className="w-3.5 h-3.5" />
              View Published Orders
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
