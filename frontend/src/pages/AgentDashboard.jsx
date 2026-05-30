import React, { useState, useEffect, useCallback } from 'react';

const API = '/api';

export default function AgentDashboard() {
  const [agents, setAgents] = useState({});
  const [graphs, setGraphs] = useState([]);
  const [routing, setRouting] = useState({});
  const [coordStatus, setCoordStatus] = useState({});
  const [events, setEvents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [selectedGraph, setSelectedGraph] = useState(null);
  const [dagData, setDagData] = useState(null);
  const [tab, setTab] = useState('agents');
  const [loading, setLoading] = useState(true);
  const [requestInput, setRequestInput] = useState('');

  const fetchAll = useCallback(async () => {
    try {
      const [aRes, gRes, rRes, cRes] = await Promise.all([
        fetch(`${API}/agents`).then(r => r.json()),
        fetch(`${API}/graphs?limit=10`).then(r => r.json()),
        fetch(`${API}/models/routing`).then(r => r.json()),
        fetch(`${API}/coordinator/status`).then(r => r.json()),
      ]);
      setAgents(aRes.agents || {});
      setGraphs(gRes.graphs || []);
      setRouting(rRes.routing || {});
      setCoordStatus(cRes || {});
    } catch (err) {
      console.error('Failed to fetch agent data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const fetchEvents = async () => {
    try {
      const res = await fetch(`${API}/coordinator/events?limit=50`);
      const data = await res.json();
      setEvents(data.events || []);
    } catch {}
  };

  const fetchDag = async (graphId) => {
    try {
      const res = await fetch(`${API}/graphs/${graphId}/dag`);
      const data = await res.json();
      setDagData(data);
      setSelectedGraph(graphId);
    } catch {}
  };

  const submitRequest = async () => {
    if (!requestInput.trim()) return;
    try {
      await fetch(`${API}/graphs/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request: requestInput }),
      });
      setRequestInput('');
      fetchAll();
    } catch (err) {
      console.error('Failed to submit request:', err);
    }
  };

  const cancelGraph = async (graphId) => {
    try {
      await fetch(`${API}/graphs/${graphId}/cancel`, { method: 'POST' });
      fetchAll();
    } catch {}
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: '#606080', running: '#00d4ff', completed: '#44ff88',
      failed: '#ff4444', skipped: '#9090b0', cancelled: '#ffaa44', blocked: '#ff6600',
      idle: '#44ff88', planning: '#00d4ff', executing: '#ffaa44', waiting: '#9090b0',
    };
    return colors[status] || '#606080';
  };

  const getAgentIcon = (name) => {
    const icons = {
      planner_agent: '📋', executor_agent: '🔧', critic_agent: '✅',
      memory_agent: '🧠', research_agent: '🔍', coding_agent: '💻', automation_agent: '⏰',
    };
    return icons[name] || '🤖';
  };

  if (loading) {
    return <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>Loading agent system...</div>;
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Agent Dashboard</h1>
            <p>Multi-agent system monitor & control</p>
          </div>
          <button className="btn btn-sm" onClick={fetchAll}>Refresh</button>
        </div>
      </div>

      {/* Tab bar */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--border)', paddingBottom: 8 }}>
        {['agents', 'graphs', 'routing', 'events', 'submit'].map(t => (
          <button
            key={t}
            className={`btn btn-sm ${tab === t ? 'btn-primary' : ''}`}
            onClick={() => { setTab(t); if (t === 'events') fetchEvents(); }}
            style={{ textTransform: 'capitalize' }}
          >
            {t === 'agents' && '🤖 '}
            {t === 'graphs' && '📊 '}
            {t === 'routing' && '🔀 '}
            {t === 'events' && '📋 '}
            {t === 'submit' && '➕ '}
            {t}
          </button>
        ))}
      </div>

      {/* Tab: Agents */}
      {tab === 'agents' && (
        <div className="grid grid-3">
          {Object.entries(agents).map(([name, info]) => (
            <div
              key={name}
              className="card"
              onClick={() => setSelectedAgent(selectedAgent === name ? null : name)}
              style={{ cursor: 'pointer' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <span style={{ fontSize: 24 }}>{getAgentIcon(name)}</span>
                <div>
                  <h3 style={{ fontSize: 14, fontWeight: 600, textTransform: 'capitalize' }}>
                    {name.replace('_agent', '').replace('_', ' ')}
                  </h3>
                  <span style={{
                    display: 'inline-block', padding: '2px 8px', borderRadius: 10,
                    fontSize: 11, fontWeight: 600,
                    background: getStatusColor(info.state) + '22',
                    color: getStatusColor(info.state),
                  }}>
                    {info.state}
                  </span>
                </div>
              </div>
              {selectedAgent === name && (
                <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  <div>Model: {info.model || 'default'}</div>
                  <div>Session: {info.session_id?.slice(0, 8)}...</div>
                  <div>Observations: {info.observations_count || 0}</div>
                  {info.last_error && <div style={{ color: 'var(--danger)' }}>Error: {info.last_error}</div>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Tab: Graphs */}
      {tab === 'graphs' && (
        <div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
            <div className="card" style={{ flex: 1, textAlign: 'center', padding: 16 }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--accent-primary)' }}>
                {coordStatus.active_graphs || 0}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Active</div>
            </div>
            <div className="card" style={{ flex: 1, textAlign: 'center', padding: 16 }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--success)' }}>
                {coordStatus.completed_graphs || 0}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Completed</div>
            </div>
            <div className="card" style={{ flex: 1, textAlign: 'center', padding: 16 }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--warning)' }}>
                {coordStatus.running_tasks || 0}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Running</div>
            </div>
            <div className="card" style={{ flex: 1, textAlign: 'center', padding: 16 }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-muted)' }}>
                {coordStatus.queue_size || 0}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Queued</div>
            </div>
          </div>

          {graphs.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: 40 }}>
              <p style={{ color: 'var(--text-muted)' }}>No task graphs yet. Submit a request to see graphs.</p>
            </div>
          ) : (
            graphs.map(graph => (
              <div key={graph.id} className="card" style={{ marginBottom: 12, padding: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{
                      display: 'inline-block', padding: '2px 8px', borderRadius: 10,
                      fontSize: 11, fontWeight: 600,
                      background: getStatusColor(graph.status) + '22',
                      color: getStatusColor(graph.status),
                      marginRight: 8,
                    }}>
                      {graph.status}
                    </span>
                    <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)' }}>
                      Graph {graph.id?.slice(0, 8)}...
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 12 }}>
                      {graph.task_count || 0} tasks ({graph.completed_count || 0} done, {graph.failed_count || 0} failed)
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button className="btn btn-sm" onClick={() => fetchDag(graph.id)}>DAG</button>
                    <button className="btn btn-sm btn-danger" onClick={() => cancelGraph(graph.id)}>Cancel</button>
                  </div>
                </div>
                {selectedGraph === graph.id && dagData && (
                  <div style={{ marginTop: 12 }}>
                    <DagViewer nodes={dagData.nodes || []} edges={dagData.edges || []} />
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab: Routing */}
      {tab === 'routing' && (
        <div className="card" style={{ padding: 0 }}>
          <table className="table">
            <thead>
              <tr><th>Agent</th><th>Assigned Model</th></tr>
            </thead>
            <tbody>
              {Object.entries(routing.assignments || {}).map(([agent, model]) => (
                <tr key={agent}>
                  <td style={{ textTransform: 'capitalize' }}>{agent.replace('_agent', '').replace('_', ' ')}</td>
                  <td><code>{model}</code></td>
                </tr>
              ))}
              <tr>
                <td style={{ color: 'var(--text-muted)' }}>Default</td>
                <td><code>{routing.default || 'qwen3'}</code></td>
              </tr>
            </tbody>
          </table>
          <div style={{ padding: 12, fontSize: 12, color: 'var(--text-muted)' }}>
            Fallback chain: {routing.fallback_chain?.join(' → ') || 'N/A'}
          </div>
        </div>
      )}

      {/* Tab: Events */}
      {tab === 'events' && (
        <div className="card" style={{ padding: 0, maxHeight: 500, overflow: 'auto' }}>
          {events.length === 0 ? (
            <div style={{ padding: 20, color: 'var(--text-muted)' }}>No events</div>
          ) : (
            events.slice().reverse().map((evt, i) => (
              <div key={i} className="log-entry">
                <span className="log-time">
                  {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                </span>
                <span className="log-level info">{evt.type}</span>
                <span className="log-msg">{JSON.stringify(evt.data).slice(0, 200)}</span>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab: Submit */}
      {tab === 'submit' && (
        <div className="card">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Submit a Request</h3>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
            Send a request to the multi-agent system. The planner will analyze it and create an execution graph.
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="text"
              placeholder="What would you like JARVIS to do?"
              value={requestInput}
              onChange={(e) => setRequestInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submitRequest()}
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" onClick={submitRequest}>Submit</button>
          </div>
        </div>
      )}
    </div>
  );
}

/* Simple DAG visualization */
function DagViewer({ nodes, edges }) {
  const getStatusColor = (status) => ({
    pending: '#606080', running: '#00d4ff', completed: '#44ff88',
    failed: '#ff4444', cancelled: '#ffaa44', blocked: '#ff6600',
  })[status] || '#606080';

  const colMap = {};
  nodes.forEach(n => {
    const deps = edges.filter(e => e.to === n.id).length;
    colMap[n.id] = deps;
  });

  return (
    <div style={{
      background: 'var(--bg-tertiary)', borderRadius: 8, padding: 16,
      fontFamily: 'var(--font-mono)', fontSize: 12, overflowX: 'auto',
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 400 }}>
        {nodes.map(node => (
          <div key={node.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              width: 10, height: 10, borderRadius: '50%',
              background: getStatusColor(node.status), flexShrink: 0,
            }} />
            <span style={{ color: 'var(--text-secondary)', width: 80, flexShrink: 0 }}>
              {node.agent?.replace('_agent', '').slice(0, 10)}
            </span>
            <span style={{ color: 'var(--text-primary)' }}>{node.label}</span>
            <span style={{ color: 'var(--text-muted)', marginLeft: 'auto' }}>
              [{node.status}]
            </span>
          </div>
        ))}
      </div>
      {edges.length > 0 && (
        <div style={{ marginTop: 12, color: 'var(--text-muted)', fontSize: 11 }}>
          Dependencies: {edges.map(e => `${e.from.slice(0, 6)}→${e.to.slice(0, 6)}`).join(', ')}
        </div>
      )}
    </div>
  );
}
