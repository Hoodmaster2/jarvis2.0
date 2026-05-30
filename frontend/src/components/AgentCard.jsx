import React from 'react';

export default function AgentCard({ agent, status }) {
  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
        <div style={{
          width: 40, height: 40, borderRadius: '50%',
          background: 'var(--accent-glow)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20,
        }}>
          {agent.icon || '🤖'}
        </div>
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>{agent.name}</h3>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{agent.description}</p>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 12, fontSize: 12, color: 'var(--text-muted)' }}>
        <span>Status: {status || 'idle'}</span>
        <span>Tools: {agent.tools?.length || 0}</span>
      </div>
    </div>
  );
}
