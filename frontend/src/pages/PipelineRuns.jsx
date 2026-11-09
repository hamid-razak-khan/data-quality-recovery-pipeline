import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  History,
  Search,
  Filter,
  RefreshCw,
  Eye,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Activity,
  Layers,
} from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/common/StatusBadge';
import LoadingState from '../components/common/LoadingState';
import Modal from '../components/common/Modal';
import { formatNumber, formatDuration, formatDateTime, truncateId } from '../utils/formatters';

export default function PipelineRuns() {
  const { showToast } = useOutletContext();

  const [loading, setLoading] = useState(true);
  const [runs, setRuns] = useState([]);
  const [totalCount, setTotalCount] = useState(0);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Run detail modal state
  const [selectedRunDetail, setSelectedRunDetail] = useState(null);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchRuns = async () => {
    setLoading(true);
    try {
      const params = {
        search: searchTerm || undefined,
        status: statusFilter || undefined,
      };
      const res = await api.getPipelineRuns(params);
      setRuns(res.results || []);
      setTotalCount(res.count || 0);
    } catch (err) {
      showToast('Failed to load pipeline runs.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, [statusFilter]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchRuns();
  };

  const handleInspectRun = async (runId) => {
    setIsDetailLoading(true);
    setIsModalOpen(true);
    try {
      const data = await api.getPipelineRun(runId);
      setSelectedRunDetail(data);
    } catch (err) {
      showToast('Could not fetch run details.', 'error');
      setIsModalOpen(false);
    } finally {
      setIsDetailLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-slate-900">Pipeline Execution History</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Audit ledger of every batch ingestion run, processing duration, yield, and reconciliation balance.
          </p>
        </div>
        <button
          onClick={fetchRuns}
          className="self-start sm:self-auto flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Runs
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-3.5 sm:p-4 shadow-xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by source file name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </form>

        <div className="flex items-center gap-2 text-xs text-slate-600 w-full sm:w-auto">
          <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full sm:w-auto px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Run Statuses</option>
            <option value="COMPLETED">COMPLETED (100% Clean)</option>
            <option value="COMPLETED_WITH_ERRORS">COMPLETED WITH ERRORS</option>
            <option value="FAILED">FAILED</option>
            <option value="RUNNING">RUNNING</option>
          </select>
        </div>
      </div>

      {/* Runs Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <LoadingState message="Fetching pipeline execution runs..." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs min-w-[850px]">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">Run ID</th>
                  <th className="py-3 px-4">Source File</th>
                  <th className="py-3 px-4">Start Time</th>
                  <th className="py-3 px-4 text-right">Total Ingested</th>
                  <th className="py-3 px-4 text-right">Valid (Published)</th>
                  <th className="py-3 px-4 text-right">Quarantined</th>
                  <th className="py-3 px-4 text-right">Duration</th>
                  <th className="py-3 px-4 text-right">Yield</th>
                  <th className="py-3 px-4 text-center">Status</th>
                  <th className="py-3 px-4 text-right">Report</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {runs.length > 0 ? (
                  runs.map((r) => (
                    <tr key={r.run_id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-slate-700">{truncateId(r.run_id)}</td>
                      <td className="py-3 px-4 font-semibold text-slate-900">{r.filename}</td>
                      <td className="py-3 px-4 text-slate-500">{formatDateTime(r.start_time)}</td>
                      <td className="py-3 px-4 text-right font-medium text-slate-800">{formatNumber(r.total_records)}</td>
                      <td className="py-3 px-4 text-right text-emerald-600 font-semibold">{formatNumber(r.valid_records)}</td>
                      <td className="py-3 px-4 text-right text-rose-600 font-semibold">{formatNumber(r.rejected_records)}</td>
                      <td className="py-3 px-4 text-right text-slate-500">{formatDuration(r.execution_duration)}</td>
                      <td className="py-3 px-4 text-right font-medium text-slate-700">{r.success_rate}%</td>
                      <td className="py-3 px-4 text-center">
                        <StatusBadge status={r.run_status} />
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleInspectRun(r.run_id)}
                          className="p-1 rounded-md text-slate-400 hover:text-blue-600 hover:bg-slate-100 transition-colors"
                          title="View detailed reconciliation report"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="10" className="py-12 text-center text-slate-400">
                      No execution runs found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Run Detailed Execution Report Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Execution & Reconciliation Report"
        maxWidth="max-w-2xl"
      >
        {isDetailLoading ? (
          <LoadingState message="Calculating run reconciliation..." />
        ) : selectedRunDetail ? (
          <div className="space-y-4 text-xs">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <div>
                <span className="font-mono text-slate-400 text-[11px] block">Run ID: {selectedRunDetail.run.run_id}</span>
                <h4 className="text-sm font-bold text-slate-900">{selectedRunDetail.run.filename}</h4>
              </div>
              <StatusBadge status={selectedRunDetail.run.run_status} />
            </div>

            {/* Reconciliation Balance Table */}
            <div className="border border-slate-200 rounded-lg p-4 bg-slate-50 space-y-2">
              <h5 className="font-semibold text-slate-800 uppercase text-[10px] tracking-wider">
                Mathematical Reconciliation
              </h5>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-white p-2.5 rounded border border-slate-200">
                  <span className="text-slate-400 block">Total Source Rows:</span>
                  <span className="font-bold text-slate-900 text-sm">
                    {formatNumber(selectedRunDetail.reconciliation.total_input_records)}
                  </span>
                </div>
                <div className="bg-white p-2.5 rounded border border-slate-200">
                  <span className="text-slate-400 block">Yield / Throughput:</span>
                  <span className="font-bold text-blue-600 text-sm">
                    {formatNumber(selectedRunDetail.reconciliation.records_per_second)} rec/s
                  </span>
                </div>
                <div className="bg-white p-2.5 rounded border border-slate-200">
                  <span className="text-slate-400 block">Valid Published:</span>
                  <span className="font-bold text-emerald-600 text-sm">
                    {formatNumber(selectedRunDetail.reconciliation.valid_records)}
                  </span>
                </div>
                <div className="bg-white p-2.5 rounded border border-slate-200">
                  <span className="text-slate-400 block">Quarantined Records:</span>
                  <span className="font-bold text-rose-600 text-sm">
                    {formatNumber(selectedRunDetail.reconciliation.quarantined_records)}
                  </span>
                </div>
              </div>

              <div className="p-2 rounded bg-emerald-50 border border-emerald-200 text-emerald-800 flex items-center justify-between text-xs mt-2">
                <span>Total Input = Valid + Quarantined</span>
                <span className="font-bold">
                  {selectedRunDetail.reconciliation.formula_balance ? '✓ BALANCED (100%)' : '✗ DISCREPANCY'}
                </span>
              </div>
            </div>

            {/* Quarantine Error Breakdown */}
            {selectedRunDetail.quarantine_error_breakdown &&
              Object.keys(selectedRunDetail.quarantine_error_breakdown).length > 0 && (
                <div className="space-y-2">
                  <h5 className="font-semibold text-slate-800 uppercase text-[10px] tracking-wider">
                    Quarantine Errors in this Run
                  </h5>
                  <div className="border border-slate-200 rounded-lg divide-y divide-slate-100">
                    {Object.entries(selectedRunDetail.quarantine_error_breakdown).map(([code, count]) => (
                      <div key={code} className="px-3 py-2 flex items-center justify-between text-xs">
                        <span className="font-mono font-medium text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-100">
                          {code}
                        </span>
                        <span className="font-bold text-slate-800">{count} records</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {selectedRunDetail.run.failure_reason && (
              <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs">
                <span className="font-semibold block mb-0.5">Failure Reason:</span>
                <p className="font-mono text-[11px]">{selectedRunDetail.run.failure_reason}</p>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
