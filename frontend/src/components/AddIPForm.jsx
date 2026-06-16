import { useState } from 'react';

const DURATION_OPTIONS = [
  { label: '15 min', value: 15 },
  { label: '30 min', value: 30 },
  { label: '1 hour', value: 60 },
  { label: '4 hours', value: 240 },
  { label: '24 hours', value: 1440 },
  { label: 'Custom', value: -1 },
];

export default function AddIPForm({ onSubmit, loading }) {
  const [ip, setIp] = useState('');
  const [name, setName] = useState('');
  const [reason, setReason] = useState('');
  const [duration, setDuration] = useState(60);
  const [customMinutes, setCustomMinutes] = useState('');
  const [isCustom, setIsCustom] = useState(false);

  const handleDurationChange = (val) => {
    const v = Number(val);
    if (v === -1) {
      setIsCustom(true);
      setDuration(-1);
    } else {
      setIsCustom(false);
      setDuration(v);
      setCustomMinutes('');
    }
  };

  const getEffectiveDuration = () => {
    if (isCustom) {
      const mins = parseInt(customMinutes, 10);
      return isNaN(mins) || mins <= 0 ? null : mins;
    }
    return duration;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const mins = getEffectiveDuration();
    if (mins === null) return;
    await onSubmit(ip, name, reason, mins);
    setIp('');
    setName('');
    setReason('');
    setDuration(60);
    setCustomMinutes('');
    setIsCustom(false);
  };

  const isValid = ip && name && reason && getEffectiveDuration() !== null;

  return (
    <form onSubmit={handleSubmit} className="bg-gray-900 border border-gray-800 rounded-xl p-6">
      <h2 className="text-lg font-semibold mb-4">Request IP Access</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">IP Address</label>
          <input
            type="text"
            value={ip}
            onChange={(e) => setIp(e.target.value)}
            placeholder="e.g. 203.45.67.89"
            required
            pattern="^(\d{1,3}\.){3}\d{1,3}$"
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm
                       focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                       placeholder-gray-500"
          />
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Your Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Jayant"
            required
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm
                       focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                       placeholder-gray-500"
          />
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm text-gray-400 mb-1">Reason</label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. Need access for demo session"
            required
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm
                       focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                       placeholder-gray-500"
          />
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Duration</label>
          <select
            value={isCustom ? -1 : duration}
            onChange={(e) => handleDurationChange(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm
                       focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          >
            {DURATION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {isCustom && (
          <div>
            <label className="block text-sm text-gray-400 mb-1">Minutes</label>
            <input
              type="number"
              value={customMinutes}
              onChange={(e) => setCustomMinutes(e.target.value)}
              placeholder="Enter minutes"
              min="1"
              required
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm
                         focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500
                         placeholder-gray-500"
            />
          </div>
        )}

        <div className={`flex items-end ${isCustom ? 'md:col-span-2' : ''}`}>
          <button
            type="submit"
            disabled={loading || !isValid}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-600/50
                       disabled:cursor-not-allowed text-white font-medium rounded-lg
                       px-4 py-2 text-sm transition-colors"
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Adding...
              </span>
            ) : 'Whitelist IP'}
          </button>
        </div>
      </div>
    </form>
  );
}
