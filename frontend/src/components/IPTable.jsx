import { useState } from 'react';
import StatusBadge from './StatusBadge';

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function timeLeft(dateStr) {
  if (!dateStr) return 'Permanent';
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff <= 0) return 'Expiring...';
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m left`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h left`;
  return `${Math.floor(hrs / 24)}d left`;
}

export default function IPTable({ ips, onRemove, filter, onFilterChange }) {
  const [removing, setRemoving] = useState(null);

  const handleRemove = async (ip) => {
    if (!confirm(`Remove ${ip} from whitelist?`)) return;
    setRemoving(ip);
    await onRemove(ip);
    setRemoving(null);
  };

  const filters = [
    { label: 'All', value: '' },
    { label: 'Active', value: 'active' },
    { label: 'Expired', value: 'expired' },
    { label: 'Removed', value: 'removed' },
  ];

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <h2 className="text-lg font-semibold">IP Whitelist</h2>
        <div className="flex gap-1 bg-gray-800 rounded-lg p-1">
          {filters.map((f) => (
            <button
              key={f.value}
              onClick={() => onFilterChange(f.value)}
              className={`px-3 py-1 text-xs rounded-md transition-colors ${
                filter === f.value
                  ? 'bg-gray-700 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {ips.length === 0 ? (
        <div className="px-6 py-12 text-center text-gray-500">
          No IPs found
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 text-left border-b border-gray-800">
                <th className="px-6 py-3 font-medium">IP Address</th>
                <th className="px-6 py-3 font-medium">Name</th>
                <th className="px-6 py-3 font-medium">Reason</th>
                <th className="px-6 py-3 font-medium">Status</th>
                <th className="px-6 py-3 font-medium">Pipeline</th>
                <th className="px-6 py-3 font-medium">Duration</th>
                <th className="px-6 py-3 font-medium">Added</th>
                <th className="px-6 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {ips.map((entry) => (
                <tr key={entry.ip} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="px-6 py-3 font-mono text-blue-400">{entry.ip}</td>
                  <td className="px-6 py-3">{entry.name}</td>
                  <td className="px-6 py-3 text-gray-400 max-w-[200px] truncate">{entry.reason}</td>
                  <td className="px-6 py-3">
                    <span className={`text-xs font-medium ${
                      entry.status === 'active' ? 'text-emerald-400' :
                      entry.status === 'expired' ? 'text-yellow-400' : 'text-gray-500'
                    }`}>
                      {entry.status}
                    </span>
                  </td>
                  <td className="px-6 py-3">
                    <StatusBadge status={entry.pipeline_status} />
                  </td>
                  <td className="px-6 py-3 text-gray-400">
                    {entry.status === 'active' ? timeLeft(entry.expires_at) : '—'}
                  </td>
                  <td className="px-6 py-3 text-gray-500">{timeAgo(entry.created_at)}</td>
                  <td className="px-6 py-3">
                    {entry.status === 'active' && (
                      <button
                        onClick={() => handleRemove(entry.ip)}
                        disabled={removing === entry.ip}
                        className="text-red-400 hover:text-red-300 text-xs font-medium
                                   disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {removing === entry.ip ? 'Removing...' : 'Remove'}
                      </button>
                    )}
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
