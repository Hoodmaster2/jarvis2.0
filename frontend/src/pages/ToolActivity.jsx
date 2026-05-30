import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

export default function ToolActivity() {
  const [tools, setTools] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadActivity, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const [toolsData, actData] = await Promise.all([
        fetch('/api/tools').then(r => r.json()),
        fetch('/api/tools/activity?limit=50').then(r => r.json()),
      ]);
      setTools(toolsData.tools || []);
      setActivity(actData.activity || []);
    } catch (err) {
      console.error('Failed to load tool data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadActivity = async () => {
    try {
      const actData = await fetch('/api/tools/activity?limit=50').then(r => r.json());
      setActivity(actData.activity || []);
    } catch {}
  };

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Loading tool activity...</p>;

  return (
    <div>
      <div className="page-header">
        <h1>Tool Activity</h1>
        <p>Structured tool calls and execution history</p>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <h3 style={{ marginBottom: 8, fontSize: 14, color: 'var(--text-secondary)' }}>Registered Tools</h3>
          <p style={{ fontSize: 28, fontWeight: 700 }}>{tools.length}</p>
        </div>
        <div className="card">
          <h3 style={{ marginBottom: 8, fontSize: 14, color: 'var(--text-secondary)' }}>Recent Calls</h3>
          <p style={{ fontSize: 28, fontWeight: 700 }}>{activity.length}</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Registered Tool Schemas</h2>
        {tools.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No tools registered</p>
        ) : (
          tools.map((tool, i) => (
            <details key={i} style={{ marginBottom: 8, borderBottom: '1px solid var(--border)', paddingBottom: 8 }}>
              <summary style={{ cursor: 'pointer', fontWeight: 600, fontSize: 14 }}>
                {tool.tool_name}
                <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: 8 }}>
                  ({tool.actions?.length || 0} actions)
                </span>
              </summary>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '4px 0 8px' }}>{tool.description}</p>
              {(tool.actions || []).map((action, j) => (
                <div key={j} style={{ marginLeft: 16, marginBottom: 6, fontSize: 13 }}>
                  <span style={{ color: 'var(--accent-primary)' }}>{action.name}</span>
                  <span style={{ color: 'var(--text-muted)' }}> - {action.description}</span>
                  <span style={{
                    display: 'inline-block',
                    marginLeft: 8,
                    padding: '1px 6px',
                    borderRadius: 4,
                    fontSize: 11,
                    background: action.permission_level === 'critical' ? 'var(--danger)' :
                                action.permission_level === 'high' ? 'var(--warning)' :
                                action.permission_level === 'medium' ? '#4488ff' : 'var(--text-muted)',
                    color: '#fff',
                  }}>
                    {action.permission_level}
                  </span>
                </div>
              ))}
            </details>
          ))
        )}
      </div>

      <div className="card">
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Recent Tool Activity</h2>
        {activity.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No recent tool activity</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Type</th>
                <th>Sender</th>
                <th>Payload</th>
              </tr>
            </thead>
            <tbody>
              {activity.map((evt, i) => (
                <tr key={i}>
                  <td style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                  </td>
                  <td><code style={{ fontSize: 12 }}>{evt.type}</code></td>
                  <td>{evt.sender}</td>
                  <td style={{ fontSize: 12, color: 'var(--text-secondary)', maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {evt.payload}
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
