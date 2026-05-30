import React, { useState } from 'react';

export default function Logs() {
  const [logs, setLogs] = useState([
    { time: new Date().toISOString(), level: 'info', msg: 'JARVIS backend started' },
    { time: new Date().toISOString(), level: 'info', msg: 'Ollama connection established' },
    { time: new Date().toISOString(), level: 'info', msg: 'Memory database initialized' },
    { time: new Date().toISOString(), level: 'info', msg: 'Skills loaded: file_manager, browser_playwright, powershell_runner' },
  ]);
  const [filter, setFilter] = useState('all');

  const filteredLogs = filter === 'all' ? logs : logs.filter(l => l.level === filter);

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Logs</h1>
            <p>System and agent activity log</p>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <select value={filter} onChange={(e) => setFilter(e.target.value)} style={{ fontSize: 12 }}>
              <option value="all">All</option>
              <option value="info">Info</option>
              <option value="warn">Warning</option>
              <option value="error">Error</option>
              <option value="debug">Debug</option>
            </select>
            <button className="btn btn-sm">Refresh</button>
            <button className="btn btn-sm">Clear</button>
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: 0, fontFamily: 'var(--font-mono)', fontSize: 12 }}>
        <div style={{
          padding: '8px 12px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          gap: 12,
          color: 'var(--text-muted)',
          fontWeight: 600,
          textTransform: 'uppercase',
          fontSize: 10,
          letterSpacing: 0.5,
        }}>
          <span style={{ width: 160, flexShrink: 0 }}>Time</span>
          <span style={{ width: 48, flexShrink: 0 }}>Level</span>
          <span>Message</span>
        </div>
        {filteredLogs.length === 0 ? (
          <div style={{ padding: 20, color: 'var(--text-muted)' }}>No log entries</div>
        ) : (
          filteredLogs.map((log, i) => (
            <div key={i} className="log-entry">
              <span className="log-time">{new Date(log.time).toLocaleTimeString()}</span>
              <span className={`log-level ${log.level}`}>{log.level.toUpperCase()}</span>
              <span className="log-msg">{log.msg}</span>
            </div>
          ))
        )}
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Live Log</h3>
        <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Live log streaming will appear here. Connect to the backend WebSocket for real-time updates.
        </p>
      </div>
    </div>
  );
}
