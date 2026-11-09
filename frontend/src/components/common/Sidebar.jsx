import React, { useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  UploadCloud,
  AlertTriangle,
  RotateCcw,
  CheckCircle,
  History,
  Database,
  Layers,
  X,
} from 'lucide-react';

const NAV_ITEMS = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Data Ingestion', path: '/ingestion', icon: UploadCloud },
  { name: 'Quarantine Store', path: '/quarantine', icon: AlertTriangle },
  { name: 'Controlled Replay', path: '/replay', icon: RotateCcw },
  { name: 'Processed Records', path: '/processed', icon: CheckCircle },
  { name: 'Pipeline Runs', path: '/runs', icon: History },
];

function SidebarContent({ onClose, isMobile = false }) {
  return (
    <div className="flex flex-col h-full">
      {/* Brand Header */}
      <div className="h-16 flex items-center justify-between px-5 sm:px-6 border-b border-slate-800 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 shrink-0">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-white text-base tracking-tight block">DQ Pipeline</span>
            <span className="text-[10px] uppercase font-semibold text-blue-400 tracking-wider">Enterprise Ops</span>
          </div>
        </div>

        {isMobile && (
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            aria-label="Close navigation menu"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 py-5 px-3 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              onClick={() => onClose && onClose()}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-100'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Target Database Footer */}
      <div className="p-4 border-t border-slate-800/80 shrink-0">
        <div className="bg-slate-800/50 rounded-lg p-3 text-xs">
          <div className="flex items-center gap-2 text-emerald-400 font-medium mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping shrink-0" />
            <Database className="w-3.5 h-3.5 shrink-0" />
            <span className="truncate">Supabase PostgreSQL</span>
          </div>
          <p className="text-slate-400 text-[11px] font-mono truncate">db.isykyiwwramhtohwgwuz</p>
        </div>
      </div>
    </div>
  );
}

export default function Sidebar({ isOpen, onClose }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen && onClose) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Lock body scroll on mobile when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside className="hidden lg:flex w-64 bg-slate-900 text-slate-300 flex-col shrink-0 border-r border-slate-800 h-full">
        <SidebarContent />
      </aside>

      {/* Mobile & Tablet Drawer with Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs z-40 transition-opacity lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 w-72 max-w-[85vw] bg-slate-900 text-slate-300 flex flex-col z-50 border-r border-slate-800 shadow-2xl transition-transform duration-300 ease-in-out lg:hidden ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Mobile Navigation"
      >
        <SidebarContent onClose={onClose} isMobile={true} />
      </aside>
    </>
  );
}
