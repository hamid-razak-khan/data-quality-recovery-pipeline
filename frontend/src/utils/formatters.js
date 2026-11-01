export function formatNumber(val) {
  if (val === null || val === undefined || isNaN(val)) return '0';
  return Number(val).toLocaleString();
}

export function formatCurrency(val) {
  if (val === null || val === undefined || isNaN(val)) return '$0.00';
  return `$${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatDateTime(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return String(isoString);
  }
}

export function formatDate(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return String(isoString);
  }
}

export function formatDuration(sec) {
  if (!sec && sec !== 0) return '—';
  const s = Number(sec);
  if (s < 1) return `${(s * 1000).toFixed(0)} ms`;
  if (s < 60) return `${s.toFixed(2)} s`;
  const mins = Math.floor(s / 60);
  const rem = (s % 60).toFixed(1);
  return `${mins}m ${rem}s`;
}

export function truncateId(id, len = 8) {
  if (!id) return '';
  return String(id).substring(0, len);
}
