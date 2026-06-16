const ACTION_STYLES = {
  added: 'text-emerald-400 bg-emerald-500/10',
  removed: 'text-red-400 bg-red-500/10',
  expired: 'text-yellow-400 bg-yellow-500/10',
};

function formatTime(dateStr) {
  return new Date(dateStr).toLocaleString();
}

export default function AuditLog({ entries }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-800">
        <h2 className="text-lg font-semibold">Audit Log</h2>
      </div>

      {entries.length === 0 ? (
        <div className="px-6 py-12 text-center text-gray-500">
          No activity yet
        </div>
      ) : (
        <div className="divide-y divide-gray-800/50">
          {entries.map((entry, i) => (
            <div key={i} className="px-6 py-3 flex items-center gap-4 text-sm">
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${ACTION_STYLES[entry.action] || ''}`}>
                {entry.action}
              </span>
              <span className="font-mono text-blue-400">{entry.ip}</span>
              <span className="text-gray-400 flex-1 truncate">{entry.reason}</span>
              <span className="text-gray-500 text-xs">{entry.performed_by}</span>
              <span className="text-gray-600 text-xs whitespace-nowrap">{formatTime(entry.timestamp)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
