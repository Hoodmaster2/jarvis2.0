import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

export default function BrowserWorker() {
  const [sessions, setSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [pageInfo, setPageInfo] = useState(null);
  const [url, setUrl] = useState('');
  const [actionHistory, setActionHistory] = useState([]);
  const [screenshotUrl, setScreenshotUrl] = useState('');
  const [headless, setHeadless] = useState(false);
  const [loading, setLoading] = useState(false);
  const [tab, setTab] = useState('sessions');
  const [scrapeSelectors, setScrapeSelectors] = useState('');
  const [scrapeResult, setScrapeResult] = useState('');
  const [summary, setSummary] = useState('');

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const data = await api.getBrowserSessions();
      setSessions(data.sessions || []);
    } catch (e) { console.error(e); }
  };

  const createSession = async () => {
    setLoading(true);
    try {
      const data = await api.createBrowserSession(headless);
      setSelectedSession(data.session_id);
      await loadSessions();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const closeSession = async (sid) => {
    try {
      await api.closeBrowserSession(sid);
      if (selectedSession === sid) setSelectedSession(null);
      await loadSessions();
    } catch (e) { console.error(e); }
  };

  const gotoUrl = async () => {
    if (!selectedSession || !url) return;
    setLoading(true);
    try {
      const data = await api.browserGoto(selectedSession, url);
      setPageInfo(data.page_info);
      await loadHistory();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const takeScreenshot = async () => {
    if (!selectedSession) return;
    try {
      const blob = await api.browserScreenshot(selectedSession);
      const url = URL.createObjectURL(blob);
      setScreenshotUrl(url);
    } catch (e) { console.error(e); }
  };

  const loadPageInfo = async () => {
    if (!selectedSession) return;
    try {
      const data = await api.browserPageInfo(selectedSession);
      setPageInfo(data);
    } catch (e) { console.error(e); }
  };

  const loadHistory = async () => {
    try {
      const data = await api.browserActionHistory(selectedSession);
      setActionHistory(data.actions || []);
    } catch (e) { console.error(e); }
  };

  const summarizePage = async () => {
    if (!selectedSession) return;
    try {
      const data = await api.browserSummarize(selectedSession);
      setSummary(data.summary || '');
    } catch (e) { console.error(e); }
  };

  const scrapePage = async () => {
    if (!selectedSession) return;
    try {
      const selectors = scrapeSelectors ? scrapeSelectors.split(',').map(s => s.trim()) : null;
      const data = await api.browserScrape(selectedSession, selectors);
      setScrapeResult(JSON.stringify(data, null, 2));
    } catch (e) { console.error(e); }
  };

  const testLinks = async () => {
    if (!selectedSession) return;
    try {
      const data = await api.browserTestLinks(selectedSession);
      setScrapeResult(JSON.stringify(data, null, 2));
    } catch (e) { console.error(e); }
  };

  const runSeoAudit = async () => {
    if (!selectedSession) return;
    try {
      const data = await api.browserSeoAudit(selectedSession);
      setScrapeResult(JSON.stringify(data, null, 2));
    } catch (e) { console.error(e); }
  };

  return (
    <div className="page">
      <h1>Browser Worker</h1>

      <div className="toolbar">
        <button onClick={createSession} disabled={loading}>
          {loading ? 'Creating...' : 'New Session'}
        </button>
        <label>
          <input type="checkbox" checked={headless} onChange={e => setHeadless(e.target.checked)} />
          Headless
        </label>
        <button onClick={loadSessions}>Refresh</button>
      </div>

      <div className="tab-bar">
        <button className={tab === 'sessions' ? 'active' : ''} onClick={() => setTab('sessions')}>Sessions</button>
        <button className={tab === 'browser' ? 'active' : ''} onClick={() => setTab('browser')}>Browser</button>
        <button className={tab === 'history' ? 'active' : ''} onClick={() => setTab('history')}>History</button>
        <button className={tab === 'tools' ? 'active' : ''} onClick={() => setTab('tools')}>Tools</button>
      </div>

      {tab === 'sessions' && (
        <div className="card">
          <h3>Sessions ({sessions.length})</h3>
          {sessions.length === 0 ? (
            <p className="muted">No active sessions. Create one to begin.</p>
          ) : (
            <table>
              <thead><tr><th>ID</th><th>Pages</th><th>Active</th><th>Created</th><th>Actions</th></tr></thead>
              <tbody>
                {sessions.map(s => (
                  <tr key={s.id} className={selectedSession === s.id ? 'selected' : ''}>
                    <td>{s.id}</td>
                    <td>{s.pages}</td>
                    <td>{s.active_page?.slice(0, 8)}</td>
                    <td>{new Date(s.created).toLocaleString()}</td>
                    <td>
                      <button onClick={() => setSelectedSession(s.id)}>Select</button>
                      <button onClick={() => closeSession(s.id)}>Close</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === 'browser' && selectedSession && (
        <>
          <div className="card">
            <div className="row">
              <input value={url} onChange={e => setUrl(e.target.value)} placeholder="https://example.com" className="flex-1" />
              <button onClick={gotoUrl} disabled={loading}>Go</button>
              <button onClick={loadPageInfo}>Refresh</button>
              <button onClick={takeScreenshot}>Screenshot</button>
              <button onClick={summarizePage}>Summarize</button>
            </div>
          </div>

          {pageInfo && (
            <div className="card">
              <h3>Page: {pageInfo.title}</h3>
              <p className="mono">{pageInfo.url}</p>
              <details>
                <summary>Visible Text</summary>
                <pre className="pre-wrap">{pageInfo.visible_text}</pre>
              </details>
            </div>
          )}

          {screenshotUrl && (
            <div className="card">
              <h3>Screenshot</h3>
              <img src={screenshotUrl} alt="Page screenshot" className="screenshot-preview" />
            </div>
          )}

          {summary && (
            <div className="card">
              <h3>Summary</h3>
              <p>{summary}</p>
            </div>
          )}
        </>
      )}

      {tab === 'browser' && !selectedSession && (
        <div className="card"><p className="muted">Select a session from the Sessions tab first.</p></div>
      )}

      {tab === 'history' && (
        <div className="card">
          <h3>Action History</h3>
          <button onClick={loadHistory}>Refresh</button>
          {actionHistory.length === 0 ? (
            <p className="muted">No actions recorded yet.</p>
          ) : (
            <table>
              <thead><tr><th>Time</th><th>Action</th><th>Params</th><th>Result</th></tr></thead>
              <tbody>
                {actionHistory.slice().reverse().map((a, i) => (
                  <tr key={i}>
                    <td className="mono">{new Date(a.timestamp).toLocaleTimeString()}</td>
                    <td><span className="tag">{a.action}</span></td>
                    <td className="mono small">{JSON.stringify(a.params).slice(0, 60)}</td>
                    <td className="mono small">{JSON.stringify(a.result).slice(0, 60)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === 'tools' && selectedSession && (
        <div className="card">
          <h3>Browser Tools</h3>
          <div className="card">
            <h4>Safe Scrape</h4>
            <div className="row">
              <input value={scrapeSelectors} onChange={e => setScrapeSelectors(e.target.value)} placeholder="body, h1, .content (comma-separated)" className="flex-1" />
              <button onClick={scrapePage}>Scrape</button>
              <button onClick={testLinks}>Test Links</button>
              <button onClick={runSeoAudit}>SEO Audit</button>
            </div>
            {scrapeResult && <pre className="pre-wrap">{scrapeResult}</pre>}
          </div>
        </div>
      )}
    </div>
  );
}
