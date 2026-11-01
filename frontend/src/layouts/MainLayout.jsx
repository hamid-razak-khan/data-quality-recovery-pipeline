import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/common/Sidebar';
import Navbar from '../components/common/Navbar';
import Modal from '../components/common/Modal';
import Toast from '../components/common/Toast';
import api from '../services/api';
import { Sparkles, Loader2 } from 'lucide-react';

export default function MainLayout() {
  const [toast, setToast] = useState(null);
  const [isGenerateOpen, setIsGenerateOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [genParams, setGenParams] = useState({
    records: 1000,
    seed: 42,
    invalid_ratio: 0.10,
  });

  const showToast = (message, type = 'success', title = null) => {
    setToast({ message, type, title });
    setTimeout(() => setToast(null), 5000);
  };

  const handleGenerateData = async (e) => {
    e.preventDefault();
    setGenerating(true);
    try {
      const res = await api.generateData(genParams);
      showToast(
        `Generated ${res.record_count} synthetic orders in ${res.file_name}`,
        'success',
        'Data Generated'
      );
      setIsGenerateOpen(false);
    } catch (err) {
      showToast(
        err.response?.data?.error || 'Failed to generate data.',
        'error',
        'Generation Error'
      );
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Navbar onOpenGenerateModal={() => setIsGenerateOpen(true)} />

        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <Outlet context={{ showToast }} />
        </main>
      </div>

      {/* Generate Data Modal */}
      <Modal
        isOpen={isGenerateOpen}
        onClose={() => setIsGenerateOpen(false)}
        title="Synthetic Data Generator"
        maxWidth="max-w-md"
      >
        <form onSubmit={handleGenerateData} className="space-y-4">
          <p className="text-xs text-slate-500">
            Generate reproducible customer and order records with controlled invalid patterns (missing fields, invalid foreign keys, negative amounts, malformed dates).
          </p>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Number of Order Records
            </label>
            <input
              type="number"
              value={genParams.records}
              onChange={(e) => setGenParams({ ...genParams, records: parseInt(e.target.value) || 100 })}
              min="10"
              max="500000"
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Random Seed (for reproducibility)
            </label>
            <input
              type="number"
              value={genParams.seed}
              onChange={(e) => setGenParams({ ...genParams, seed: parseInt(e.target.value) || 42 })}
              className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Invalid Records Ratio ({Math.round(genParams.invalid_ratio * 100)}%)
            </label>
            <input
              type="range"
              min="0"
              max="0.5"
              step="0.05"
              value={genParams.invalid_ratio}
              onChange={(e) => setGenParams({ ...genParams, invalid_ratio: parseFloat(e.target.value) })}
              className="w-full"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setIsGenerateOpen(false)}
              className="px-3.5 py-2 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={generating}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {generating ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  Generate Dataset
                </>
              )}
            </button>
          </div>
        </form>
      </Modal>

      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
