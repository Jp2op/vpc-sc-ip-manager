import { useState, useEffect, useCallback } from 'react';
import { api } from './api';
import AddIPForm from './components/AddIPForm';
import IPTable from './components/IPTable';
import AuditLog from './components/AuditLog';

export default function App() {
  const [ips, setIps] = useState([]);
  const [audit, setAudit] = useState([]);
  const [filter, setFilter] = useState('');
  const [tab, setTab] = useState('ips');
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [stats, setStats] = useState({ total: 0, active: 0 });

  const fetchIPs = useCallback(async () => {
    try {
      const data = await api.listIPs(filter || null);
      setIps(data.ips);
      setStats({ total: data.total, active: data.active_count });
    } catch (err) {
      console.error('Failed to fetch IPs:', err);
    }
  }, [filter]);

  const fetchAudit = useCallback(async () => {
    try {
      const data = await api.getAudit(50);
      setAudit(data.entries);
    } catch (err) {
      console.error('Failed to fetch audit:', err);
    }
  }, []);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    fetchIPs();
    const interval = setInterval(fetchIPs, 5000);
    return () => clearInterval(interval);
  }, [fetchIPs]);

  useEffect(() => {
    if (tab === 'audit') fetchAudit();
  }, [tab, fetchAudit]);

  const handleAdd = async (ip, name, reason, duration) => {
    setAdding(true);
    setError('');
    setSuccess('');
    try {
      await api.addIP(ip, name, reason, duration);
      setSuccess(`${ip} added successfully. Pipeline is processing...`);
      await fetchIPs();
      setTimeout(() => setSuccess(''), 5000);
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(''), 5000);
    } finally {
      setAdding(false);
    }
  };

  const handleRemove = async (ip) => {
    setError('');
    setSuccess('');
    try {
      await api.removeIP(ip);
      setSuccess(`${ip} removed.`);
      await fetchIPs();
      setTimeout(() => setSuccess(''), 5000);
    } catch (err) {
      setError(err.message);
      setTimeout(() => setError(''), 5000);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🛡️</span>
            <div>
              <h1 className="text-lg font-bold">{import.meta.env.VITE_APP_TITLE || 'LLM Access Manager'}</h1>
              <p className="text-xs text-gray-500">VPC Service Controls — IP Whitelisting</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-gray-400">{stats.active} active</span>
            </div>
            <div className="text-gray-600">{stats.total} total</div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        {/* Notifications */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError('')} className="text-red-400 hover:text-red-300">✕</button>
          </div>
        )}
        {success && (
          <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
            <span>{success}</span>
            <button onClick={() => setSuccess('')} className="text-emerald-400 hover:text-emerald-300">✕</button>
          </div>
        )}

        {/* Add IP Form */}
        <AddIPForm onSubmit={handleAdd} loading={adding} />

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-900 rounded-lg p-1 w-fit border border-gray-800">
          <button
            onClick={() => setTab('ips')}
            className={`px-4 py-2 text-sm rounded-md transition-colors ${
              tab === 'ips' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            IP Whitelist
          </button>
          <button
            onClick={() => setTab('audit')}
            className={`px-4 py-2 text-sm rounded-md transition-colors ${
              tab === 'audit' ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white'
            }`}
          >
            Audit Log
          </button>
        </div>

        {/* Content */}
        {tab === 'ips' && (
          <IPTable
            ips={ips}
            onRemove={handleRemove}
            filter={filter}
            onFilterChange={setFilter}
          />
        )}
        {tab === 'audit' && <AuditLog entries={audit} />}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-12">
        <div className="max-w-6xl mx-auto px-6 py-4 text-center text-xs text-gray-600">
          Auto-refreshes every 5 seconds
        </div>
      </footer>
    </div>
  );
}
