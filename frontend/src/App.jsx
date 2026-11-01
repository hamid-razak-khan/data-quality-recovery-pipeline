import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import Ingestion from './pages/Ingestion';
import Quarantine from './pages/Quarantine';
import Replay from './pages/Replay';
import ProcessedRecords from './pages/ProcessedRecords';
import PipelineRuns from './pages/PipelineRuns';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="ingestion" element={<Ingestion />} />
          <Route path="quarantine" element={<Quarantine />} />
          <Route path="replay" element={<Replay />} />
          <Route path="processed" element={<ProcessedRecords />} />
          <Route path="runs" element={<PipelineRuns />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
