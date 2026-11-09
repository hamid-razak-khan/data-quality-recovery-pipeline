import React from 'react';
import { PlusCircle, RefreshCw, Menu } from 'lucide-react';

export default function Navbar({ onOpenGenerateModal, onRefresh, isRefreshing, onToggleMobileMenu }) {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between z-20 shrink-0">
      <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
        {/* Mobile Hamburger Menu Toggle */}
        <button
          type="button"
          onClick={onToggleMobileMenu}
          className="lg:hidden p-2 -ml-1 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors shrink-0"
          aria-label="Open sidebar navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Title */}
        <div className="min-w-0">
          <h1 className="text-sm sm:text-base font-semibold text-slate-800 tracking-tight truncate">
            <span className="hidden md:inline">Data Quality & Recovery Pipeline Operations</span>
            <span className="inline md:hidden">DQ Recovery Operations</span>
          </h1>
        </div>

        {/* Live Database Badge */}
        <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 shrink-0">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          PostgreSQL Live
        </span>
      </div>

      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
            title="Refresh pipeline metrics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        )}

        <button
          onClick={onOpenGenerateModal}
          className="flex items-center gap-1.5 px-3 sm:px-3.5 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors shrink-0"
          title="Generate synthetic source records"
        >
          <PlusCircle className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          <span className="hidden sm:inline">Generate Test Data</span>
          <span className="sm:hidden font-semibold">Generate</span>
        </button>
      </div>
    </header>
  );
}
