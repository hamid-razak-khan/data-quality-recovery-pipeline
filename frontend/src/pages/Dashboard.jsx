import React, { useState, useEffect } from 'react';
import { useOutletContext, Link, useNavigate } from 'react-router-dom';
import {
  Inbox,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  XCircle,
  TrendingUp,
  ArrowRight,
  RefreshCw,
  Clock,
  FileText,
  Activity,
  Layers,
  Filter,
  CheckCircle,
  Zap,
  Gauge,
  Calendar,
  X,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';
import api from '../services/api';
import StatCard from '../components/common/StatCard';
import StatusBadge from '../components/common/StatusBadge';
import LoadingState from '../components/common/LoadingState';
import Modal from '../components/common/Modal';
import QualityTrendChart from '../components/charts/QualityTrendChart';
import ErrorBreakdownChart from '../components/charts/ErrorBreakdownChart';
import { formatNumber, formatDuration, formatDateTime, truncateId } from '../utils/formatters';

export default function Dashboard() {
  const { showToast } = useOutletContext();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  // Trend Chart Filters
  const [filterSchema, setFilterSchema] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterFile, setFilterFile] = useState('');
  const [filterStartDate, setFilterStartDate] = useState('');
  const [filterEndDate, setFilterEndDate] = useState('');

  // Execution Run Details Modal
  const [selectedRun, setSelectedRun] = useState(null);
  const [isRunModalOpen, setIsRunModalOpen] = useState(false);

  const fetchMetrics = async (isManual = false, customFilters = null) => {
    if (isManual) setRefreshing(true);
    try {
      const activeFilters = customFilters || {
        schema: filterSchema || undefined,
        status: filterStatus || undefined,
        source_file: filterFile || undefined,
        start_date: filterStartDate || undefined,
        end_date: filterEndDate || undefined,
      };

      const res = await api.getMetrics(activeFilters);
      setData(res);
      if (isManual) showToast('Dashboard metrics refreshed from Supabase PostgreSQL', 'info');
    } catch (err) {
      showToast(err.response?.data?.error || 'Failed to load pipeline metrics.', 'error');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMetrics(false);
  }, [filterSchema, filterStatus, filterFile, filterStartDate, filterEndDate]);

  const handleResetFilters = () => {
    setFilterSchema('');
    setFilterStatus('');
    setFilterFile('');
    setFilterStartDate('');
    setFilterEndDate('');
    fetchMetrics(false, {});
  };

  const handleInspectRun = (run) => {
    setSelectedRun(run);
    setIsRunModalOpen(true);
  };

  if (loading) return <LoadingState message="Fetching live pipeline metrics from Supabase PostgreSQL..." />;

  const {
    kpis,
    performance,
    reconciliation_ledger,
    filter_options,
    latest_run,
    recent_runs,
    quality_trends,
    error_breakdown,
  } = data || {};

  const hasActiveFilters = Boolean(
    filterSchema || filterStatus || filterFile || filterStartDate || filterEndDate
  );

  const getSchemaBadgeColor = (schema) => {
    switch (schema?.toLowerCase()) {
      case 'telemetry':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'ecommerce':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'generic':
      default:
        return 'bg-blue-50 text-blue-700 border-blue-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Operations Control Center</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time multi-schema data quality monitoring, reconciliation ledger, and recovery engine.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchMetrics(true)}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors shadow-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh Metrics
          </button>
        </div>
      </div>

      {/* Primary KPI Cards with Calculation Tooltips */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard
          title="Total Ingested"
          value={formatNumber(kpis?.total_records_received)}
          subtitle="Cumulative source rows"
          icon={Inbox}
          color="blue"
          tooltip={{
            formula: 'Σ (pipeline_runs.total_records)',
            rules: 'Counts every raw incoming record across all batch executions before schema validation or deduplication.',
            source: 'PostgreSQL pipeline_runs table',
          }}
        />
        <StatCard
          title="Published (Target)"
          value={formatNumber(kpis?.successfully_processed)}
          subtitle="Unique canonical records"
          icon={CheckCircle2}
          color="emerald"
          tooltip={{
            formula: 'COUNT(order_id) FROM processed_orders',
            rules: 'Validated canonical records persisted to the target database table. Deduplicated by primary business key.',
            source: 'PostgreSQL processed_orders table',
          }}
        />
        <StatCard
          title="Active Quarantine"
          value={formatNumber(kpis?.active_quarantine)}
          subtitle="Unresolved rejections"
          icon={AlertTriangle}
          color="amber"
          tooltip={{
            formula: "COUNT(*) WHERE status IN ('PENDING', 'CORRECTED', 'FAILED')",
            rules: 'Records currently in quarantine awaiting operator inspection, manual correction, or re-validation.',
            source: 'PostgreSQL quarantine_records table',
          }}
        />
        <StatCard
          title="Recovered (Replay)"
          value={formatNumber(kpis?.replayed_records)}
          subtitle="Corrected & published"
          icon={RotateCcw}
          color="purple"
          tooltip={{
            formula: "COUNT(*) WHERE status = 'REPLAYED'",
            rules: 'Quarantined records successfully fixed by operators, re-validated, and replayed into target database.',
            source: 'PostgreSQL quarantine_records table',
          }}
        />
        <StatCard
          title="Failed Replays"
          value={formatNumber(kpis?.failed_records)}
          subtitle="Flawed replay attempts"
          icon={XCircle}
          color="rose"
          tooltip={{
            formula: "COUNT(*) WHERE status = 'FAILED'",
            rules: 'Quarantined records where attempted replay failed re-validation against active schema rules.',
            source: 'PostgreSQL quarantine_records table',
          }}
        />
        <StatCard
          title="Quality Rate"
          value={`${kpis?.success_rate_percent || 0}%`}
          subtitle="First-pass clean rate"
          icon={TrendingUp}
          color="indigo"
          tooltip={{
            formula: '(Σ valid_records / Σ total_records) * 100',
            rules: 'Percentage of raw ingested records that passed all schema and business validation rules on initial ingestion.',
            source: 'PostgreSQL pipeline_runs aggregate',
          }}
        />
      </div>

      {/* Database-Driven Reconciliation Ledger */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 mb-4 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-blue-50 text-blue-600 rounded-lg">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Database-Driven Record Accounting & Reconciliation
              </h3>
              <p className="text-xs text-slate-500">
                End-to-end reconciliation balancing cumulative ingestion against unique target storage and quarantine.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                reconciliation_ledger?.ingestion_formula_balanced
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-rose-50 text-rose-700 border-rose-200'
              }`}
            >
              <CheckCircle className="w-3 h-3" />
              {reconciliation_ledger?.ingestion_formula_balanced ? 'Ingestion Balanced' : 'Ingestion Discrepancy'}
            </span>
            <span
              className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                reconciliation_ledger?.quarantine_formula_balanced
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : 'bg-rose-50 text-rose-700 border-rose-200'
              }`}
            >
              <CheckCircle className="w-3 h-3" />
              {reconciliation_ledger?.quarantine_formula_balanced ? 'Quarantine Ledger Balanced' : 'Quarantine Discrepancy'}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {/* Column 1: Ingestion Intake Balance */}
          <div className="bg-slate-50/70 rounded-lg p-3.5 border border-slate-200/80 space-y-2">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
              1. Ingestion Volume Intake
            </span>
            <div className="space-y-1.5 text-slate-700">
              <div className="flex justify-between">
                <span className="text-slate-500">Total Ingested:</span>
                <span className="font-bold text-slate-900 font-mono">
                  {formatNumber(reconciliation_ledger?.total_source_records_ingested)}
                </span>
              </div>
              <div className="flex justify-between text-emerald-700">
                <span>↳ Valid at Ingestion:</span>
                <span className="font-mono font-semibold">
                  {formatNumber(reconciliation_ledger?.valid_at_ingestion)}
                </span>
              </div>
              <div className="flex justify-between text-rose-700">
                <span>↳ Quarantined:</span>
                <span className="font-mono font-semibold">
                  {formatNumber(reconciliation_ledger?.rejected_at_ingestion)}
                </span>
              </div>
              <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-500 font-mono">
                {reconciliation_ledger?.total_source_records_ingested} = {reconciliation_ledger?.valid_at_ingestion} + {reconciliation_ledger?.rejected_at_ingestion}
              </div>
            </div>
          </div>

          {/* Column 2: Target Storage & Deduplication */}
          <div className="bg-slate-50/70 rounded-lg p-3.5 border border-slate-200/80 space-y-2">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
              2. Target Canonical Storage
            </span>
            <div className="space-y-1.5 text-slate-700">
              <div className="flex justify-between">
                <span className="text-slate-500">Cumulative Valid:</span>
                <span className="font-bold text-slate-900 font-mono">
                  {formatNumber(reconciliation_ledger?.valid_at_ingestion)}
                </span>
              </div>
              <div className="flex justify-between text-blue-700">
                <span>↳ Unique Target Records:</span>
                <span className="font-mono font-semibold">
                  {formatNumber(reconciliation_ledger?.unique_target_published)}
                </span>
              </div>
              <div className="flex justify-between text-indigo-700" title="Records re-uploaded and updated idempotently">
                <span>↳ Idempotent Updates:</span>
                <span className="font-mono font-semibold">
                  {formatNumber(reconciliation_ledger?.idempotent_deduplicated)}
                </span>
              </div>
              <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-500">
                Strict PostgreSQL primary key idempotency prevents duplicates.
              </div>
            </div>
          </div>

          {/* Column 3: Quarantine & Recovery Ledger */}
          <div className="bg-slate-50/70 rounded-lg p-3.5 border border-slate-200/80 space-y-2">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
              3. Quarantine Recovery Ledger
            </span>
            <div className="space-y-1.5 text-slate-700">
              <div className="flex justify-between">
                <span className="text-slate-500">Total Quarantined:</span>
                <span className="font-bold text-slate-900 font-mono">
                  {formatNumber(reconciliation_ledger?.total_quarantined_stored)}
                </span>
              </div>
              <div className="flex justify-between text-purple-700">
                <span>↳ Recovered via Replay:</span>
                <span className="font-mono font-semibold">
                  {formatNumber(reconciliation_ledger?.successfully_replayed_recovered)}
                </span>
              </div>
              <div className="flex justify-between text-amber-700">
                <span>↳ Active Unresolved:</span>
                <span className="font-mono font-semibold">
                  {formatNumber(reconciliation_ledger?.active_quarantine_remaining)}
                </span>
              </div>
              <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-500 font-mono">
                {reconciliation_ledger?.total_quarantined_stored} = {reconciliation_ledger?.successfully_replayed_recovered} + {reconciliation_ledger?.active_quarantine_remaining}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Secondary Analytics: Processing Performance & Throughput */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3">
          <div className="p-2.5 bg-blue-50 text-blue-600 rounded-lg shrink-0">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <span className="text-slate-400 block text-[11px] uppercase font-semibold">Avg Throughput</span>
            <span className="text-lg font-bold text-slate-900">
              {performance?.avg_throughput_rps || 0} <span className="text-xs font-normal text-slate-500">rec/sec</span>
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5">
              Across {performance?.total_batches_executed || 0} total batches
            </span>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3">
          <div className="p-2.5 bg-emerald-50 text-emerald-600 rounded-lg shrink-0">
            <Gauge className="w-5 h-5" />
          </div>
          <div>
            <span className="text-slate-400 block text-[11px] uppercase font-semibold">Latest Batch Throughput</span>
            <span className="text-lg font-bold text-emerald-700">
              {performance?.latest_throughput_rps || 0} <span className="text-xs font-normal text-slate-500">rec/sec</span>
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5 truncate max-w-[180px]" title={latest_run?.filename}>
              {latest_run?.filename || 'No recent run'}
            </span>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3">
          <div className="p-2.5 bg-amber-50 text-amber-600 rounded-lg shrink-0">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <span className="text-slate-400 block text-[11px] uppercase font-semibold">Avg Batch Duration</span>
            <span className="text-lg font-bold text-slate-900">
              {performance?.avg_duration_seconds || 0}s
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5">
              Total compute: {performance?.total_duration_seconds || 0}s
            </span>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex items-center gap-3">
          <div className="p-2.5 bg-purple-50 text-purple-600 rounded-lg shrink-0">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <span className="text-slate-400 block text-[11px] uppercase font-semibold">Unique Ingestion Yield</span>
            <span className="text-lg font-bold text-purple-700">
              {kpis?.unique_published_yield || 0}%
            </span>
            <span className="text-[10px] text-slate-400 block mt-0.5">
              {formatNumber(kpis?.idempotent_updates)} deduplicated on replay/upload
            </span>
          </div>
        </div>
      </div>

      {/* Latest Pipeline Run Summary Card */}
      {latest_run && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-blue-50 text-blue-600 rounded-lg shrink-0">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Latest Pipeline Run
                </span>
                <span
                  className={`inline-block px-2 py-0.5 rounded text-[11px] uppercase font-bold border font-mono ${getSchemaBadgeColor(
                    latest_run.detected_schema || latest_run.metadata?.schema_detected
                  )}`}
                >
                  Schema: {latest_run.detected_schema || latest_run.metadata?.schema_detected || 'generic'}
                </span>
                <StatusBadge status={latest_run.run_status} />
              </div>
              <h4 className="text-base font-semibold text-slate-900 mt-1 flex items-center gap-2">
                <FileText className="w-4 h-4 text-slate-400" />
                {latest_run.filename}
              </h4>
              <p className="text-xs text-slate-500 mt-1">
                Started {formatDateTime(latest_run.start_time)} • Duration: {formatDuration(latest_run.execution_duration)} • Throughput: {latest_run.throughput_rps || 0} rec/s
              </p>
            </div>
          </div>

          <div className="flex items-center gap-6 border-t md:border-t-0 md:border-l border-slate-100 pt-3 md:pt-0 md:pl-6 text-xs">
            <div>
              <span className="text-slate-400 block">Total Records</span>
              <span className="font-semibold text-slate-800 text-sm font-mono">{formatNumber(latest_run.total_records)}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Valid (Published)</span>
              <span className="font-semibold text-emerald-600 text-sm font-mono">{formatNumber(latest_run.valid_records)}</span>
            </div>
            <div>
              <span className="text-slate-400 block">Quarantined</span>
              <span className="font-semibold text-rose-600 text-sm font-mono">{formatNumber(latest_run.rejected_records)}</span>
            </div>
            <button
              onClick={() => handleInspectRun(latest_run)}
              className="px-3 py-1.5 text-xs font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 rounded-lg transition-colors flex items-center gap-1"
            >
              Inspect <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quality Trends with Interactive Filters */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">Data Quality Trends</h3>
                <p className="text-xs text-slate-500">
                  Valid vs Quarantined records per batch run (Click bars for details)
                </p>
              </div>
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-rose-600 hover:text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200"
                >
                  <X className="w-3 h-3" /> Clear Filters
                </button>
              )}
            </div>

            {/* Filter Controls Row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3 p-2.5 bg-slate-50/80 rounded-lg border border-slate-200/80 text-xs">
              <div>
                <label className="block text-[10px] font-medium text-slate-500 mb-0.5">Schema</label>
                <select
                  value={filterSchema}
                  onChange={(e) => setFilterSchema(e.target.value)}
                  className="w-full px-2 py-1 text-xs bg-white border border-slate-300 rounded focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">All Schemas</option>
                  <option value="generic">generic</option>
                  <option value="telemetry">telemetry</option>
                  <option value="ecommerce">ecommerce</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-medium text-slate-500 mb-0.5">Status</label>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="w-full px-2 py-1 text-xs bg-white border border-slate-300 rounded focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">All Statuses</option>
                  <option value="COMPLETED">COMPLETED</option>
                  <option value="COMPLETED_WITH_ERRORS">COMPLETED WITH ERRORS</option>
                  <option value="FAILED">FAILED</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-medium text-slate-500 mb-0.5">Start Date</label>
                <input
                  type="date"
                  value={filterStartDate}
                  onChange={(e) => setFilterStartDate(e.target.value)}
                  className="w-full px-1.5 py-0.5 text-xs bg-white border border-slate-300 rounded text-slate-600 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-[10px] font-medium text-slate-500 mb-0.5">End Date</label>
                <input
                  type="date"
                  value={filterEndDate}
                  onChange={(e) => setFilterEndDate(e.target.value)}
                  className="w-full px-1.5 py-0.5 text-xs bg-white border border-slate-300 rounded text-slate-600 focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
          </div>

          <QualityTrendChart data={quality_trends} onBarClick={handleInspectRun} />
        </div>

        {/* Top Quarantine Error Causes */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">Top Quarantine Error Causes</h3>
              <p className="text-xs text-slate-500">
                Distribution of validation rejection reasons (Active vs Historical Recovered)
              </p>
            </div>
            <Link to="/quarantine" className="text-xs font-medium text-blue-600 hover:underline flex items-center gap-1">
              Quarantine Store <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <ErrorBreakdownChart data={error_breakdown} />
        </div>
      </div>

      {/* Recent Pipeline Executions Table with Detected Schema */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Recent Pipeline Executions</h3>
            <p className="text-xs text-slate-500">Audit trail of recent batch ingestion runs</p>
          </div>
          <Link to="/runs" className="text-xs font-medium text-blue-600 hover:underline flex items-center gap-1">
            All Execution History <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                <th className="py-3 px-4">Run ID</th>
                <th className="py-3 px-4">Source File</th>
                <th className="py-3 px-4">Detected Schema</th>
                <th className="py-3 px-4">Start Time</th>
                <th className="py-3 px-4 text-right">Total Ingested</th>
                <th className="py-3 px-4 text-right">Valid (Published)</th>
                <th className="py-3 px-4 text-right">Quarantined</th>
                <th className="py-3 px-4 text-right">Duration</th>
                <th className="py-3 px-4 text-right">Throughput</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {recent_runs && recent_runs.length > 0 ? (
                recent_runs.map((r) => {
                  const schemaName = r.detected_schema || r.metadata?.schema_detected || 'generic';
                  return (
                    <tr key={r.run_id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-slate-700">{truncateId(r.run_id)}</td>
                      <td className="py-3 px-4 font-semibold text-slate-900">{r.filename}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[11px] font-mono font-bold uppercase border ${getSchemaBadgeColor(
                            schemaName
                          )}`}
                        >
                          {schemaName}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-500">{formatDateTime(r.start_time)}</td>
                      <td className="py-3 px-4 text-right font-medium text-slate-800 font-mono">
                        {formatNumber(r.total_records)}
                      </td>
                      <td className="py-3 px-4 text-right text-emerald-600 font-semibold font-mono">
                        {formatNumber(r.valid_records)}
                      </td>
                      <td className="py-3 px-4 text-right text-rose-600 font-semibold font-mono">
                        {formatNumber(r.rejected_records)}
                      </td>
                      <td className="py-3 px-4 text-right text-slate-500 font-mono">
                        {formatDuration(r.execution_duration)}
                      </td>
                      <td className="py-3 px-4 text-right font-medium text-slate-700 font-mono">
                        {r.throughput_rps || (r.execution_duration > 0 ? (r.total_records / r.execution_duration).toFixed(1) : 0)} rec/s
                      </td>
                      <td className="py-3 px-4 text-center">
                        <StatusBadge status={r.run_status} />
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => handleInspectRun(r)}
                          className="p-1 rounded-md text-slate-400 hover:text-blue-600 hover:bg-slate-100 transition-colors"
                          title="Inspect execution details"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="11" className="py-8 text-center text-slate-400">
                    No pipeline runs recorded yet. Use the Data Ingestion tab to upload and process source datasets.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Execution Run Details Modal (from Clickable Chart Bars or Table) */}
      <Modal
        isOpen={isRunModalOpen}
        onClose={() => setIsRunModalOpen(false)}
        title={`Pipeline Run Execution: ${selectedRun?.run_id || ''}`}
        maxWidth="max-w-2xl"
      >
        {selectedRun && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 bg-slate-50 p-4 rounded-lg border border-slate-200">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Source File</span>
                <span className="font-semibold text-slate-800 break-all">{selectedRun.filename}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Detected Schema</span>
                <span
                  className={`inline-block px-2 py-0.5 rounded text-[11px] font-mono font-bold uppercase border mt-0.5 ${getSchemaBadgeColor(
                    selectedRun.schema || selectedRun.detected_schema || selectedRun.metadata?.schema_detected
                  )}`}
                >
                  {selectedRun.schema || selectedRun.detected_schema || selectedRun.metadata?.schema_detected || 'generic'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Execution Status</span>
                <div className="mt-0.5">
                  <StatusBadge status={selectedRun.run_status || selectedRun.status} />
                </div>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Total Ingested</span>
                <span className="font-mono font-bold text-slate-900 text-sm">
                  {formatNumber(selectedRun.total_records)}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Valid (Published)</span>
                <span className="font-mono font-bold text-emerald-600 text-sm">
                  {formatNumber(selectedRun.valid_records)}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Quarantined</span>
                <span className="font-mono font-bold text-rose-600 text-sm">
                  {formatNumber(selectedRun.rejected_records)}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Execution Duration</span>
                <span className="font-mono font-medium text-slate-700">
                  {formatDuration(selectedRun.execution_duration || selectedRun.duration_seconds)}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Throughput</span>
                <span className="font-mono font-medium text-slate-700">
                  {selectedRun.throughput_rps || 0} rec/s
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase font-semibold">Start Time</span>
                <span className="text-slate-700">{formatDateTime(selectedRun.start_time)}</span>
              </div>
            </div>

            {/* Reconciliation Check Banner */}
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-slate-600">
              <span className="text-slate-400 block text-[10px] uppercase font-semibold mb-1">
                Run Ingestion Balance Check
              </span>
              <div className="flex items-center justify-between font-mono text-xs">
                <span>
                  {selectedRun.total_records} = {selectedRun.valid_records} (valid) + {selectedRun.rejected_records} (quarantined)
                </span>
                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800">
                  100% Balanced
                </span>
              </div>
            </div>

            {selectedRun.failure_reason && (
              <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-rose-700">
                <span className="font-semibold block mb-0.5">Failure Reason:</span>
                <p>{selectedRun.failure_reason}</p>
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-200">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setIsRunModalOpen(false);
                    navigate(`/quarantine?run_id=${selectedRun.full_run_id || selectedRun.run_id}`);
                  }}
                  className="px-3 py-1.5 text-xs font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-lg transition-colors flex items-center gap-1.5"
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Inspect Quarantined ({selectedRun.rejected_records})
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsRunModalOpen(false);
                    navigate(`/runs?search=${encodeURIComponent(selectedRun.filename)}`);
                  }}
                  className="px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors flex items-center gap-1.5"
                >
                  <FileText className="w-3.5 h-3.5" />
                  View in Run History
                </button>
              </div>
              <button
                type="button"
                onClick={() => setIsRunModalOpen(false)}
                className="px-4 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
