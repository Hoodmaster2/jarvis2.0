import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';
import SkillCard from '../components/SkillCard';

export default function Skills() {
  const [skills, setSkills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [installPath, setInstallPath] = useState('');

  useEffect(() => {
    loadSkills();
  }, []);

  const loadSkills = async () => {
    try {
      const data = await api.getSkills();
      setSkills(data.skills || []);
    } catch (err) {
      console.error('Failed to load skills:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (name, enabled) => {
    try {
      await api.toggleSkill(name, enabled);
      setSkills(prev => prev.map(s =>
        s.name === name ? { ...s, enabled } : s
      ));
    } catch (err) {
      console.error('Failed to toggle skill:', err);
    }
  };

  const handleInstall = async () => {
    if (!installPath.trim()) return;
    try {
      await api.installSkill(installPath);
      setInstallPath('');
      await loadSkills();
    } catch (err) {
      console.error('Failed to install skill:', err);
    }
  };

  const handleUninstall = async (name) => {
    try {
      await api.uninstallSkill(name);
      setSkills(prev => prev.filter(s => s.name !== name));
    } catch (err) {
      console.error('Failed to uninstall skill:', err);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Skills</h1>
            <p>Manage JARVIS capabilities</p>
          </div>
          <button className="btn btn-sm" onClick={loadSkills}>Refresh</button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            type="text"
            placeholder="Path to skill directory..."
            value={installPath}
            onChange={(e) => setInstallPath(e.target.value)}
            style={{ flex: 1 }}
          />
          <button className="btn btn-primary" onClick={handleInstall}>Install</button>
          <button className="btn btn-sm" onClick={api.reloadSkills}>Reload All</button>
        </div>
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-muted)' }}>Loading skills...</p>
      ) : skills.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <p style={{ fontSize: 18, marginBottom: 8 }}>No skills installed</p>
          <p style={{ color: 'var(--text-secondary)' }}>
            Place skill folders in the /skills directory or install from a path above.
          </p>
        </div>
      ) : (
        <div className="grid grid-2">
          {skills.map((skill) => (
            <div key={skill.name} style={{ position: 'relative' }}>
              <SkillCard skill={skill} onToggle={handleToggle} />
              <button
                className="btn btn-sm btn-danger"
                style={{ position: 'absolute', top: 8, right: 56 }}
                onClick={() => handleUninstall(skill.name)}
                title="Uninstall"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
