import React from 'react';

const STATUS_STYLES = {
  // Run statuses
  COMPLETED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  COMPLETED_WITH_ERRORS: 'bg-amber-50 text-amber-700 border-amber-200',
  FAILED: 'bg-rose-50 text-rose-700 border-rose-200',
  RUNNING: 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse',

  // Quarantine statuses
  PENDING: 'bg-amber-50 text-amber-700 border-amber-200',
  CORRECTED: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  REPLAYED: 'bg-emerald-50 text-emerald-700 border-emerald-200',

  // Order statuses
  CONFIRMED: 'bg-blue-50 text-blue-700 border-blue-200',
  SHIPPED: 'bg-purple-50 text-purple-700 border-purple-200',
  DELIVERED: 'bg-teal-50 text-teal-700 border-teal-200',
  CANCELLED: 'bg-slate-100 text-slate-700 border-slate-200',
};

export default function StatusBadge({ status, text }) {
  const normStatus = (status || '').toUpperCase();
  const style = STATUS_STYLES[normStatus] || 'bg-gray-50 text-gray-700 border-gray-200';
  const label = text || status || 'UNKNOWN';

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${style}`}>
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-70" />
      {label}
    </span>
  );
}
