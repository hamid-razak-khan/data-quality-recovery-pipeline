import React, { useState, useRef, useEffect } from 'react';
import { Info } from 'lucide-react';

export default function StatCard({ title, value, subtitle, tooltip, icon: Icon, color = 'blue' }) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  const colorMap = {
    blue: 'bg-blue-50 text-blue-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    purple: 'bg-purple-50 text-purple-600',
    rose: 'bg-rose-50 text-rose-600',
    indigo: 'bg-indigo-50 text-indigo-600',
  };

  const iconBg = colorMap[color] || colorMap.blue;

  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [isOpen]);

  return (
    <div className="relative bg-white rounded-xl border border-slate-200/80 p-4 sm:p-5 shadow-xs hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0 pr-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <p className="text-[11px] sm:text-xs font-semibold uppercase tracking-wider text-slate-500 truncate">{title}</p>
            {tooltip && (
              <div
                ref={containerRef}
                className="relative inline-flex items-center"
                onMouseEnter={() => setIsOpen(true)}
                onMouseLeave={() => setIsOpen(false)}
              >
                <button
                  type="button"
                  onClick={() => setIsOpen((prev) => !prev)}
                  className="text-slate-400 hover:text-slate-600 focus:outline-none p-0.5 rounded"
                  aria-label={`Calculation rules for ${title}`}
                >
                  <Info className="w-3.5 h-3.5" />
                </button>
                {isOpen && (
                  <div className="absolute left-0 sm:left-auto sm:right-0 md:left-0 bottom-full mb-2 z-50 w-64 sm:w-72 max-w-[calc(100vw-3rem)] p-3 bg-slate-900 text-slate-200 text-xs rounded-lg shadow-xl border border-slate-700 animate-in fade-in zoom-in-95 duration-150">
                    <div className="font-semibold text-white mb-1">{title}</div>
                    {typeof tooltip === 'string' ? (
                      <p className="text-[11px] leading-relaxed text-slate-300">{tooltip}</p>
                    ) : (
                      <div className="space-y-1.5 text-[11px]">
                        {tooltip.formula && (
                          <div>
                            <span className="text-slate-400 font-semibold block text-[10px] uppercase">Calculation:</span>
                            <span className="font-mono text-emerald-400 break-all">{tooltip.formula}</span>
                          </div>
                        )}
                        {tooltip.rules && (
                          <div>
                            <span className="text-slate-400 font-semibold block text-[10px] uppercase">Counting Rule:</span>
                            <span className="text-slate-300 leading-tight">{tooltip.rules}</span>
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
                    <div className="absolute left-3 sm:left-auto sm:right-3 md:left-3 top-full w-2 h-2 bg-slate-900 border-r border-b border-slate-700 transform rotate-45 -mt-1" />
                  </div>
                )}
              </div>
            )}
          </div>
          <h3 className="text-xl sm:text-2xl font-bold text-slate-900 mt-1 truncate">{value}</h3>
          {subtitle && <p className="text-[11px] sm:text-xs text-slate-500 mt-0.5 truncate">{subtitle}</p>}
        </div>
        {Icon && (
          <div className={`p-2.5 sm:p-3 rounded-lg ${iconBg} shrink-0`}>
            <Icon className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
        )}
      </div>
    </div>
  );
}
