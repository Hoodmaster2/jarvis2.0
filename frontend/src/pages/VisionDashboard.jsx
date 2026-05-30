import React, { useState, useEffect } from 'react';

export default function VisionDashboard() {
  const [status, setStatus] = useState(null);
  const [screenshots, setScreenshots] = useState([]);
  const [selectedImg, setSelectedImg] = useState(null);
  const [ocrText, setOcrText] = useState('');
  const [analysis, setAnalysis] = useState('');
  const [uiElements, setUiElements] = useState([]);
  const [desktopCtx, setDesktopCtx] = useState(null);
  const [visualMem, setVisualMem] = useState([]);
  const [windows, setWindows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    try {
      const [statRes, ssRes, ctxRes, memRes, winRes] = await Promise.all([
        fetch('/api/vision/status'),
        fetch('/api/vision/screenshots?limit=20'),
        fetch('/api/vision/context'),
        fetch('/api/vision/memory?limit=10'),
        fetch('/api/vision/windows'),
      ]);
      setStatus(await statRes.json());
      setScreenshots((await ssRes.json()).screenshots || []);
      setDesktopCtx((await ctxRes.json()).context || null);
      setVisualMem((await memRes.json()).entries || []);
      setWindows((await winRes.json()).windows || []);
    } catch (err) {
      console.error('Failed to load vision data:', err);
    } finally {
      setLoading(false);
    }
  };

  const captureScreen = async () => {
    const res = await fetch('/api/vision/capture', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: 'full' }),
    });
    const data = await res.json();
    loadAll();
    selectImage(data.id);
  };

  const selectImage = async (id) => {
    setSelectedImg(id);
    setOcrText('');
    setAnalysis('');
    setUiElements([]);
    try {
      const [ocrRes, uiRes] = await Promise.all([
        fetch('/api/vision/ocr', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_path: `${require('os').homedir?.() || ''}\\.jarvis\\screenshots\\${id}.png` }),
        }).catch(() => null),
        fetch('/api/vision/ui-detect', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_path: `...` }),
        }).catch(() => null),
      ]);
      if (ocrRes?.ok) {
        const ocrData = await ocrRes.json();
        setOcrText(ocrData.text || '');
      }
    } catch {}
  };

  const refreshContext = async () => {
    const res = await fetch('/api/vision/context/refresh', { method: 'POST' });
    const data = await res.json();
    setDesktopCtx(data.context);
  };

  const analyzeImage = async (id) => {
    try {
      const res = await fetch('/api/vision/analyze', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_path: `...`, prompt: 'Describe this screenshot in detail.' }),
      });
      const data = await res.json();
      setAnalysis(data.analysis || '');
    } catch {}
  };

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Loading Vision Dashboard...</p>;

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Vision Dashboard</h1>
          <p>Screen capture, OCR, UI detection, and desktop context</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" onClick={captureScreen}>Capture Screen</button>
          <button className="btn" onClick={refreshContext}>Refresh Context</button>
        </div>
      </div>

      <div className="grid grid-4" style={{ marginBottom: 24 }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 24, fontWeight: 700, color: status?.ocr_available ? 'var(--success)' : 'var(--text-muted)' }}>
            {status?.ocr_available ? '✓' : '✗'}
          </p>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>OCR Available</p>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 24, fontWeight: 700 }}>{status?.screenshot_count || 0}</p>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Screenshots</p>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 24, fontWeight: 700 }}>{status?.visual_memory_entries?.total || 0}</p>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Memory Entries</p>
        </div>
        <div className="card" style={{ textAlign: 'center' }}>
          <p style={{ fontSize: 24, fontWeight: 700 }}>{windows.length}</p>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Windows</p>
        </div>
      </div>

      <div className="grid grid-2" style={{ marginBottom: 24 }}>
        {/* Screenshot viewer */}
        <div className="card" style={{ maxHeight: 400, overflow: 'auto' }}>
          <h3 style={{ fontSize: 14, marginBottom: 12 }}>Screenshots</h3>
          {screenshots.length === 0 ? (
            <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>No screenshots yet. Click Capture Screen.</p>
          ) : (
            screenshots.map((ss) => (
              <div key={ss.id} style={{
                padding: 8, cursor: 'pointer', borderBottom: '1px solid var(--border)',
                background: selectedImg === ss.id ? 'var(--bg-hover)' : 'transparent',
              }} onClick={() => selectImage(ss.id)}>
                <p style={{ fontSize: 12, fontWeight: 600 }}>Capture {new Date(ss.timestamp * 1000).toLocaleTimeString()}</p>
                <p style={{ fontSize: 11, color: 'var(--text-muted)' }}>{(ss.size / 1024).toFixed(1)} KB</p>
              </div>
            ))
          )}
        </div>

        {/* Desktop Context */}
        <div className="card">
          <h3 style={{ fontSize: 14, marginBottom: 12 }}>Desktop Context</h3>
          {desktopCtx ? (
            <div>
              <p style={{ fontSize: 12, color: 'var(--accent-primary)' }}>
                Active: {desktopCtx.active_window?.title || 'Unknown'}
              </p>
              {desktopCtx.visible_errors?.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--danger)' }}>Visible Errors:</p>
                  {desktopCtx.visible_errors.map((err, i) => (
                    <p key={i} style={{ fontSize: 11, color: 'var(--warning)', marginTop: 2 }}>{err}</p>
                  ))}
                </div>
              )}
              {desktopCtx.screen_text && (
                <div style={{ marginTop: 8 }}>
                  <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>Screen Text:</p>
                  <pre style={{ fontSize: 11, color: 'var(--text-muted)', whiteSpace: 'pre-wrap', maxHeight: 150, overflow: 'auto' }}>
                    {desktopCtx.screen_text.substring(0, 1000)}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>No context captured. Click Refresh Context.</p>
          )}
        </div>
      </div>

      {/* OCR Results */}
      {selectedImg && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 14, marginBottom: 8 }}>OCR Results</h3>
          {ocrText ? (
            <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto', color: 'var(--text-secondary)' }}>
              {ocrText}
            </pre>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>Run OCR on this screenshot to extract text.</p>
          )}
          <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
            <button className="btn btn-sm btn-primary" onClick={() => analyzeImage(selectedImg)}>Analyze</button>
          </div>
          {analysis && (
            <div style={{ marginTop: 8, padding: 8, background: 'var(--bg-tertiary)', borderRadius: 4 }}>
              <p style={{ fontSize: 13, color: 'var(--text-primary)' }}>{analysis}</p>
            </div>
          )}
        </div>
      )}

      {/* Windows */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Open Windows ({windows.length})</h3>
        {windows.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>Unable to detect windows</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Visible</th>
              </tr>
            </thead>
            <tbody>
              {windows.map((w, i) => (
                <tr key={i}>
                  <td style={{ fontSize: 13 }}>{w.title}</td>
                  <td>
                    <span style={{ color: w.visible !== false ? 'var(--success)' : 'var(--text-muted)' }}>
                      {w.visible !== false ? 'Yes' : 'No'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Visual Memory */}
      <div className="card">
        <h3 style={{ fontSize: 14, marginBottom: 12 }}>Visual Memory</h3>
        {visualMem.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>No visual memories stored</p>
        ) : (
          visualMem.map((entry, i) => (
            <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: 12 }}>
              <p style={{ color: 'var(--text-secondary)' }}>{entry.summary?.substring(0, 200)}</p>
              <p style={{ color: 'var(--text-muted)', fontSize: 11, marginTop: 2 }}>
                {new Date(entry.timestamp * 1000).toLocaleString()}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
