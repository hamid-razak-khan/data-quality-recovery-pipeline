import React, { useState, useEffect } from 'react';
import { useOutletContext, Link } from 'react-router-dom';
import {
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Loader2,
  RefreshCw,
  History,
  CheckSquare,
  Square,
  ArrowRight,
  Database,
} from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/common/StatusBadge';
import LoadingState from '../components/common/LoadingState';
import Modal from '../components/common/Modal';
import { formatNumber, formatDateTime, truncateId } from '../utils/formatters';

export default function Replay() {
  const { showToast } = useOutletContext();

  const [loading, setLoading] = useState(true);
  const [eligibleRecords, setEligibleRecords] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [replayHistory, setReplayHistory] = useState([]);

  // Confirm Modal state
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [replayAllMode, setReplayAllMode] = useState(false);
  const [isReplaying, setIsReplaying] = useState(false);
  const [lastReplayResult, setLastReplayResult] = useState(null);

  const fetchEligibleRecords = async () => {
    setLoading(true);
    try {
      // Eligible records are strictly those with status = 'CORRECTED'
      const res = await api.getQuarantineRecords({ status: 'CORRECTED' });
      setEligibleRecords(res.results || []);
      setSelectedIds(new Set());
    } catch (err) {
      showToast('Failed to load corrected records.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await api.getReplayHistory();
      setReplayHistory(res.results || []);
    } catch (err) {
      console.error('Failed to load replay history:', err);
    }
  };

  useEffect(() => {
    fetchEligibleRecords();
    fetchHistory();
  }, []);

  const handleSelectAll = () => {
    if (selectedIds.size === eligibleRecords.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(eligibleRecords.map((r) => r.quarantine_id)));
    }
  };

  const handleToggleSelect = (id) => {
    const updated = new Set(selectedIds);
    if (updated.has(id)) {
      updated.delete(id);
    } else {
      updated.add(id);
    }
    setSelectedIds(updated);
  };

  const openConfirmation = (allMode = false) => {
    setReplayAllMode(allMode);
    setIsConfirmOpen(true);
  };

  const executeReplay = async () => {
    setIsReplaying(true);
    setLastReplayResult(null);

    const payload = replayAllMode
      ? { replay_all: true }
      : { record_ids: Array.from(selectedIds) };

    try {
      const res = await api.triggerReplay(payload);
      setLastReplayResult(res);
      showToast(
        `Replay finished! ${res.successful_count} successfully published to processed_orders.`,
        res.failed_count > 0 ? 'info' : 'success',
        'Replay Executed'
      );
      setIsConfirmOpen(false);
      fetchEligibleRecords();
      fetchHistory();
    } catch (err) {
      showToast(err.response?.data?.error || 'Replay execution failed.', 'error');
    } finally {
      setIsReplaying(false);
    }
  };

  const selectedCount = replayAllMode ? eligibleRecords.length : selectedIds.size;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-slate-900">Controlled Replay Engine</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            The core recovery guarantee: Replays ONLY approved, operator-corrected records. Previously successful records are never reprocessed.
          </p>
        </div>
        <button
          onClick={() => {
            fetchEligibleRecords();
            fetchHistory();
          }}
          className="self-start sm:self-auto flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Replay State
        </button>
      </div>

      {/* Safety Notice Banner */}
      <div className="bg-indigo-50/70 border border-indigo-200 rounded-xl p-3.5 sm:p-4 flex items-start gap-3 text-xs text-indigo-900">
        <ShieldCheck className="w-5 h-5 text-indigo-600 shrink-0 mt-0.5" />
        <div>
          <h4 className="font-semibold text-indigo-950">Strict Business Guarantee Active</h4>
          <p className="mt-0.5 text-indigo-800 leading-relaxed">
            The replay engine queries exclusively records with status <span className="font-semibold font-mono bg-indigo-100 px-1 rounded">CORRECTED</span>.
            Target table upserts employ PostgreSQL primary key constraints. It is architecturally impossible to replay uncorrected records or duplicate previously successful records.
          </p>
        </div>
      </div>

      {/* Last Replay Result Summary */}
      {lastReplayResult && (
        <div className="bg-white rounded-xl border border-emerald-200 shadow-xs p-4 sm:p-5 bg-emerald-50/20">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <h3 className="text-sm font-bold text-emerald-900 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              Latest Replay Run Completed
            </h3>
            <span className="font-mono text-xs text-slate-500">Replay ID: {truncateId(lastReplayResult.replay_id)}</span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 p-3 bg-white rounded-lg border border-slate-200 text-xs">
            <div>
              <span className="text-slate-500 block text-[11px]">Submitted for Replay</span>
              <span className="text-base font-bold text-slate-900">{formatNumber(lastReplayResult.total_submitted)}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[11px]">Successfully Published</span>
              <span className="text-base font-bold text-emerald-600">{formatNumber(lastReplayResult.successful_count)}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[11px]">Failed Re-validation</span>
              <span className="text-base font-bold text-rose-600">{formatNumber(lastReplayResult.failed_count)}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[11px]">Remaining Quarantined</span>
              <span className="text-base font-bold text-slate-700">{formatNumber(lastReplayResult.remaining_quarantine_count)}</span>
            </div>
          </div>

          <div className="mt-3 flex items-center gap-3">
            <Link
              to="/processed"
              className="text-xs font-semibold text-blue-600 hover:underline flex items-center gap-1"
            >
              <Database className="w-3.5 h-3.5" /> View Updated Target Records →
            </Link>
          </div>
        </div>
      )}

      {/* Eligible Corrected Records Queue */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-4 sm:px-6 py-3.5 sm:py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Eligible Records Queue ({eligibleRecords.length})
            </h3>
            <p className="text-xs text-slate-500">
              Records corrected by operators awaiting controlled replay execution
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            {eligibleRecords.length > 0 && (
              <>
                <button
                  type="button"
                  onClick={() => openConfirmation(true)}
                  disabled={isReplaying}
                  className="flex-1 sm:flex-none px-3.5 py-1.5 text-xs font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 rounded-lg transition-colors shadow-xs text-center"
                >
                  Replay All ({eligibleRecords.length})
                </button>
                <button
                  type="button"
                  onClick={() => openConfirmation(false)}
                  disabled={selectedIds.size === 0 || isReplaying}
                  className="flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors disabled:opacity-50 text-center"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Replay Selected ({selectedIds.size})
                </button>
              </>
            )}
          </div>
        </div>

        {loading ? (
          <LoadingState message="Fetching eligible corrected records..." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs min-w-[780px]">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4 w-10 text-center">
                    <button
                      type="button"
                      onClick={handleSelectAll}
                      className="text-slate-400 hover:text-slate-600"
                    >
                      {selectedIds.size === eligibleRecords.length && eligibleRecords.length > 0 ? (
                        <CheckSquare className="w-4 h-4 text-blue-600" />
                      ) : (
                        <Square className="w-4 h-4" />
                      )}
                    </button>
                  </th>
                  <th className="py-3 px-4">Record ID</th>
                  <th className="py-3 px-4">Customer ID</th>
                  <th className="py-3 px-4">Product Name</th>
                  <th className="py-3 px-4 text-right">Quantity</th>
                  <th className="py-3 px-4 text-right">Total Amount</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4">Corrected At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                {eligibleRecords.length > 0 ? (
                  eligibleRecords.map((r) => {
                    const payload = r.corrected_record || r.raw_record || {};
                    const isSelected = selectedIds.has(r.quarantine_id);
                    return (
                      <tr
                        key={r.quarantine_id}
                        onClick={() => handleToggleSelect(r.quarantine_id)}
                        className={`cursor-pointer transition-colors ${
                          isSelected ? 'bg-blue-50/50' : 'hover:bg-slate-50/60'
                        }`}
                      >
                        <td className="py-3 px-4 text-center" onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            onClick={() => handleToggleSelect(r.quarantine_id)}
                            className="text-slate-400 hover:text-slate-600"
                          >
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-blue-600" />
                            ) : (
                              <Square className="w-4 h-4" />
                            )}
                          </button>
                        </td>
                        <td className="py-3 px-4 font-bold text-slate-800">{r.record_id}</td>
                        <td className="py-3 px-4 text-slate-600">{payload.customer_id || '—'}</td>
                        <td className="py-3 px-4 font-sans text-slate-700 truncate max-w-[200px]">
                          {payload.product_name || '—'}
                        </td>
                        <td className="py-3 px-4 text-right text-slate-700">{payload.quantity ?? '—'}</td>
                        <td className="py-3 px-4 text-right font-semibold text-slate-900">${payload.total_amount ?? '—'}</td>
                        <td className="py-3 px-4 text-center">
                          <StatusBadge status="CORRECTED" />
                        </td>
                        <td className="py-3 px-4 font-sans text-slate-500">{formatDateTime(r.updated_at)}</td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="8" className="py-12 text-center text-slate-400 font-sans">
                      No records currently awaiting replay. Inspect the{' '}
                      <Link to="/quarantine" className="text-blue-600 hover:underline">
                        Quarantine Store
                      </Link>{' '}
                      to correct invalid records.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Historical Replay Executions Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Replay Execution History</h3>
            <p className="text-xs text-slate-500">Audit log of all controlled recovery operations</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs min-w-[650px]">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                <th className="py-3 px-4 sm:px-6">Replay ID</th>
                <th className="py-3 px-4 sm:px-6">Execution Time</th>
                <th className="py-3 px-4 sm:px-6 text-right">Submitted</th>
                <th className="py-3 px-4 sm:px-6 text-right">Successful</th>
                <th className="py-3 px-4 sm:px-6 text-right">Failed</th>
                <th className="py-3 px-4 sm:px-6 text-right">Success Rate</th>
                <th className="py-3 px-4 sm:px-6 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {replayHistory.length > 0 ? (
                replayHistory.map((h) => (
                  <tr key={h.replay_id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="py-3 px-4 sm:px-6 font-mono text-slate-600">{truncateId(h.replay_id)}</td>
                    <td className="py-3 px-4 sm:px-6 text-slate-500">{formatDateTime(h.started_at)}</td>
                    <td className="py-3 px-4 sm:px-6 text-right font-medium text-slate-700">{formatNumber(h.total_submitted)}</td>
                    <td className="py-3 px-4 sm:px-6 text-right font-semibold text-emerald-600">{formatNumber(h.successful_count)}</td>
                    <td className="py-3 px-4 sm:px-6 text-right font-medium text-rose-600">{formatNumber(h.failed_count)}</td>
                    <td className="py-3 px-4 sm:px-6 text-right font-medium text-slate-700">{h.success_rate}%</td>
                    <td className="py-3 px-4 sm:px-6 text-center">
                      <StatusBadge status={h.status} />
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-slate-400">
                    No historical replays executed yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation Modal */}
      <Modal
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        title="Confirm Controlled Replay Execution"
        maxWidth="max-w-md"
      >
        <div className="space-y-4 text-xs text-slate-600">
          <p>
            You are about to replay{' '}
            <span className="font-bold text-slate-900 text-sm">
              {replayAllMode ? `${eligibleRecords.length} eligible` : `${selectedIds.size} selected`}
            </span>{' '}
            corrected records.
          </p>

          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-emerald-900 space-y-1">
            <h5 className="font-semibold text-emerald-950 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Guaranteed Invariants:
            </h5>
            <ul className="list-disc pl-4 space-y-0.5 text-emerald-800 text-[11px]">
              <li>Only corrected records will be re-validated.</li>
              <li>Previously successful records will NOT be reprocessed.</li>
              <li>Target updates use atomic PostgreSQL upserts.</li>
            </ul>
          </div>

          <div className="flex flex-col-reverse sm:flex-row justify-end gap-2 pt-3 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setIsConfirmOpen(false)}
              className="w-full sm:w-auto px-3.5 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors text-center"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={executeReplay}
              disabled={isReplaying}
              className="w-full sm:w-auto flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors shadow-xs disabled:opacity-50 text-center"
            >
              {isReplaying ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Executing Replay...
                </>
              ) : (
                <>
                  <RotateCcw className="w-3.5 h-3.5" />
                  Confirm & Replay
                </>
              )}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
