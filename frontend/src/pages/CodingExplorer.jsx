import React, { useState, useEffect } from 'react';

export default function CodingExplorer() {
  const [projectPath, setProjectPath] = useState('');
  const [index, setIndex] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [deps, setDeps] = useState(null);
  const [gitStatus, setGitStatus] = useState(null);
  const [patches, setPatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('files');

  const indexProject = async () => {
    if (!projectPath.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/coding/index', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: projectPath }),
      });
      const data = await res.json();
      setIndex(data);
      setActiveTab('files');
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const searchCode = async () => {
    if (!searchQuery.trim()) return;
    try {
      const res = await fetch('/api/coding/search', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, path: projectPath, limit: 20 }),
      });
      const data = await res.json();
      setSearchResults(data.results || []);
      setActiveTab('search');
    } catch (err) {
      console.error(err);
    }
  };

  const analyzeDeps = async () => {
    try {
      const res = await fetch('/api/coding/deps', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: projectPath }),
      });
      const data = await res.json();
      setDeps(data);
      setActiveTab('deps');
    } catch (err) {
      console.error(err);
    }
  };

  const loadGitStatus = async () => {
    try {
      const res = await fetch(`/api/coding/git/status?path=${encodeURIComponent(projectPath)}`);
      const data = await res.json();
      setGitStatus(data);
      setActiveTab('git');
    } catch (err) {
      console.error(err);
    }
  };

  const loadPatches = async () => {
    try {
      const res = await fetch('/api/coding/patches');
      const data = await res.json();
      setPatches(data.patches || []);
      setActiveTab('patches');
    } catch (err) {
      console.error(err);
    }
  };

  const gitCommit = async () => {
    const msg = prompt('Commit message:');
    if (!msg) return;
    await fetch('/api/coding/git/commit', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: projectPath, message: msg }),
    });
    loadGitStatus();
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="page-header">
        <h1>Code Explorer</h1>
        <p>Repository indexing, semantic search, dependency analysis, and git integration</p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input type="text" placeholder="Path to project folder..." value={projectPath}
            onChange={e => setProjectPath(e.target.value)} onKeyDown={e => e.key === 'Enter' && indexProject()}
            style={{ flex: 1, minWidth: 200 }} />
          <button className="btn btn-primary" onClick={indexProject} disabled={loading}>
            {loading ? 'Indexing...' : 'Index'}
          </button>
          <button className="btn" onClick={analyzeDeps}>Deps</button>
          <button className="btn" onClick={loadGitStatus}>Git</button>
          <button className="btn" onClick={loadPatches}>Patches</button>
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <input type="text" placeholder="Semantic search..." value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && searchCode()}
            style={{ flex: 1 }} />
          <button className="btn btn-sm btn-primary" onClick={searchCode}>Search</button>
        </div>
      </div>

      {/* Tab navigation */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
        {['files', 'search', 'deps', 'git', 'patches'].map(tab => (
          <button key={tab} className={`btn btn-sm ${activeTab === tab ? 'btn-primary' : ''}`}
            onClick={() => setActiveTab(tab)}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
        {/* Files tab */}
        {activeTab === 'files' && index && (
          <div className="card">
            <h3 style={{ fontSize: 14, marginBottom: 8 }}>{index.name}</h3>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
              {index.file_count} files, {index.total_lines} lines, {Object.keys(index.languages || {}).length} languages
            </p>
            {index.has_git && <p style={{ fontSize: 12, color: 'var(--accent-primary)', marginBottom: 8 }}>Git: {index.git_branch}</p>}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 12 }}>
              {Object.entries(index.languages || {}).map(([ext, count]) => (
                <span key={ext} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, background: 'var(--bg-hover)', color: 'var(--accent-primary)' }}>
                  {ext}: {count}
                </span>
              ))}
            </div>
            <div style={{ maxHeight: 400, overflow: 'auto' }}>
              {(index.files || []).map((f, i) => (
                <div key={i} style={{ display: 'flex', gap: 8, padding: '3px 0', fontSize: 12, borderBottom: '1px solid var(--border)' }}>
                  <span style={{ color: 'var(--text-muted)', width: 60, textAlign: 'right' }}>{f.lines} lines</span>
                  <span style={{ color: 'var(--text-primary)' }}>{f.path}</span>
                  <span style={{ color: 'var(--text-muted)' }}>{f.ext}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {activeTab === 'files' && !index && (
          <div className="card" style={{ textAlign: 'center', padding: 40 }}>
            <p style={{ color: 'var(--text-muted)' }}>Index a project to view files</p>
          </div>
        )}

        {/* Search tab */}
        {activeTab === 'search' && (
          <div className="card">
            {searchResults.length === 0 ? (
              <p style={{ color: 'var(--text-muted)' }}>Search for code to see results</p>
            ) : (
              searchResults.map((r, i) => (
                <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                  <span style={{ color: 'var(--accent-primary)' }}>{r.path}</span>
                  <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>Score: {r.score}</span>
                  <p style={{ color: 'var(--text-secondary)', fontSize: 12, marginTop: 2 }}>{(r.content || '').substring(0, 200)}</p>
                </div>
              ))
            )}
          </div>
        )}

        {/* Deps tab */}
        {activeTab === 'deps' && deps && (
          <div className="grid grid-2">
            {deps.python && (
              <div className="card">
                <h3 style={{ fontSize: 14, marginBottom: 8 }}>Python</h3>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>Imports: {(deps.python.imports || []).length}</p>
                {deps.python.third_party?.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--warning)' }}>Third-party:</p>
                    {(deps.python.third_party || []).map((d, i) => (
                      <span key={i} style={{ fontSize: 11, padding: '1px 6px', borderRadius: 4, background: 'var(--bg-hover)', margin: 2, display: 'inline-block' }}>{d}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
            {deps.node && (
              <div className="card">
                <h3 style={{ fontSize: 14, marginBottom: 8 }}>Node.js</h3>
                {deps.node.dependencies?.length > 0 && (
                  <div>
                    <p style={{ fontSize: 12, fontWeight: 600 }}>Dependencies:</p>
                    {(deps.node.dependencies || []).map((d, i) => (
                      <span key={i} style={{ fontSize: 11, padding: '1px 6px', borderRadius: 4, background: 'var(--bg-hover)', margin: 2, display: 'inline-block' }}>{d}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Git tab */}
        {activeTab === 'git' && gitStatus && (
          <div className="card">
            {gitStatus.error ? (
              <p style={{ color: 'var(--warning)' }}>{gitStatus.error}</p>
            ) : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div>
                    <p style={{ fontSize: 14, fontWeight: 600 }}>Branch: {gitStatus.branch}</p>
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {gitStatus.modified?.length || 0} modified, {gitStatus.staged?.length || 0} staged, {gitStatus.untracked?.length || 0} untracked
                    </p>
                  </div>
                  <button className="btn btn-sm btn-primary" onClick={gitCommit}>Commit</button>
                </div>
                {gitStatus.modified?.length > 0 && (
                  <div style={{ marginBottom: 8 }}>
                    <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--warning)' }}>Modified:</p>
                    {gitStatus.modified.map((f, i) => (
                      <div key={i} style={{ fontSize: 12, padding: '2px 0', color: 'var(--text-secondary)' }}>{f}</div>
                    ))}
                  </div>
                )}
                {gitStatus.untracked?.length > 0 && (
                  <div>
                    <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)' }}>Untracked:</p>
                    {gitStatus.untracked.map((f, i) => (
                      <div key={i} style={{ fontSize: 12, padding: '2px 0', color: 'var(--text-secondary)' }}>{f}</div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* Patches tab */}
        {activeTab === 'patches' && (
          <div>
            {patches.length === 0 ? (
              <div className="card" style={{ textAlign: 'center', padding: 40 }}>
                <p style={{ color: 'var(--text-muted)' }}>No pending patches</p>
              </div>
            ) : (
              patches.map((p, i) => (
                <div className="card" key={i} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div>
                      <span style={{ fontWeight: 600, fontSize: 14 }}>{p.file_path?.split('/').pop() || p.file_path?.split('\\').pop()}</span>
                      <span style={{ color: 'var(--text-muted)', fontSize: 12, marginLeft: 8 }}>{p.id?.substring(0, 8)}</span>
                    </div>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn btn-sm btn-primary"
                        onClick={async () => { await fetch(`/api/coding/patches/${p.id}/approve`, { method: 'POST' }); loadPatches(); }}>
                        Approve
                      </button>
                      <button className="btn btn-sm" style={{ borderColor: 'var(--success)', color: 'var(--success)' }}
                        onClick={async () => { await fetch(`/api/coding/patches/${p.id}/apply`, { method: 'POST' }); loadPatches(); }}>
                        Apply
                      </button>
                    </div>
                  </div>
                  <pre style={{ fontSize: 11, background: 'var(--bg-tertiary)', padding: 8, borderRadius: 4, overflow: 'auto', maxHeight: 200 }}>
                    {p.diff || p.description || 'No diff available'}
                  </pre>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
