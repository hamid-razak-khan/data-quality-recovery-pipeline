import React from 'react';
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
} from 'lucide-react';

const NAV_ITEMS = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Data Ingestion', path: '/ingestion', icon: UploadCloud },
  { name: 'Quarantine Store', path: '/quarantine', icon: AlertTriangle },
  { name: 'Controlled Replay', path: '/replay', icon: RotateCcw },
  { name: 'Processed Records', path: '/processed', icon: CheckCircle },
  { name: 'Pipeline Runs', path: '/runs', icon: History },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 border-r border-slate-800">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 gap-3 border-b border-slate-800">
        <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
          <Layers className="w-5 h-5" />
        </div>
        <div>
          <span className="font-bold text-white text-base tracking-tight block">DQ Pipeline</span>
          <span className="text-[10px] uppercase font-semibold text-blue-400 tracking-wider">Enterprise Ops</span>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 py-6 px-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
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
      <div className="p-4 border-t border-slate-800/80">
        <div className="bg-slate-800/50 rounded-lg p-3 text-xs">
          <div className="flex items-center gap-2 text-emerald-400 font-medium mb-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <Database className="w-3.5 h-3.5" />
            <span>Supabase PostgreSQL</span>
          </div>
          <p className="text-slate-400 text-[11px] truncate">db.isykyiwwramhtohwgwuz</p>
        </div>
      </div>
    </aside>
  );
}
