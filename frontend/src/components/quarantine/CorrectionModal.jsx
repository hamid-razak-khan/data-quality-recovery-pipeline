import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  History,
  Code,
  CheckCircle,
  Save,
  Calculator,
  Loader2,
  Info,
} from 'lucide-react';
import Modal from '../common/Modal';
import StatusBadge from '../common/StatusBadge';
import { formatDateTime } from '../../utils/formatters';

export default function CorrectionModal({
  isOpen,
  onClose,
  record,
  onSaveCorrection,
  isSaving,
}) {
  const [activeTab, setActiveTab] = useState('editor'); // 'editor', 'raw', 'history'
  const [formData, setFormData] = useState({});
  const [notes, setNotes] = useState('');
  const [schemaType, setSchemaType] = useState('generic'); // 'telemetry', 'generic', 'ecommerce'

  useEffect(() => {
    if (record) {
      const initialPayload = record.corrected_record || record.raw_record || {};
      const isTelem = ('reading_id' in initialPayload || 'asset_code' in initialPayload || 'metric_name' in initialPayload);
      const isGen = !isTelem && ('record_id' in initialPayload || 'entity_id' in initialPayload || !('order_id' in initialPayload));

      if (isTelem) {
        setSchemaType('telemetry');
        setFormData({
          reading_id: initialPayload.reading_id || record.record_id || '',
          asset_code: initialPayload.asset_code || '',
          metric_name: initialPayload.metric_name || 'temperature',
          metric_value: initialPayload.metric_value ?? '25.00',
          unit: initialPayload.unit || 'C',
          observed_at: initialPayload.observed_at || new Date().toISOString(),
          quality_flag: initialPayload.quality_flag || 'GOOD',
        });
      } else if (isGen) {
        setSchemaType('generic');
        setFormData({
          record_id: initialPayload.record_id || record.record_id || '',
          entity_id: initialPayload.entity_id || '',
          event_type: initialPayload.event_type || 'CREATED',
          amount: initialPayload.amount ?? '0.00',
          quantity: initialPayload.quantity ?? 1,
          event_timestamp: initialPayload.event_timestamp || new Date().toISOString(),
          status: initialPayload.status || 'ACTIVE',
        });
      } else {
        setSchemaType('ecommerce');
        setFormData({
          order_id: initialPayload.order_id || record.record_id || '',
          customer_id: initialPayload.customer_id || '',
          product_name: initialPayload.product_name || '',
          quantity: initialPayload.quantity ?? 1,
          unit_price: initialPayload.unit_price ?? '0.00',
          total_amount: initialPayload.total_amount ?? '0.00',
          order_date: initialPayload.order_date || new Date().toISOString(),
          order_status: initialPayload.order_status || 'CONFIRMED',
        });
      }
      setNotes('');
      setActiveTab('editor');
    }
  }, [record]);

  if (!record) return null;

  const handleFieldChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleRecalculateTotal = () => {
    const qty = parseInt(formData.quantity) || 0;
    const price = parseFloat(formData.unit_price) || 0;
    const calc = (qty * price).toFixed(2);
    setFormData((prev) => ({ ...prev, total_amount: calc }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSaveCorrection(record.quarantine_id, formData, notes);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Quarantine Inspection: ${record.record_id}`}
      maxWidth="max-w-3xl"
    >
      {/* Record Metadata Banner */}
      <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 mb-4 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div>
          <span className="text-slate-400">Source:</span>{' '}
          <span className="font-semibold text-slate-700">{record.source_file}</span> (Row {record.source_row_number})
        </div>
        <div>
          <span className="text-slate-400">Replay Attempts:</span>{' '}
          <span className="font-semibold text-slate-700">{record.attempt_count}</span>
        </div>
        <StatusBadge status={record.status} />
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 mb-4 text-xs font-medium overflow-x-auto whitespace-nowrap">
        <button
          onClick={() => setActiveTab('editor')}
          className={`py-2 px-3 sm:px-4 border-b-2 transition-colors shrink-0 ${
            activeTab === 'editor'
              ? 'border-blue-600 text-blue-600 font-semibold'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Correction Editor
        </button>
        <button
          onClick={() => setActiveTab('raw')}
          className={`py-2 px-3 sm:px-4 border-b-2 transition-colors shrink-0 ${
            activeTab === 'raw'
              ? 'border-blue-600 text-blue-600 font-semibold'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Verbatim Raw Record
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`py-2 px-3 sm:px-4 border-b-2 transition-colors shrink-0 ${
            activeTab === 'history'
              ? 'border-blue-600 text-blue-600 font-semibold'
              : 'border-transparent text-slate-500 hover:text-slate-700'
          }`}
        >
          Correction Audit History ({record.corrections?.length || 0})
        </button>
      </div>

      {/* Tab 1: Correction Editor */}
      {activeTab === 'editor' && (
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Validation Errors Box */}
          <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-xs">
            <h4 className="font-semibold text-rose-800 flex items-center gap-1.5 mb-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              Active Validation Errors ({record.validation_errors?.length || 1})
            </h4>
            <div className="space-y-1 text-rose-700">
              {record.validation_errors && record.validation_errors.length > 0 ? (
                record.validation_errors.map((err, i) => (
                  <div key={i} className="flex items-start gap-1">
                    <span className="font-mono font-semibold bg-rose-100 px-1 rounded text-[10px]">
                      {err.error_code}
                    </span>
                    <span>{err.error_reason}</span>
                  </div>
                ))
              ) : (
                <div className="flex items-start gap-1">
                  <span className="font-mono font-semibold bg-rose-100 px-1 rounded text-[10px]">
                    {record.error_code}
                  </span>
                  <span>{record.error_reason}</span>
                </div>
              )}
            </div>
          </div>

          {/* Dynamic Form based on schema type */}
          {schemaType === 'telemetry' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Reading ID</label>
                <input
                  type="text"
                  value={formData.reading_id || ''}
                  onChange={(e) => handleFieldChange('reading_id', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Asset Code</label>
                <input
                  type="text"
                  value={formData.asset_code || ''}
                  onChange={(e) => handleFieldChange('asset_code', e.target.value)}
                  placeholder="e.g. ASSET-101"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Metric Name</label>
                <select
                  value={formData.metric_name || 'temperature'}
                  onChange={(e) => {
                    const metric = e.target.value;
                    const defaultUnits = {
                      temperature: 'C',
                      humidity: '%',
                      pressure: 'kPa',
                      vibration: 'mm/s',
                    };
                    handleFieldChange('metric_name', metric);
                    if (defaultUnits[metric]) {
                      handleFieldChange('unit', defaultUnits[metric]);
                    }
                  }}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500"
                >
                  <option value="temperature">temperature</option>
                  <option value="humidity">humidity</option>
                  <option value="pressure">pressure</option>
                  <option value="vibration">vibration</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Unit</label>
                <input
                  type="text"
                  value={formData.unit || ''}
                  onChange={(e) => handleFieldChange('unit', e.target.value)}
                  placeholder="C, %, kPa, mm/s"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Metric Value</label>
                <input
                  type="number"
                  step="any"
                  value={formData.metric_value ?? ''}
                  onChange={(e) => handleFieldChange('metric_value', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Quality Flag</label>
                <select
                  value={formData.quality_flag || 'GOOD'}
                  onChange={(e) => handleFieldChange('quality_flag', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500"
                >
                  <option value="GOOD">GOOD</option>
                  <option value="REVIEW">REVIEW</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">Observed At (ISO-8601 Timestamp)</label>
                <input
                  type="text"
                  value={formData.observed_at || ''}
                  onChange={(e) => handleFieldChange('observed_at', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">Correction Notes / Reason</label>
                <input
                  type="text"
                  placeholder="e.g. Corrected invalid metric value and aligned unit"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          ) : schemaType === 'generic' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Record ID</label>
                <input
                  type="text"
                  value={formData.record_id || ''}
                  onChange={(e) => handleFieldChange('record_id', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Entity ID</label>
                <input
                  type="text"
                  value={formData.entity_id || ''}
                  onChange={(e) => handleFieldChange('entity_id', e.target.value)}
                  placeholder="e.g. ENT-701"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Event Type</label>
                <select
                  value={formData.event_type || 'CREATED'}
                  onChange={(e) => handleFieldChange('event_type', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500"
                >
                  <option value="CREATED">CREATED</option>
                  <option value="UPDATED">UPDATED</option>
                  <option value="COMPLETED">COMPLETED</option>
                  <option value="CANCELLED">CANCELLED</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Status</label>
                <select
                  value={formData.status || 'ACTIVE'}
                  onChange={(e) => handleFieldChange('status', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="COMPLETED">COMPLETED</option>
                  <option value="CANCELLED">CANCELLED</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Amount ($)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.00"
                  value={formData.amount ?? ''}
                  onChange={(e) => handleFieldChange('amount', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Quantity (Positive integer)</label>
                <input
                  type="number"
                  min="1"
                  value={formData.quantity ?? ''}
                  onChange={(e) => handleFieldChange('quantity', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">Event Timestamp (ISO-8601)</label>
                <input
                  type="text"
                  value={formData.event_timestamp || ''}
                  onChange={(e) => handleFieldChange('event_timestamp', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">Correction Notes / Reason</label>
                <input
                  type="text"
                  placeholder="e.g. Corrected invalid amount formatting and verified entity reference"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block font-medium text-slate-700 mb-1">Order ID</label>
                <input
                  type="text"
                  value={formData.order_id || ''}
                  onChange={(e) => handleFieldChange('order_id', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Customer ID</label>
                <input
                  type="text"
                  value={formData.customer_id || ''}
                  onChange={(e) => handleFieldChange('customer_id', e.target.value)}
                  placeholder="e.g. CUST-00001"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">Product Name</label>
                <input
                  type="text"
                  value={formData.product_name || ''}
                  onChange={(e) => handleFieldChange('product_name', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Quantity (Positive integer)</label>
                <input
                  type="number"
                  min="1"
                  value={formData.quantity ?? ''}
                  onChange={(e) => handleFieldChange('quantity', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Unit Price ($)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={formData.unit_price ?? ''}
                  onChange={(e) => handleFieldChange('unit_price', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block font-medium text-slate-700">Total Amount ($)</label>
                  <button
                    type="button"
                    onClick={handleRecalculateTotal}
                    className="text-[11px] text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
                  >
                    <Calculator className="w-3 h-3" /> Auto-calculate
                  </button>
                </div>
                <input
                  type="number"
                  step="0.01"
                  value={formData.total_amount ?? ''}
                  onChange={(e) => handleFieldChange('total_amount', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">Order Status</label>
                <select
                  value={formData.order_status || 'PENDING'}
                  onChange={(e) => handleFieldChange('order_status', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500"
                >
                  <option value="PENDING">PENDING</option>
                  <option value="CONFIRMED">CONFIRMED</option>
                  <option value="SHIPPED">SHIPPED</option>
                  <option value="DELIVERED">DELIVERED</option>
                  <option value="CANCELLED">CANCELLED</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">Order Date (ISO-8601)</label>
                <input
                  type="text"
                  value={formData.order_date || ''}
                  onChange={(e) => handleFieldChange('order_date', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block font-medium text-slate-700 mb-1">Correction Notes / Reason</label>
                <input
                  type="text"
                  placeholder="e.g. Corrected invalid customer reference and recalculated total"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          )}

          <div className="flex flex-col-reverse sm:flex-row sm:items-center justify-between gap-3 pt-4 border-t border-slate-200">
            <span className="text-[11px] text-slate-400">
              Saving sets status to <span className="font-medium text-indigo-600">CORRECTED</span>. Record will then be eligible for controlled replay.
            </span>
            <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
              <button
                type="button"
                onClick={onClose}
                className="w-full sm:w-auto px-4 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors text-center"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSaving}
                className="w-full sm:w-auto flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors disabled:opacity-50 text-center"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-3.5 h-3.5" />
                    Save Correction
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Tab 2: Verbatim Raw Record */}
      {activeTab === 'raw' && (
        <div className="space-y-3">
          <p className="text-xs text-slate-500">
            Immutable original JSON payload preserved upon ingestion failure:
          </p>
          <pre className="bg-slate-900 text-emerald-400 p-4 rounded-lg font-mono text-xs overflow-x-auto max-h-96">
            {JSON.stringify(record.raw_record, null, 2)}
          </pre>
        </div>
      )}

      {/* Tab 3: Correction Audit History */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          {record.corrections && record.corrections.length > 0 ? (
            record.corrections.map((corr) => (
              <div key={corr.correction_id} className="border border-slate-200 rounded-lg p-3 text-xs space-y-2">
                <div className="flex items-center justify-between text-slate-500 border-b border-slate-100 pb-1.5">
                  <span className="font-semibold text-slate-700">Modified by: {corr.corrected_by}</span>
                  <span>{formatDateTime(corr.created_at)}</span>
                </div>
                {corr.correction_notes && (
                  <p className="italic text-slate-600">"{corr.correction_notes}"</p>
                )}
                <div>
                  <span className="font-medium text-slate-700 block mb-1">Field Diffs:</span>
                  <pre className="bg-slate-50 p-2 rounded font-mono text-[11px] text-slate-700">
                    {JSON.stringify(corr.changed_fields, null, 2)}
                  </pre>
                </div>
              </div>
            ))
          ) : (
            <p className="text-center py-8 text-xs text-slate-400">
              No previous corrections recorded for this quarantine entry.
            </p>
          )}
        </div>
      )}
    </Modal>
  );
}
