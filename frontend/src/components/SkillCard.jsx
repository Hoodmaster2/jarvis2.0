import React from 'react';

export default function SkillCard({ skill, onToggle }) {
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{skill.name}</h3>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>{skill.description}</p>
          {skill.commands && skill.commands.length > 0 && (
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
              {skill.commands.map((cmd, i) => (
                <span key={i} style={{
                  background: 'var(--bg-tertiary)',
                  padding: '2px 8px',
                  borderRadius: 4,
                  fontSize: 11,
                  color: 'var(--accent-primary)',
                  fontFamily: 'var(--font-mono)',
                }}>
                  {cmd.name || cmd}
                </span>
              ))}
            </div>
          )}
        </div>
        <label className="toggle">
          <input
            type="checkbox"
            checked={skill.enabled !== false}
            onChange={() => onToggle(skill.name, skill.enabled === false)}
          />
          <span className="toggle-slider" />
        </label>
      </div>
      {skill.permissions && skill.permissions.length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {skill.permissions.map((perm, i) => (
            <span key={i} style={{
              padding: '2px 8px',
              borderRadius: 4,
              fontSize: 10,
              background: perm === 'critical' ? 'rgba(255,68,68,0.15)' :
                          perm === 'high' ? 'rgba(255,170,68,0.15)' : 'rgba(68,255,136,0.15)',
              color: perm === 'critical' ? 'var(--danger)' :
                     perm === 'high' ? 'var(--warning)' : 'var(--success)',
            }}>
              {perm}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
