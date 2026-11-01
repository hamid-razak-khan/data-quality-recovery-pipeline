import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
import { ArrowRight, ExternalLink } from 'lucide-react';

function CustomErrorTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-slate-900 text-white rounded-lg p-3 text-xs shadow-xl border border-slate-700 min-w-[210px]">
        <div className="font-mono font-bold text-rose-400 border-b border-slate-800 pb-1.5 mb-2">
          {data.error_code}
        </div>
        <div className="space-y-1.5 text-[11px]">
          <div className="flex justify-between">
            <span className="text-slate-400">Total Occurrences:</span>
            <span className="font-bold text-white">
              {data.count.toLocaleString()} ({data.percentage}%)
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-amber-400">Active (Unresolved):</span>
            <span className="font-bold text-amber-300">
              {(data.active_count ?? data.count).toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-emerald-400">Recovered (Replayed):</span>
            <span className="font-bold text-emerald-300">
              {(data.historical_count ?? 0).toLocaleString()}
            </span>
          </div>
        </div>
        <div className="mt-2.5 pt-1.5 border-t border-slate-800 text-[10px] text-blue-300 flex items-center justify-center gap-1 font-medium">
          Click to inspect affected records <ArrowRight className="w-3 h-3" />
        </div>
      </div>
    );
  }
  return null;
}

export default function ErrorBreakdownChart({ data = [] }) {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState('chart'); // 'chart' | 'table'

  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center text-xs text-slate-400 p-6 text-center">
        <p className="font-medium text-slate-500">No quarantine errors recorded in database.</p>
        <p className="text-[11px] mt-1 text-slate-400">The pipeline target store is currently 100% clean.</p>
      </div>
    );
  }

  const handleRowClick = (errorCode) => {
    navigate(`/quarantine?error_code=${encodeURIComponent(errorCode)}`);
  };

  const handleChartClick = (state) => {
    if (state && state.activePayload && state.activePayload.length > 0) {
      const err = state.activePayload[0].payload;
      if (err && err.error_code) {
        handleRowClick(err.error_code);
      }
    }
  };

  return (
    <div className="space-y-3">
      {/* View Mode Toggle */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-500 text-[11px]">
          Showing top {data.length} rejection causes
        </span>
        <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200">
          <button
            type="button"
            onClick={() => setViewMode('chart')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
              viewMode === 'chart'
                ? 'bg-white text-slate-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Chart
          </button>
          <button
            type="button"
            onClick={() => setViewMode('table')}
            className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
              viewMode === 'table'
                ? 'bg-white text-slate-800 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Table & Links
          </button>
        </div>
      </div>

      {viewMode === 'chart' ? (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={data}
              margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
              onClick={handleChartClick}
              className="cursor-pointer"
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
              <XAxis type="number" stroke="#94a3b8" fontSize={11} tickLine={false} />
              <YAxis
                type="category"
                dataKey="error_code"
                stroke="#94a3b8"
                fontSize={10}
                tickLine={false}
                width={130}
              />
              <Tooltip content={<CustomErrorTooltip />} />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '6px' }} />
              <Bar dataKey="active_count" name="Active (Unresolved)" fill="#f43f5e" stackId="a" radius={[0, 0, 0, 0]} />
              <Bar dataKey="historical_count" name="Recovered (Replayed)" fill="#10b981" stackId="a" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="overflow-x-auto max-h-64 overflow-y-auto border border-slate-200 rounded-lg">
          <table className="w-full text-left border-collapse text-xs">
            <thead className="bg-slate-50 sticky top-0 border-b border-slate-200 text-slate-500 uppercase text-[10px] tracking-wider">
              <tr>
                <th className="py-2 px-3">Error Code</th>
                <th className="py-2 px-3 text-right">Active</th>
                <th className="py-2 px-3 text-right">Recovered</th>
                <th className="py-2 px-3 text-right">Total (% of DQ)</th>
                <th className="py-2 px-3 text-center">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((item) => (
                <tr
                  key={item.error_code}
                  onClick={() => handleRowClick(item.error_code)}
                  className="hover:bg-slate-50/80 cursor-pointer transition-colors"
                >
                  <td className="py-2 px-3 font-mono font-semibold text-rose-600 truncate max-w-[150px]">
                    {item.error_code}
                  </td>
                  <td className="py-2 px-3 text-right font-medium text-amber-600">
                    {(item.active_count ?? item.count).toLocaleString()}
                  </td>
                  <td className="py-2 px-3 text-right font-medium text-emerald-600">
                    {(item.historical_count ?? 0).toLocaleString()}
                  </td>
                  <td className="py-2 px-3 text-right font-bold text-slate-800">
                    {item.count.toLocaleString()}{' '}
                    <span className="text-[10px] text-slate-400 font-normal">
                      ({item.percentage}%)
                    </span>
                  </td>
                  <td className="py-2 px-3 text-center">
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 text-[11px] text-blue-600 hover:text-blue-700 font-medium hover:underline"
                    >
                      View <ExternalLink className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
