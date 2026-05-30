import React, { useState, useEffect } from 'react';

export default function BackgroundActivity() {
  const [status, setStatus] = useState(null);
  const [observers, setObservers] = useState([]);
  const [queue, setQueue] = useState(null);
  const [events, setEvents] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadAll = async () => {
    try {
      const [statRes, obsRes, queueRes, evtRes, sugRes] = await Promise.all([
        fetch('/api/background/status'),
        fetch('/api/observers'),
        fetch('/api/queue/status'),
        fetch('/api/events?limit=30'),
        fetch('/api/background/suggestions'),
      ]);
      setStatus(await statRes.json());
      setObservers((await obsRes.json()).observers || []);
      setQueue(await queueRes.json());
      setEvents((await evtRes.json()).events || []);
      setSuggestions((await sugRes.json()).suggestions || []);
    } catch (err) {
      console.error('Failed to load background data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadStatus = async () => {
    try {
      const statRes = await fetch('/api/background/status');
      setStatus(await statRes.json());
    } catch {}
  };

  const toggleObserver = async (name, enabled) => {
    await fetch(`/api/observers/${name}/toggle`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !enabled }),
    });
    loadAll();
  };

  const requestSuggestion = async () => {
    try {
      const res = await fetch('/api/background/suggest', { method: 'POST' });
      const data = await res.json();
      if (data.suggestion) {
        setSuggestions(prev => [{ content: data.suggestion, type: 'suggestion' }, ...prev]);
      }
    } catch {}
  };

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Loading background activity...</p>;

  return (
    <div>
      <div className="page-header">
        <h1>Background Activity</h1>
        <p>Daemon status, observers, and event history</p>
      </div>

      <div className="grid grid-3" style={{ marginBottom: 24 }}>
        <div className="card">
          <h3 style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 8 }}>Daemon</h3>
          <p style={{ fontSize: 13 }}>
            Status: <span style={{ color: status?.running ? 'var(--success)' : 'var(--danger)' }}>
              {status?.running ? 'Running' : 'Stopped'}
            </span>
          </p>
          <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Uptime: {Math.floor((status?.uptime || 0) / 60)}m
          </p>
        </div>
        <div className="card">
          <h3 style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 8 }}>Task Queue</h3>
          <p style={{ fontSize: 13 }}>Pending: {queue?.pending || 0}</p>
          <p style={{ fontSize: 13 }}>Running: {queue?.running || 0}</p>
          <p style={{ fontSize: 13 }}>Completed: {queue?.completed || 0}</p>
        </div>
        <div className="card">
          <h3 style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 8 }}>Notifications</h3>
          <p style={{ fontSize: 13 }}>Unread: {status?.notifications?.unread || 0}</p>
          <p style={{ fontSize: 13 }}>Total: {status?.notifications?.total || 0}</p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        <button className="btn" onClick={requestSuggestion}>Generate Suggestion</button>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <h2 style={{ fontSize: 16, marginBottom: 12 }}>Observers</h2>
          {observers.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No observers</p>
          ) : (
            observers.map((obs, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                <div>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{obs.name}</span>
                  <span style={{ color: 'var(--text-muted)', fontSize: 12, marginLeft: 8 }}>{obs.interval}s interval</span>
                </div>
                <label className="toggle">
                  <input type="checkbox" checked={obs.enabled} onChange={() => toggleObserver(obs.name, obs.enabled)} />
                  <span className="toggle-slider" />
                </label>
              </div>
            ))
          )}
        </div>

        <div className="card">
          <h2 style={{ fontSize: 16, marginBottom: 12 }}>Suggestions</h2>
          {suggestions.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No suggestions yet</p>
          ) : (
            suggestions.slice(0, 10).map((s, i) => (
              <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                <p style={{ color: 'var(--text-secondary)' }}>{typeof s === 'string' ? s : s.content}</p>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="card">
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Recent Events</h2>
        {events.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No recent events</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Type</th>
                <th>Sender</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              {events.map((evt, i) => (
                <tr key={i}>
                  <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                  </td>
                  <td><code style={{ fontSize: 12 }}>{evt.type}</code></td>
                  <td>{evt.sender}</td>
                  <td style={{ color: evt.priority === 'HIGH' ? 'var(--warning)' : 'var(--text-muted)' }}>
                    {evt.priority}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
