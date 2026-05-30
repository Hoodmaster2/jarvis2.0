import React, { useState, useEffect } from 'react';

export default function MCPMarketplace() {
  const [servers, setServers] = useState([]);
  const [tools, setTools] = useState([]);
  const [discoverable, setDiscoverable] = useState({});
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', command: '', args: '', transport: 'stdio', url: '', trusted: false });

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    try {
      const [sRes, tRes, dRes] = await Promise.all([
        fetch('/api/mcp/servers'),
        fetch('/api/mcp/tools'),
        fetch('/api/mcp/discover'),
      ]);
      setServers((await sRes.json()).servers || []);
      setTools((await tRes.json()).tools || []);
      setDiscoverable((await dRes.json()).common || {});
    } catch (err) {
      console.error('Failed to load MCP data:', err);
    } finally {
      setLoading(false);
    }
  };

  const connectServer = async (name) => {
    await fetch('/api/mcp/servers/connect', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    loadAll();
  };

  const disconnectServer = async (name) => {
    await fetch('/api/mcp/servers/disconnect', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    loadAll();
  };

  const trustServer = async (name) => {
    await fetch(`/api/mcp/servers/${name}/trust`, { method: 'POST' });
    loadAll();
  };

  const untrustServer = async (name) => {
    await fetch(`/api/mcp/servers/${name}/untrust`, { method: 'POST' });
    loadAll();
  };

  const removeServer = async (name) => {
    await fetch(`/api/mcp/servers/${name}`, { method: 'DELETE' });
    loadAll();
  };

  const installDiscovered = async (type) => {
    await fetch('/api/mcp/discover/install', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type }),
    });
    loadAll();
  };

  const registerServer = async () => {
    await fetch('/api/mcp/servers/register', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: { ...form, args: form.args.split(' ').filter(Boolean) },
    });
    setShowForm(false);
    setForm({ name: '', command: '', args: '', transport: 'stdio', url: '', trusted: false });
    loadAll();
  };

  const statusColor = (status) => {
    switch (status) {
      case 'connected': return 'var(--success)';
      case 'connecting': return 'var(--warning)';
      case 'error': return 'var(--danger)';
      default: return 'var(--text-muted)';
    }
  };

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Loading MCP Marketplace...</p>;

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>MCP Marketplace</h1>
          <p>Model Context Protocol — connect external tools and servers</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ Add Server'}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, marginBottom: 12 }}>Register MCP Server</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input placeholder="Server name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
            <input placeholder="Command (e.g., npx)" value={form.command} onChange={e => setForm({ ...form, command: e.target.value })} />
            <input placeholder="Args (space separated)" value={form.args} onChange={e => setForm({ ...form, args: e.target.value })} />
            <select value={form.transport} onChange={e => setForm({ ...form, transport: e.target.value })}>
              <option value="stdio">Stdio</option>
              <option value="websocket">WebSocket</option>
            </select>
            {form.transport === 'websocket' && (
              <input placeholder="WebSocket URL" value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} />
            )}
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
              <input type="checkbox" checked={form.trusted} onChange={e => setForm({ ...form, trusted: e.target.checked })} />
              Trust this server (skip permission checks)
            </label>
            <button className="btn btn-primary" onClick={registerServer}>Register</button>
          </div>
        </div>
      )}

      {/* Connected Servers */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Connected Servers ({servers.length})</h2>
        {servers.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No servers registered. Add one above or install a common server below.</p>
        ) : (
          servers.map((srv, i) => (
            <div key={i} style={{ borderBottom: '1px solid var(--border)', padding: '12px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{srv.name}</span>
                  <span style={{ display: 'inline-block', marginLeft: 8, width: 10, height: 10, borderRadius: '50%', background: statusColor(srv.status) }} />
                  <span style={{ color: 'var(--text-muted)', fontSize: 12, marginLeft: 4 }}>{srv.status}</span>
                  <span style={{ color: 'var(--text-secondary)', fontSize: 12, marginLeft: 8 }}>{srv.transport}</span>
                  {srv.trusted && <span style={{ color: 'var(--success)', fontSize: 12, marginLeft: 8 }}>✓ Trusted</span>}
                </div>
                <div style={{ display: 'flex', gap: 4 }}>
                  {srv.status === 'connected' ? (
                    <button className="btn btn-sm" onClick={() => disconnectServer(srv.name)}>Disconnect</button>
                  ) : (
                    <button className="btn btn-sm btn-primary" onClick={() => connectServer(srv.name)}>Connect</button>
                  )}
                  {srv.trusted ? (
                    <button className="btn btn-sm" onClick={() => untrustServer(srv.name)}>Untrust</button>
                  ) : (
                    <button className="btn btn-sm" onClick={() => trustServer(srv.name)}>Trust</button>
                  )}
                  <button className="btn btn-sm btn-danger" onClick={() => removeServer(srv.name)}>Remove</button>
                </div>
              </div>
              {srv.tools?.length > 0 && (
                <div style={{ marginTop: 8, marginLeft: 16 }}>
                  <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>
                    Tools ({srv.tools.length}):
                  </p>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                    {srv.tools.map((t, j) => (
                      <span key={j} style={{ fontSize: 11, padding: '2px 6px', borderRadius: 4, background: 'var(--bg-hover)', color: 'var(--accent-primary)' }}>
                        {t.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {srv.error && <p style={{ color: 'var(--danger)', fontSize: 12, marginTop: 4 }}>Error: {srv.error}</p>}
            </div>
          ))
        )}
      </div>

      {/* Tools */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>All MCP Tools ({tools.length})</h2>
        {tools.length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No tools available from connected servers</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Tool</th>
                <th>Server</th>
                <th>Description</th>
                <th>Permission</th>
              </tr>
            </thead>
            <tbody>
              {tools.map((t, i) => (
                <tr key={i}>
                  <td style={{ fontWeight: 600 }}>{t.name}</td>
                  <td><code style={{ fontSize: 12 }}>{t.server_name}</code></td>
                  <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{t.description}</td>
                  <td><span style={{ fontSize: 11, padding: '1px 6px', borderRadius: 4, background: t.permission_level === 'high' ? 'var(--warning)' : 'var(--text-muted)', color: '#fff' }}>{t.permission_level}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Discoverable */}
      <div className="card">
        <h2 style={{ fontSize: 16, marginBottom: 12 }}>Discoverable Common Servers</h2>
        {Object.keys(discoverable).length === 0 ? (
          <p style={{ color: 'var(--text-muted)' }}>No discoverable servers</p>
        ) : (
          Object.entries(discoverable).map(([key, info]) => (
            <div key={key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
              <div>
                <span style={{ fontWeight: 600, fontSize: 14 }}>{key}</span>
                <span style={{ color: 'var(--text-secondary)', fontSize: 12, marginLeft: 8 }}>
                  {info.config?.command || info.config?.url}
                </span>
                {info.registered && <span style={{ color: 'var(--text-muted)', fontSize: 12, marginLeft: 8 }}>(registered)</span>}
              </div>
              {!info.registered ? (
                <button className="btn btn-sm btn-primary" onClick={() => installDiscovered(key)}>
                  Install & Connect
                </button>
              ) : (
                <span style={{ color: 'var(--success)', fontSize: 12 }}>Installed</span>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
