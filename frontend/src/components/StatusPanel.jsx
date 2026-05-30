import React from 'react';

export default function StatusPanel({ status, onClose }) {
  return (
    <div className="status-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h3>System Status</h3>
        <button className="btn btn-sm" onClick={onClose}>✕</button>
      </div>

      <div className="status-item">
        <span className="label">Ollama</span>
        <span className="value">
          <span className={`status-dot ${status.connected ? 'connected' : 'disconnected'}`} style={{ marginRight: 6 }} />
          {status.connected ? 'Connected' : 'Disconnected'}
        </span>
      </div>

      <div className="status-item">
        <span className="label">Model</span>
        <span className="value">{status.model || 'N/A'}</span>
      </div>

      <div className="status-item">
        <span className="label">Skills</span>
        <span className="value">{status.skillsCount ?? 0} loaded</span>
      </div>

      <div className="status-item">
        <span className="label">Platform</span>
        <span className="value">{status.platform || 'N/A'}</span>
      </div>
    </div>
  );
}
