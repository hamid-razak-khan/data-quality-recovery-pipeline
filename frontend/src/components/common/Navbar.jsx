import React from 'react';
import { Database, PlusCircle, RefreshCw } from 'lucide-react';

export default function Navbar({ onOpenGenerateModal, onRefresh, isRefreshing }) {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between z-10 shrink-0">
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold text-slate-800 tracking-tight">
          Data Quality & Recovery Pipeline Operations
        </h1>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          PostgreSQL Live
        </span>
      </div>

      <div className="flex items-center gap-3">
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
            title="Refresh pipeline metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        )}

        <button
          onClick={onOpenGenerateModal}
          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          Generate Test Data
        </button>
      </div>
    </header>
  );
}
