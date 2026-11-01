import React, { useState } from 'react';
import { Info } from 'lucide-react';

export default function StatCard({ title, value, subtitle, tooltip, icon: Icon, color = 'blue' }) {
  const [isHovered, setIsHovered] = useState(false);

  const colorMap = {
    blue: 'bg-blue-50 text-blue-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    purple: 'bg-purple-50 text-purple-600',
    rose: 'bg-rose-50 text-rose-600',
    indigo: 'bg-indigo-50 text-indigo-600',
  };

  const iconBg = colorMap[color] || colorMap.blue;

  return (
    <div className="relative bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1 pr-2">
          <div className="flex items-center gap-1.5">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p>
            {tooltip && (
              <div
                className="relative inline-flex items-center"
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
              >
                <button
                  type="button"
                  className="text-slate-400 hover:text-slate-600 focus:outline-hidden p-0.5"
                  aria-label={`Calculation rules for ${title}`}
                >
                  <Info className="w-3.5 h-3.5" />
                </button>
                {isHovered && (
                  <div className="absolute left-0 bottom-full mb-2 z-50 w-64 p-3 bg-slate-900 text-slate-200 text-xs rounded-lg shadow-xl border border-slate-700 pointer-events-none animate-in fade-in zoom-in-95 duration-150">
                    <div className="font-semibold text-white mb-1">{title}</div>
                    {typeof tooltip === 'string' ? (
                      <p className="text-[11px] leading-relaxed text-slate-300">{tooltip}</p>
                    ) : (
                      <div className="space-y-1.5 text-[11px]">
                        {tooltip.formula && (
                          <div>
                            <span className="text-slate-400 font-semibold block text-[10px] uppercase">Calculation:</span>
                            <span className="font-mono text-emerald-400">{tooltip.formula}</span>
                          </div>
                        )}
                        {tooltip.rules && (
                          <div>
                            <span className="text-slate-400 font-semibold block text-[10px] uppercase">Counting Rule:</span>
                            <span className="text-slate-300">{tooltip.rules}</span>
                          </div>
                        )}
                        {tooltip.source && (
                          <div>
                            <span className="text-slate-400 font-semibold block text-[10px] uppercase">Data Source:</span>
                            <span className="text-slate-400">{tooltip.source}</span>
                          </div>
                        )}
                      </div>
                    )}
                    <div className="absolute left-3 top-full w-2 h-2 bg-slate-900 border-r border-b border-slate-700 transform rotate-45 -mt-1" />
                  </div>
                )}
              </div>
            )}
          </div>
          <h3 className="text-2xl font-bold text-slate-900 mt-1">{value}</h3>
          {subtitle && <p className="text-xs text-slate-500 mt-1">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={`p-3 rounded-lg ${iconBg} shrink-0`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>
    </div>
  );
}
