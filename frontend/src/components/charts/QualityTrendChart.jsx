import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';

function CustomTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const valid = data.valid_records || 0;
    const rejected = data.rejected_records || 0;
    const total = data.total_records || (valid + rejected);
    const yieldPct = total > 0 ? ((valid / total) * 100).toFixed(1) : '0.0';

    return (
      <div className="bg-slate-900 text-white rounded-lg p-3 text-xs shadow-xl border border-slate-700 min-w-[200px]">
        <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-1.5 mb-2">
          <span className="font-mono font-bold text-slate-200">Run: {data.run_id}</span>
          <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30">
            {data.schema || 'generic'}
          </span>
        </div>
        <div className="text-[11px] text-slate-300 truncate max-w-[220px] mb-2 font-medium" title={data.filename}>
          {data.filename}
        </div>
        <div className="space-y-1 text-[11px]">
          <div className="flex justify-between">
            <span className="text-emerald-400">Valid (Published):</span>
            <span className="font-bold">{valid.toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-rose-400">Quarantined:</span>
            <span className="font-bold">{rejected.toLocaleString()}</span>
          </div>
          <div className="flex justify-between border-t border-slate-800 pt-1 text-slate-300">
            <span>Total Ingested:</span>
            <span className="font-bold">{total.toLocaleString()}</span>
          </div>
          <div className="flex justify-between text-indigo-300">
            <span>First-pass Yield:</span>
            <span className="font-bold">{yieldPct}%</span>
          </div>
          {data.throughput_rps > 0 && (
            <div className="flex justify-between text-amber-300 text-[10px]">
              <span>Throughput:</span>
              <span>{data.throughput_rps} rec/s</span>
            </div>
          )}
        </div>
        <div className="mt-2.5 pt-1.5 border-t border-slate-800 text-[10px] text-blue-300 text-center font-medium">
          Click bar to inspect execution details
        </div>
      </div>
    );
  }
  return null;
}

export default function QualityTrendChart({ data = [], onBarClick }) {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center text-xs text-slate-400 p-6 text-center">
        <p className="font-medium text-slate-500">No execution trend data matching criteria.</p>
        <p className="text-[11px] mt-1 text-slate-400">Adjust the filters above or upload new datasets to observe data quality metrics.</p>
      </div>
    );
  }

  const handleChartClick = (state) => {
    if (state && state.activePayload && state.activePayload.length > 0) {
      const clicked = state.activePayload[0].payload;
      if (onBarClick) {
        onBarClick(clicked);
      }
    }
  };

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
          onClick={handleChartClick}
          className="cursor-pointer"
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis dataKey="run_id" stroke="#94a3b8" fontSize={11} tickLine={false} />
          <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
          <Bar dataKey="valid_records" name="Valid Records" fill="#10b981" radius={[4, 4, 0, 0]} stackId="a" />
          <Bar dataKey="rejected_records" name="Quarantined" fill="#f43f5e" radius={[4, 4, 0, 0]} stackId="a" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
