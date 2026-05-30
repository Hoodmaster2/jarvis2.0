import React, { useState, useEffect } from 'react';

export default function Files() {
  const [currentPath, setCurrentPath] = useState('C:\\');
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFiles();
  }, [currentPath]);

  const loadFiles = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/skills/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_name: 'file_manager',
          command: 'list',
          args: { path: currentPath },
        }),
      });
      const data = await res.json();
      setFiles(data.result?.files || []);
    } catch (err) {
      console.error('Failed to load files:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleNavigate = (path) => {
    setCurrentPath(path);
  };

  const handleGoUp = () => {
    const parent = currentPath.endsWith('\\')
      ? currentPath.slice(0, -1).split('\\').slice(0, -1).join('\\') + '\\'
      : currentPath.split('\\').slice(0, -1).join('\\') + '\\';
    setCurrentPath(parent);
  };

  const getFileIcon = (name, isDir) => {
    if (isDir) return '📁';
    const ext = name.split('.').pop().toLowerCase();
    const icons = {
      txt: '📄', md: '📝', json: '📋', js: '📜', py: '🐍',
      html: '🌐', css: '🎨', jsx: '⚛️', tsx: '⚛️', ts: '📘',
      exe: '⚙️', dll: '🔧', ps1: '🖥️', bat: '🖥️',
      png: '🖼️', jpg: '🖼️', jpeg: '🖼️', gif: '🖼️',
      pdf: '📕', doc: '📘', docx: '📘', xlsx: '📊',
      zip: '📦', rar: '📦', '7z': '📦',
    };
    return icons[ext] || '📄';
  };

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Files</h1>
            <p>Browse and manage files</p>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            <button className="btn btn-sm" onClick={handleGoUp}>↑ Up</button>
            <button className="btn btn-sm" onClick={loadFiles}>Refresh</button>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ color: 'var(--text-muted)' }}>📍</span>
          <input
            type="text"
            value={currentPath}
            onChange={(e) => setCurrentPath(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && loadFiles()}
            style={{ flex: 1, fontFamily: 'var(--font-mono)', fontSize: 12 }}
          />
          <button className="btn btn-sm btn-primary" onClick={loadFiles}>Go</button>
        </div>
      </div>

      {loading ? (
        <p style={{ color: 'var(--text-muted)' }}>Loading...</p>
      ) : (
        <div className="card" style={{ padding: 4 }}>
          <div className="file-list">
            {files.map((file, i) => (
              <div
                key={i}
                className="file-item"
                onClick={() => file.is_dir && handleNavigate(file.path)}
                style={{ cursor: file.is_dir ? 'pointer' : 'default' }}
              >
                <span className="file-icon">{getFileIcon(file.name, file.is_dir)}</span>
                <span className="file-name" style={{ fontWeight: file.is_dir ? 600 : 400 }}>
                  {file.name}
                </span>
                {!file.is_dir && file.size != null && (
                  <span className="file-size">
                    {file.size < 1024 ? `${file.size} B` :
                     file.size < 1048576 ? `${(file.size/1024).toFixed(1)} KB` :
                     `${(file.size/1048576).toFixed(1)} MB`}
                  </span>
                )}
                {file.modified && (
                  <span className="file-size">{new Date(file.modified).toLocaleDateString()}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
