const API_BASE = import.meta.env.VITE_API_BASE || '/llm-blocker/v1';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || data.error || 'Request failed');
  return data;
}

export const api = {
  addIP: (ip, name, reason, durationMinutes) =>
    request('/ips', {
      method: 'POST',
      body: JSON.stringify({
        ip,
        name,
        reason,
        duration_minutes: durationMinutes,
      }),
    }),

  removeIP: (ip, reason = 'Manual removal') =>
    request(`/ips/${ip}`, {
      method: 'DELETE',
      body: JSON.stringify({ reason }),
    }),

  listIPs: (status = null) =>
    request(`/ips${status ? `?status=${status}` : ''}`),

  getIP: (ip) => request(`/ips/${ip}`),

  getAudit: (limit = 50) => request(`/audit?limit=${limit}`),
};
