import React, { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  Search,
  Filter,
  Download,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Eye,
} from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/common/StatusBadge';
import LoadingState from '../components/common/LoadingState';
import Modal from '../components/common/Modal';
import { formatNumber, formatCurrency, formatDateTime, formatDate, truncateId } from '../utils/formatters';

export default function ProcessedRecords() {
  const { showToast } = useOutletContext();

  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Selected Order for inspection
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const params = {
        page,
        search: searchTerm || undefined,
        status: statusFilter || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      };
      const res = await api.getProcessedOrders(params);
      setOrders(res.results || []);
      setTotalCount(res.count || 0);
    } catch (err) {
      showToast('Failed to load processed records.', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [page, statusFilter, startDate, endDate]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchOrders();
  };

  const handleExportCsv = () => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
    const params = new URLSearchParams();
    if (searchTerm) params.append('search', searchTerm);
    if (statusFilter) params.append('status', statusFilter);
    params.append('export', 'csv');
    window.open(`${baseUrl}/processed/?${params.toString()}`, '_blank');
    showToast('Exporting processed records to CSV...', 'info');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div>
          <h2 className="text-lg sm:text-xl font-bold text-slate-900">Processed Target Records</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Published, transformed, schema-compliant records stored in Supabase PostgreSQL target table.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          <button
            onClick={handleExportCsv}
            className="flex-1 sm:flex-none justify-center flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-xs transition-colors"
          >
            <Download className="w-3.5 h-3.5" /> <span className="hidden xs:inline">Export to </span>CSV
          </button>
          <button
            onClick={fetchOrders}
            className="flex-1 sm:flex-none justify-center flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-3.5 sm:p-4 shadow-xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by record ID, entity, or event type..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </form>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 w-full md:w-auto">
          {/* Status Filter */}
          <div className="flex items-center gap-1.5 text-xs text-slate-600 w-full sm:w-auto">
            <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full sm:w-auto px-2.5 py-1.5 text-xs bg-slate-50 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="COMPLETED">COMPLETED</option>
              <option value="CANCELLED">CANCELLED</option>
              <option value="GOOD">GOOD</option>
              <option value="REVIEW">REVIEW</option>
              <option value="PENDING">PENDING</option>
              <option value="CONFIRMED">CONFIRMED</option>
              <option value="SHIPPED">SHIPPED</option>
              <option value="DELIVERED">DELIVERED</option>
            </select>
          </div>

          {/* Date Filter */}
          <div className="flex items-center gap-1.5 text-xs w-full sm:w-auto">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="flex-1 sm:flex-none px-2 py-1 text-xs border border-slate-300 rounded-md text-slate-600"
              title="Start Date"
            />
            <span className="text-slate-400">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="flex-1 sm:flex-none px-2 py-1 text-xs border border-slate-300 rounded-md text-slate-600"
              title="End Date"
            />
          </div>
        </div>
      </div>

      {/* Generic Records Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {loading ? (
          <LoadingState message="Fetching target processed records from PostgreSQL..." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs min-w-[850px]">
              <thead>
                <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">Record / Reading ID</th>
                  <th className="py-3 px-4">Entity / Asset</th>
                  <th className="py-3 px-4">Event / Metric</th>
                  <th className="py-3 px-4 text-right">Quantity</th>
                  <th className="py-3 px-4 text-right">Amount / Value</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4 text-center">Status / Flag</th>
                  <th className="py-3 px-4 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {orders.length > 0 ? (
                  orders.map((o) => {
                    const recordId = o.reading_id || o.record_id || o.order_id;
                    const entityId = o.asset_code || o.entity_id || o.customer_id;
                    const eventType = o.metric_name || o.event_type || o.product_name || 'EVENT';
                    const isTelemetry = Boolean(o.reading_id || o.asset_code || o.metric_name);
                    const formattedValue = isTelemetry && o.metric_value !== null && o.metric_value !== undefined
                      ? `${o.metric_value} ${o.unit || ''}`
                      : formatCurrency(o.amount !== null && o.amount !== undefined ? o.amount : o.total_amount);
                    const timestampVal = o.observed_at || o.event_timestamp || o.order_date;
                    const statusVal = o.quality_flag || o.status || o.order_status;

                    return (
                      <tr key={recordId} className="hover:bg-slate-50/60 transition-colors">
                        <td className="py-3 px-4 font-mono font-bold text-slate-900">{recordId}</td>
                        <td className="py-3 px-4">
                          <span className="font-mono text-slate-700 block text-[11px]">{entityId}</span>
                        </td>
                        <td className="py-3 px-4 text-slate-800 font-medium truncate max-w-[200px]" title={eventType}>
                          <span className="inline-block px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-mono text-[11px] border border-blue-200 font-semibold">
                            {eventType}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right font-medium text-slate-700">{o.quantity}</td>
                        <td className="py-3 px-4 text-right font-bold text-slate-900">{formattedValue}</td>
                        <td className="py-3 px-4 text-slate-500">{formatDateTime(timestampVal)}</td>
                        <td className="py-3 px-4 text-center">
                          <StatusBadge status={statusVal} />
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => {
                              setSelectedOrder(o);
                              setIsDetailOpen(true);
                            }}
                            className="p-1 rounded-md text-slate-400 hover:text-blue-600 hover:bg-slate-100 transition-colors"
                            title="View complete record details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan="8" className="py-12 text-center text-slate-400">
                      No processed records found matching current criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        <div className="px-4 sm:px-6 py-3 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-2.5 text-xs text-slate-500">
          <span className="text-center sm:text-left">Showing {orders.length} of {formatNumber(totalCount)} target records</span>
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
              disabled={orders.length < 50}
              className="p-1 rounded hover:bg-slate-100 disabled:opacity-40 transition-colors"
              aria-label="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Record Details Modal */}
      <Modal
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        title={`Target Record Detail: ${selectedOrder?.record_id || selectedOrder?.order_id || ''}`}
        maxWidth="max-w-xl"
      >
        {selectedOrder && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-4 bg-slate-50 p-4 rounded-lg border border-slate-200">
              <div>
                <span className="text-slate-400 block">{selectedOrder.reading_id ? 'Reading ID' : 'Record ID'}</span>
                <span className="font-mono font-bold text-slate-800">{selectedOrder.reading_id || selectedOrder.record_id || selectedOrder.order_id}</span>
              </div>
              <div>
                <span className="text-slate-400 block">{selectedOrder.quality_flag ? 'Quality Flag' : 'Status'}</span>
                <StatusBadge status={selectedOrder.quality_flag || selectedOrder.status || selectedOrder.order_status} />
              </div>
              <div>
                <span className="text-slate-400 block">{selectedOrder.asset_code ? 'Asset Code' : 'Entity ID'}</span>
                <span className="font-mono font-semibold text-slate-800">{selectedOrder.asset_code || selectedOrder.entity_id || selectedOrder.customer_id}</span>
              </div>
              <div>
                <span className="text-slate-400 block">{selectedOrder.metric_name ? 'Metric Name' : 'Event Type'}</span>
                <span className="font-mono font-semibold text-blue-700">{selectedOrder.metric_name || selectedOrder.event_type || selectedOrder.product_name}</span>
              </div>
              <div>
                <span className="text-slate-400 block">{selectedOrder.unit ? 'Unit' : 'Quantity'}</span>
                <span className="font-bold text-slate-800">{selectedOrder.unit || selectedOrder.quantity}</span>
              </div>
              <div>
                <span className="text-slate-400 block">{selectedOrder.metric_value !== null && selectedOrder.metric_value !== undefined ? 'Metric Value' : 'Amount'}</span>
                <span className="text-base font-bold text-emerald-600">
                  {selectedOrder.metric_value !== null && selectedOrder.metric_value !== undefined
                    ? `${selectedOrder.metric_value} ${selectedOrder.unit || ''}`
                    : formatCurrency(selectedOrder.amount !== null && selectedOrder.amount !== undefined ? selectedOrder.amount : selectedOrder.total_amount)}
                </span>
              </div>
            </div>

            <div className="border border-slate-200 rounded-lg p-3 space-y-1.5 text-slate-600">
              <h5 className="font-semibold text-slate-800 uppercase text-[10px] tracking-wider mb-2">
                Traceability Metadata
              </h5>
              <div className="flex justify-between">
                <span className="text-slate-400">Source File:</span>
                <span className="font-medium">{selectedOrder.source_file}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Source Row Number:</span>
                <span className="font-mono">{selectedOrder.source_row_number}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Pipeline Run ID:</span>
                <span className="font-mono">{selectedOrder.run_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Event Timestamp:</span>
                <span>{formatDateTime(selectedOrder.event_timestamp || selectedOrder.order_date)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Published Timestamp:</span>
                <span>{formatDateTime(selectedOrder.processed_at)}</span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setIsDetailOpen(false)}
                className="px-4 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
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
