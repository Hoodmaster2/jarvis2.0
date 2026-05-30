import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

export default function HybridMemory() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterProject, setFilterProject] = useState('');
  const [projects, setProjects] = useState([]);
  const [categories, setCategories] = useState({});
  const [newType, setNewType] = useState('note');
  const [newContent, setNewContent] = useState('');
  const [newProject, setNewProject] = useState('');
  const [tab, setTab] = useState('browse');
  const [timeline, setTimeline] = useState([]);

  useEffect(() => {
    loadEntries();
    loadProjects();
    loadCategories();
  }, [filterType, filterProject]);

  const loadEntries = async () => {
    setLoading(true);
    try {
      const data = await api.getHybridMemory(filterType, filterProject);
      setEntries(data.entries || []);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const loadProjects = async () => {
    try {
      const data = await api.getHybridMemoryProjects();
      setProjects(data.projects || []);
    } catch (e) { console.error(e); }
  };

  const loadCategories = async () => {
    try {
      const data = await api.getHybridMemoryCategories();
      setCategories(data.categories || {});
    } catch (e) { console.error(e); }
  };

  const loadTimeline = async (days = 7) => {
    try {
      const data = await api.getHybridMemoryTimeline(days, filterType);
      setTimeline(data.entries || []);
    } catch (e) { console.error(e); }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return loadEntries();
    try {
      const data = await api.searchHybridMemory(searchQuery, filterType || null);
      setEntries(data.results || []);
    } catch (e) { console.error(e); }
  };

  const addEntry = async () => {
    if (!newContent.trim()) return;
    try {
      await api.addHybridMemory(newType, newContent, {}, filterProject || undefined);
      setNewContent('');
      loadEntries();
      loadCategories();
    } catch (e) { console.error(e); }
  };

  const deleteEntry = async (id) => {
    try {
      await api.deleteHybridMemory(id);
      setEntries(entries.filter(e => e.id !== id));
      loadCategories();
    } catch (e) { console.error(e); }
  };

  const exportMemory = async () => {
    try {
      const data = await api.exportHybridMemory(filterType, filterProject);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `memory-export-${Date.now()}.json`;
      a.click();
    } catch (e) { console.error(e); }
  };

  const clearMemory = async () => {
    if (!window.confirm('Clear all hybrid memory entries?')) return;
    try {
      await api.clearHybridMemory(filterType);
      loadEntries();
      loadCategories();
    } catch (e) { console.error(e); }
  };

  const typeColors = {
    preference: '#6366f1', project: '#8b5cf6', task: '#ec4899',
    tool_usage: '#f59e0b', coding_fix: '#10b981', website_note: '#06b6d4',
    automation: '#3b82f6', skill_behavior: '#8b5cf6', episodic: '#6366f1',
    procedural: '#14b8a6', conversation: '#6b7280',
  };

  return (
    <div className="page">
      <h1>Hybrid Long-Term Memory</h1>

      <div className="tab-bar">
        <button className={tab === 'browse' ? 'active' : ''} onClick={() => setTab('browse')}>Browse</button>
        <button className={tab === 'search' ? 'active' : ''} onClick={() => setTab('search')}>Search</button>
        <button className={tab === 'add' ? 'active' : ''} onClick={() => setTab('add')}>Add Memory</button>
        <button className={tab === 'timeline' ? 'active' : ''} onClick={() => setTab('timeline')}>Timeline</button>
        <button className={tab === 'settings' ? 'active' : ''} onClick={() => setTab('settings')}>Settings</button>
      </div>

      {tab === 'browse' && (
        <div className="card">
          <div className="row">
            <select value={filterType} onChange={e => setFilterType(e.target.value)}>
              <option value="">All Types</option>
              {Object.keys(categories).map(t => (
                <option key={t} value={t}>{t} ({categories[t]})</option>
              ))}
            </select>
            <select value={filterProject} onChange={e => setFilterProject(e.target.value)}>
              <option value="">All Projects</option>
              {projects.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <button onClick={loadEntries}>Refresh</button>
          </div>
          {loading ? <p>Loading...</p> : (
            <table>
              <thead><tr><th>Type</th><th>Content</th><th>Project</th><th>Imp</th><th>Date</th><th>Actions</th></tr></thead>
              <tbody>
                {entries.map(e => (
                  <tr key={e.id}>
                    <td><span className="tag" style={{ background: typeColors[e.type] || '#6b7280' }}>{e.type}</span></td>
                    <td className="mono">{e.content?.slice(0, 120)}</td>
                    <td>{e.project || '-'}</td>
                    <td>{'⭐'.repeat(e.importance || 1)}</td>
                    <td className="mono small">{new Date(e.created_at).toLocaleDateString()}</td>
                    <td><button onClick={() => deleteEntry(e.id)}>Delete</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === 'search' && (
        <div className="card">
          <div className="row">
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Semantic search..."
              className="flex-1"
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <button onClick={handleSearch}>Search</button>
          </div>
          {entries.map(e => (
            <div key={e.id} className="memory-entry">
              <span className="tag" style={{ background: typeColors[e.type] || '#6b7280' }}>{e.type}</span>
              {e.score !== undefined && <span className="tag bg-blue">{(e.score * 100).toFixed(0)}% match</span>}
              <p>{e.content}</p>
              <small className="muted">{e.project && `Project: ${e.project}`} {e.created_at && new Date(e.created_at).toLocaleString()}</small>
            </div>
          ))}
        </div>
      )}

      {tab === 'add' && (
        <div className="card">
          <div className="form-group">
            <label>Type</label>
            <select value={newType} onChange={e => setNewType(e.target.value)}>
              {['note', 'preference', 'project', 'task', 'tool_usage', 'coding_fix', 'website_note', 'automation', 'skill_behavior', 'episodic', 'procedural'].map(t => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Content</label>
            <textarea value={newContent} onChange={e => setNewContent(e.target.value)} rows={4} placeholder="Memory content..." />
          </div>
          <div className="form-group">
            <label>Project (optional)</label>
            <input value={newProject} onChange={e => setNewProject(e.target.value)} placeholder="Project name" />
          </div>
          <button onClick={addEntry}>Save Memory</button>
        </div>
      )}

      {tab === 'timeline' && (
        <div className="card">
          <div className="row">
            <button onClick={() => loadTimeline(1)}>24h</button>
            <button onClick={() => loadTimeline(7)}>7 days</button>
            <button onClick={() => loadTimeline(30)}>30 days</button>
            <button onClick={() => loadTimeline(90)}>90 days</button>
          </div>
          {timeline.map(e => (
            <div key={e.id} className="memory-entry">
              <span className="tag" style={{ background: typeColors[e.type] || '#6b7280' }}>{e.type}</span>
              <p>{e.content?.slice(0, 200)}</p>
              <small className="muted">{new Date(e.created_at).toLocaleString()}</small>
            </div>
          ))}
        </div>
      )}

      {tab === 'settings' && (
        <div className="card">
          <h3>Memory Controls</h3>
          <div className="form-group">
            <button onClick={exportMemory}>Export Memory</button>
            <button onClick={clearMemory} className="btn-danger">Clear Memory</button>
          </div>
          <h4>Category Breakdown</h4>
          <div className="stats-grid">
            {Object.entries(categories).map(([k, v]) => (
              <div key={k} className="stat-card">
                <span className="tag" style={{ background: typeColors[k] || '#6b7280' }}>{k}</span>
                <span className="stat-value">{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
