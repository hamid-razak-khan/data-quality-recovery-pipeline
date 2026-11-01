import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

export const api = {
  // Monitoring & Metrics
  getMetrics: (params) => client.get('/metrics/', { params }).then(res => res.data),
  getReconciliation: () => client.get('/metrics/reconciliation/').then(res => res.data),

  // Ingestion & Pipeline Runs
  uploadFile: (formData, onProgress) =>
    client.post('/ingestion/upload/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
    }).then(res => res.data),

  runPipeline: (payload) => client.post('/pipeline/run/', payload).then(res => res.data),
  getPipelineRuns: (params) => client.get('/pipeline/runs/', { params }).then(res => res.data),
  getPipelineRun: (runId) => client.get(`/pipeline/runs/${runId}/`).then(res => res.data),

  // Quarantine
  getQuarantineRecords: (params) => client.get('/quarantine/', { params }).then(res => res.data),
  getQuarantineRecord: (id) => client.get(`/quarantine/${id}/`).then(res => res.data),
  correctQuarantineRecord: (id, payload) =>
    client.patch(`/quarantine/${id}/correct/`, payload).then(res => res.data),
  getQuarantineSummary: () => client.get('/quarantine/summary/').then(res => res.data),

  // Replay
  triggerReplay: (payload) => client.post('/replay/', payload).then(res => res.data),
  getReplayHistory: (params) => client.get('/replay/history/', { params }).then(res => res.data),

  // Processed Orders
  getProcessedOrders: (params) => client.get('/processed/', { params }).then(res => res.data),
  getProcessedOrder: (id) => client.get(`/processed/${id}/`).then(res => res.data),

  // Data Generation
  generateData: (payload) => client.post('/data/generate/', payload).then(res => res.data),
};

export default api;
