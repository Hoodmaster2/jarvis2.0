import React, { useState } from 'react';

export default function Browser() {
  const [url, setUrl] = useState('');
  const [screenshot, setScreenshot] = useState(null);
  const [pageContent, setPageContent] = useState('');
  const [status, setStatus] = useState('');

  const handleOpen = async () => {
    if (!url.trim()) return;
    setStatus(`Opening ${url}...`);
    try {
      const res = await fetch('/api/skills/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_name: 'browser_playwright',
          command: 'navigate',
          args: { url },
        }),
      });
      const data = await res.json();
      setStatus(data.result?.status || 'Page opened');
    } catch (err) {
      setStatus(`Error: ${err.message}`);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Browser</h1>
        <p>Playwright web automation</p>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            placeholder="Enter URL..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleOpen()}
            style={{ flex: 1 }}
          />
          <button className="btn btn-primary" onClick={handleOpen}>Open</button>
          <button className="btn" onClick={() => setStatus('Taking screenshot...')}>Screenshot</button>
          <button className="btn" onClick={() => setStatus('Scraping content...')}>Scrape</button>
        </div>
        {status && <p style={{ marginTop: 8, fontSize: 13, color: 'var(--text-secondary)' }}>{status}</p>}
      </div>

      <div className="grid grid-3" style={{ marginBottom: 20 }}>
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Navigation</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <button className="btn btn-sm">Back</button>
            <button className="btn btn-sm">Forward</button>
            <button className="btn btn-sm">Refresh</button>
          </div>
        </div>
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Actions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <button className="btn btn-sm">Click Element</button>
            <button className="btn btn-sm">Fill Form</button>
            <button className="btn btn-sm">Get Text</button>
          </div>
        </div>
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Testing</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <button className="btn btn-sm">Run Audit</button>
            <button className="btn btn-sm">Take Screenshot</button>
            <button className="btn btn-sm">Download File</button>
          </div>
        </div>
      </div>

      {screenshot && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Screenshot</h3>
          <img src={screenshot} alt="Page screenshot" style={{ width: '100%', borderRadius: 8 }} />
        </div>
      )}

      {pageContent && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <h3 style={{ fontSize: 14, fontWeight: 600 }}>Page Content</h3>
            <button className="btn btn-sm" onClick={() => setPageContent('')}>Clear</button>
          </div>
          <pre style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            maxHeight: 300,
            overflow: 'auto',
            background: 'var(--bg-tertiary)',
            padding: 12,
            borderRadius: 8,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}>
            {pageContent}
          </pre>
        </div>
      )}
    </div>
  );
}
