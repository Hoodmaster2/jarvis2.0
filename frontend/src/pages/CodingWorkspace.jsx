import React, { useState } from 'react';

export default function CodingWorkspace() {
  const [projectPath, setProjectPath] = useState('');
  const [files, setFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [output, setOutput] = useState('');
  const [loading, setLoading] = useState(false);

  const openProject = async () => {
    if (!projectPath.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/skills/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_name: 'code_editor',
          command: 'list_files',
          args: { path: projectPath },
        }),
      });
      const data = await res.json();
      setFiles(data.result?.files || []);
      setOutput(`Opened project: ${projectPath}`);
    } catch (err) {
      setOutput(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const openFile = async (filePath) => {
    setActiveFile(filePath);
    try {
      const res = await fetch('/api/skills/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_name: 'code_editor',
          command: 'read_file',
          args: { path: filePath },
        }),
      });
      const data = await res.json();
      setFileContent(data.result?.content || '// File not found');
    } catch (err) {
      setFileContent(`// Error: ${err.message}`);
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div className="page-header">
        <h1>Coding Workspace</h1>
        <p>AI-assisted coding environment</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            placeholder="Path to project folder..."
            value={projectPath}
            onChange={(e) => setProjectPath(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && openProject()}
            style={{ flex: 1 }}
          />
          <button className="btn btn-primary" onClick={openProject}>Open Project</button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 16, flex: 1, overflow: 'hidden' }}>
        {/* File Explorer */}
        <div className="card" style={{ width: 250, flexShrink: 0, overflow: 'auto' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Files</h3>
          {files.length === 0 ? (
            <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>No project opened</p>
          ) : (
            <div className="file-list">
              {files.map((f, i) => (
                <div
                  key={i}
                  className="file-item"
                  onClick={() => openFile(f.path)}
                  style={{
                    cursor: 'pointer',
                    background: activeFile === f.path ? 'var(--bg-hover)' : 'transparent',
                  }}
                >
                  <span className="file-icon">
                    {f.is_dir ? '📁' : '📄'}
                  </span>
                  <span className="file-name">{f.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Editor */}
        <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <h3 style={{ fontSize: 13, fontWeight: 600 }}>
              {activeFile ? activeFile.split('\\').pop() : 'No file selected'}
            </h3>
            <div style={{ display: 'flex', gap: 4 }}>
              <button className="btn btn-sm" onClick={() => setOutput('Suggesting changes...')}>Suggest</button>
              <button className="btn btn-sm" onClick={() => setOutput('Debugging...')}>Debug</button>
              <button className="btn btn-sm" onClick={() => setOutput('Running tests...')}>Test</button>
            </div>
          </div>
          <textarea
            value={fileContent}
            onChange={(e) => setFileContent(e.target.value)}
            style={{
              flex: 1,
              fontFamily: 'var(--font-mono)',
              fontSize: 13,
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: 12,
              color: 'var(--text-primary)',
              resize: 'none',
              outline: 'none',
              tabSize: 2,
            }}
            spellCheck={false}
          />
        </div>

        {/* Output */}
        <div className="card" style={{ width: 300, flexShrink: 0, overflow: 'auto' }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Output</h3>
          <pre style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            whiteSpace: 'pre-wrap',
            color: 'var(--text-secondary)',
          }}>
            {output || 'Ready'}
          </pre>
        </div>
      </div>
    </div>
  );
}
