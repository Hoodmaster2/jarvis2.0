import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

export default function Memory() {
  const [memories, setMemories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('');
  const [newMemoryType, setNewMemoryType] = useState('note');
  const [newMemoryContent, setNewMemoryContent] = useState('');

  useEffect(() => {
    loadMemories();
  }, [filterType]);

  const loadMemories = async () => {
    try {
      const data = await api.getMemories(filterType);
      setMemories(data.memories || []);
    } catch (err) {
      console.error('Failed to load memories:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return loadMemories();
    try {
      const data = await api.searchMemory(searchQuery, filterType || null);
      setMemories(data.results || []);
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  const handleCreate = async () => {
    if (!newMemoryContent.trim()) return;
    try {
      await api.createMemory(newMemoryType, newMemoryContent);
      setNewMemoryContent('');
      await loadMemories();
    } catch (err) {
      console.error('Failed to create memory:', err);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.deleteMemory(id);
      setMemories(prev => prev.filter(m => m.id !== id));
    } catch (err) {
      console.error('Failed to delete memory:', err);
    }
  };

  const handleClear = async () => {
    try {
      await api.clearMemory();
      setMemories([]);
    } catch (err) {
      console.error('Failed to clear memory:', err);
    }
  };

  const handleExport = async () => {
    try {
      await api.exportMemory();
    } catch (err) {
      console.error('Failed to export:', err);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Memory</h1>
            <p>JARVIS long-term memory</p>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <button className="btn btn-sm" onClick={handleExport}>Export</button>
            <button className="btn btn-sm btn-danger" onClick={handleClear}>Clear All</button>
          </div>
        </div>
      </div>

      {/* Search & Create */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
        <div className="card" style={{ flex: 1 }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Search</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="text"
              placeholder="Search memories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              style={{ flex: 1 }}
            />
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
              <option value="">All types</option>
              <option value="note">Notes</option>
              <option value="preference">Preferences</option>
              <option value="task">Tasks</option>
              <option value="project">Projects</option>
              <option value="prompt">Prompts</option>
            </select>
            <button className="btn btn-primary btn-sm" onClick={handleSearch}>Search</button>
          </div>
        </div>
        <div className="card" style={{ flex: 1 }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Add Memory</h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <select value={newMemoryType} onChange={(e) => setNewMemoryType(e.target.value)}>
              <option value="note">Note</option>
              <option value="preference">Preference</option>
              <option value="task">Task</option>
              <option value="project">Project</option>
              <option value="prompt">Prompt</option>
            </select>
            <input
              type="text"
              placeholder="Content..."
              value={newMemoryContent}
              onChange={(e) => setNewMemoryContent(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary btn-sm" onClick={handleCreate}>Save</button>
          </div>
        </div>
      </div>

      {/* Memory List */}
      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <p style={{ padding: 20, color: 'var(--text-muted)' }}>Loading memories...</p>
        ) : memories.length === 0 ? (
          <p style={{ padding: 20, color: 'var(--text-muted)' }}>No memories found</p>
        ) : (
          memories.map((mem) => (
            <div key={mem.id} className="memory-item" style={{ position: 'relative' }}>
              <div className="memory-type">{mem.type || 'note'}</div>
              <div className="memory-content">{mem.content}</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="memory-time">
                  {mem.created_at ? new Date(mem.created_at).toLocaleString() : ''}
                </div>
                <button
                  className="btn btn-sm btn-danger"
                  onClick={() => handleDelete(mem.id)}
                  style={{ padding: '2px 8px', fontSize: 11 }}
                >
                  Delete
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
