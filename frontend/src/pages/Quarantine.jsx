import React, { useState, useEffect } from 'react';
import { useOutletContext, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  Search,
  Filter,
  RefreshCw,
  Edit3,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  Clock,
  CheckCircle,
} from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/common/StatusBadge';
import LoadingState from '../components/common/LoadingState';
import CorrectionModal from '../components/quarantine/CorrectionModal';
import { formatNumber, formatDateTime, truncateId } from '../utils/formatters';

export default function Quarantine() {
  const { showToast } = useOutletContext();
  const [searchParams, setSearchParams] = useSearchParams();

  const [loading, setLoading] = useState(true);
  const [records, setRecords] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [summary, setSummary] = useState(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState(searchParams.get('search') || '');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [errorFilter, setErrorFilter] = useState(searchParams.get('error_code') || '');

  // Selected for inspection & correction
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSavingCorrection, setIsSavingCorrection] = useState(false);

  const fetchSummary = async () => {
    try {
      const sum = await api.getQuarantineSummary();
      setSummary(sum);
    } catch (e) {
      console.error('Failed to load quarantine summary:', e);
    }
  };

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        search: searchTerm || undefined,
        status: statusFilter || undefined,
        error_code: errorFilter || undefined,
      };
      const res = await api.getQuarantineRecords(params);
      setRecords(res.results || []);
      setTotalCount(res.count || 0);
    } catch (err) {
      showToast(err.response?.data?.error || 'Failed to load quarantine records.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const errorParam = searchParams.get('error_code');
    if (errorParam !== null && errorParam !== undefined) {
      setErrorFilter(errorParam);
    }
    const statParam = searchParams.get('status');
    if (statParam !== null && statParam !== undefined) {
      setStatusFilter(statParam);
    }
  }, [searchParams]);

  useEffect(() => {
    fetchSummary();
  }, []);

  useEffect(() => {
    fetchRecords();
  }, [page, statusFilter, errorFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchRecords();
  };

  const handleInspect = async (quarantineId) => {
    try {
      const fullRecord = await api.getQuarantineRecord(quarantineId);
      setSelectedRecord(fullRecord);
      setIsModalOpen(true);
    } catch (err) {
      showToast('Could not load record details.', 'error');
    }
  };

  const handleSaveCorrection = async (quarantineId, correctedPayload, notes) => {
    setIsSavingCorrection(true);
    try {
      const res = await api.correctQuarantineRecord(quarantineId, {
        corrected_record: correctedPayload,
        notes: notes || 'Operator correction in dashboard',
      });
      showToast('Correction saved successfully! Record is now marked CORRECTED and ready for replay.', 'success', 'Saved');
      setIsModalOpen(false);
      fetchRecords();
      fetchSummary();
    } catch (err) {
      showToast(err.response?.data?.error || 'Failed to save correction.', 'error');
    } finally {
      setIsSavingCorrection(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Quarantine Ledger</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Immutable audit store for invalid records. Operators can inspect root cause errors, apply field corrections, and approve records for controlled replay.
          </p>
        </div>
        <button
          onClick={() => {
            fetchSummary();
            fetchRecords();
          }}
          className="self-start sm:self-auto flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Store
        </button>
      </div>

      {/* Summary KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 text-xs">
          <div className="bg-white border border-slate-200 rounded-xl p-3.5 sm:p-4 shadow-xs">
            <span className="text-slate-500 block uppercase font-semibold text-[10px] tracking-wider">Total Quarantined</span>
            <span className="text-lg sm:text-xl font-bold text-slate-900 mt-1 block">{formatNumber(summary.total_quarantined)}</span>
          </div>
          <div className="bg-white border border-amber-200 rounded-xl p-3.5 sm:p-4 shadow-xs bg-amber-50/20">
            <span className="text-amber-700 block uppercase font-semibold text-[10px] tracking-wider">Pending Correction</span>
            <span className="text-lg sm:text-xl font-bold text-amber-600 mt-1 block">
              {formatNumber(summary.status_breakdown?.PENDING || 0)}
            </span>
          </div>
          <div className="bg-white border border-indigo-200 rounded-xl p-3.5 sm:p-4 shadow-xs bg-indigo-50/20">
            <span className="text-indigo-700 block uppercase font-semibold text-[10px] tracking-wider">Ready for Replay</span>
            <span className="text-lg sm:text-xl font-bold text-indigo-600 mt-1 block">
              {formatNumber(summary.eligible_for_replay || 0)}
            </span>
          </div>
          <div className="bg-white border border-emerald-200 rounded-xl p-3.5 sm:p-4 shadow-xs bg-emerald-50/20">
            <span className="text-emerald-700 block uppercase font-semibold text-[10px] tracking-wider">Successfully Replayed</span>
            <span className="text-lg sm:text-xl font-bold text-emerald-600 mt-1 block">
              {formatNumber(summary.status_breakdown?.REPLAYED || 0)}
            </span>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-3.5 sm:p-4 shadow-xs flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="relative w-full lg:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by record ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </form>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full lg:w-auto items-center">
          {/* Status Filter */}
          <div className="flex items-center gap-1.5 text-xs text-slate-600 w-full">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Statuses</option>
              <option value="PENDING">Pending Correction</option>
              <option value="CORRECTED">Corrected (Ready for Replay)</option>
              <option value="REPLAYED">Successfully Replayed</option>
              <option value="FAILED">Replay Failed</option>
            </select>
          </div>

          {/* Error Type Filter */}
          <div className="flex items-center gap-1.5 text-xs text-slate-600 w-full">
            <select
              value={errorFilter}
              onChange={(e) => {
                setErrorFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Error Codes</option>
              <option value="ERR_INVALID_TYPE">ERR_INVALID_TYPE</option>
              <option value="ERR_INVALID_QUANTITY">ERR_INVALID_QUANTITY</option>
              <option value="ERR_INVALID_PRICE">ERR_INVALID_PRICE</option>
              <option value="ERR_INVALID_STATUS">ERR_INVALID_STATUS</option>
              <option value="ERR_INVALID_DATE_FORMAT">ERR_INVALID_DATE_FORMAT</option>
              <option value="ERR_INVALID_DATE_RANGE">ERR_INVALID_DATE_RANGE</option>
              <option value="ERR_MISSING_FIELD">ERR_MISSING_FIELD</option>
              <option value="ERR_NULL_VALUE">ERR_NULL_VALUE</option>
              <option value="ERR_DUPLICATE_RECORD_ID">ERR_DUPLICATE_RECORD_ID</option>
              <option value="ERR_DUPLICATE_ORDER_ID">ERR_DUPLICATE_ORDER_ID</option>
              <option value="ERR_INVALID_FK">ERR_INVALID_FK</option>
              <option value="ERR_CALCULATION_MISMATCH">ERR_CALCULATION_MISMATCH</option>
            </select>
          </div>
        </div>
      </div>

      {/* Quarantine Records Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <LoadingState message="Fetching quarantine ledger records..." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs min-w-[850px]">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">Record ID</th>
                  <th className="py-3 px-4">Origin File</th>
                  <th className="py-3 px-4">Row #</th>
                  <th className="py-3 px-4">Error Classification</th>
                  <th className="py-3 px-4">Validation Stage</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-center">Attempts</th>
                  <th className="py-3 px-4">Quarantined At</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {records.length > 0 ? (
                  records.map((r) => (
                    <tr key={r.quarantine_id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-slate-800">{r.record_id}</td>
                      <td className="py-3 px-4 text-slate-600 truncate max-w-[150px]" title={r.source_file}>
                        {r.source_file}
                      </td>
                      <td className="py-3 px-4 text-slate-500 font-mono">{r.source_row_number}</td>
                      <td className="py-3 px-4">
                        <span className="inline-block px-2 py-0.5 rounded bg-rose-50 text-rose-700 font-mono text-[10px] border border-rose-200 mr-1.5">
                          {r.error_code}
                        </span>
                        <span className="text-slate-600 text-[11px] truncate max-w-[200px] inline-block align-middle" title={r.error_reason}>
                          {r.error_reason}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-semibold text-slate-600 uppercase text-[10px]">
                          {r.validation_stage}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="py-3 px-4 text-center font-medium text-slate-600">
                        {r.attempt_count}
                      </td>
                      <td className="py-3 px-4 text-slate-500">{formatDateTime(r.created_at)}</td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleInspect(r.quarantine_id)}
                          className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 border border-blue-200 rounded-md transition-colors"
                        >
                          <Edit3 className="w-3 h-3" />
                          Inspect & Correct
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="9" className="py-12 text-center text-slate-400">
                      No quarantined records found matching current criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        <div className="px-4 sm:px-6 py-3 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-2.5 text-xs text-slate-500">
          <span className="text-center sm:text-left">Showing {records.length} of {formatNumber(totalCount)} quarantined records</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1 rounded hover:bg-slate-100 disabled:opacity-40 transition-colors"
              aria-label="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-medium text-slate-700">Page {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={records.length < 50}
              className="p-1 rounded hover:bg-slate-100 disabled:opacity-40 transition-colors"
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Record Inspection & Correction Modal */}
      <CorrectionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        record={selectedRecord}
        onSaveCorrection={handleSaveCorrection}
        isSaving={isSavingCorrection}
      />
    </div>
  );
}
