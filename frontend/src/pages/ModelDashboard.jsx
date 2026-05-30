import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

export default function ModelDashboard() {
  const [routerStatus, setRouterStatus] = useState({});
  const [installed, setInstalled] = useState([]);
  const [health, setHealth] = useState({});
  const [taskInput, setTaskInput] = useState('');
  const [routingDecision, setRoutingDecision] = useState(null);
  const [forceModel, setForceModel] = useState('');
  const [tab, setTab] = useState('overview');

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      const [statusData, installedData, healthData] = await Promise.all([
        api.getRouterStatus().catch(() => ({})),
        api.getInstalledModels().catch(() => ({ models: [] })),
        api.getModelHealth().catch(() => ({ models: {} })),
      ]);
      setRouterStatus(statusData);
      setInstalled(installedData.models || []);
      setHealth(healthData.models || {});
    } catch (e) { console.error(e); }
  };

  const analyzeTask = async () => {
    if (!taskInput.trim()) return;
    try {
      const data = await api.analyzeTask(taskInput);
      setRoutingDecision(data);
    } catch (e) { console.error(e); }
  };

  const handleForceModel = async () => {
    if (!forceModel.trim()) return;
    try {
      await api.forceModel(forceModel);
      loadAll();
    } catch (e) { console.error(e); }
  };

  const releaseForce = async () => {
    await api.releaseForceModel();
    setForceModel('');
    loadAll();
  };

  const toggleModel = async (name, disable) => {
    if (disable) await api.disableModel(name);
    else await api.enableModel(name);
    loadAll();
  };

  const setStrategy = async (strategy) => {
    await api.setBalancerStrategy(strategy);
    loadAll();
  };

  const warmUp = async (model) => {
    await api.warmUpModel(model);
  };

  const statusColor = (s) => {
    if (s === 'healthy') return '#10b981';
    if (s === 'degraded') return '#f59e0b';
    if (s === 'unhealthy') return '#ef4444';
    return '#6b7280';
  };

  return (
    <div className="page">
      <h1>Model Intelligence Router</h1>

      <div className="tab-bar">
        <button className={tab === 'overview' ? 'active' : ''} onClick={() => setTab('overview')}>Overview</button>
        <button className={tab === 'routing' ? 'active' : ''} onClick={() => setTab('routing')}>Routing</button>
        <button className={tab === 'models' ? 'active' : ''} onClick={() => setTab('models')}>Models</button>
        <button className={tab === 'health' ? 'active' : ''} onClick={() => setTab('health')}>Health</button>
        <button className={tab === 'logs' ? 'active' : ''} onClick={() => setTab('logs')}>Logs</button>
      </div>

      {tab === 'overview' && (
        <div className="card">
          <h3>Active Model: {routerStatus.forced_model || routerStatus.default_model || 'qwen3'}</h3>
          {routerStatus.forced_model && <span className="tag bg-yellow">Forced</span>}
          <div className="stats-grid">
            <div className="stat-card">Installed: {routerStatus.installed || 0}</div>
            <div className="stat-card">Healthy: {routerStatus.health_summary?.healthy || 0}</div>
            <div className="stat-card">Degraded: {routerStatus.health_summary?.degraded || 0}</div>
            <div className="stat-card">Unhealthy: {routerStatus.health_summary?.unhealthy || 0}</div>
            <div className="stat-card">Balancer: {routerStatus.balancer_strategy || 'least_load'}</div>
            <div className="stat-card">Warmed: {(routerStatus.warmed_up || []).length}</div>
          </div>

          <h4>Agent Assignments</h4>
          <table>
            <thead><tr><th>Agent</th><th>Model</th></tr></thead>
            <tbody>
              {Object.entries(routerStatus.agent_assignments || {}).map(([agent, model]) => (
                <tr key={agent}><td>{agent}</td><td><span className="tag">{model}</span></td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'routing' && (
        <div className="card">
          <h3>Task Analysis & Routing</h3>
          <div className="row">
            <textarea
              value={taskInput}
              onChange={e => setTaskInput(e.target.value)}
              placeholder="Describe a task to analyze which model is best..."
              rows={3}
              className="flex-1"
            />
            <button onClick={analyzeTask}>Analyze</button>
          </div>
          {routingDecision && (
            <div className="card">
              <h4>Routing Decision</h4>
              <p><strong>Model:</strong> <span className="tag bg-green">{routingDecision.chosen_model}</span></p>
              <p><strong>Type:</strong> {routingDecision.task_type}</p>
              <p><strong>Complexity:</strong> {'🧠'.repeat(routingDecision.complexity || 1)}</p>
              <p><strong>Needs Vision:</strong> {routingDecision.needs_vision ? 'Yes' : 'No'}</p>
              <p><strong>Available:</strong> {routingDecision.available_models?.join(', ')}</p>
            </div>
          )}

          <h4>Balancer Strategy</h4>
          <div className="row">
            {['round_robin', 'least_load', 'random', 'fastest'].map(s => (
              <button key={s} onClick={() => setStrategy(s)}
                className={routerStatus.balancer_strategy === s ? 'active' : ''}>{s}</button>
            ))}
          </div>

          <h4>Manual Override</h4>
          <div className="row">
            <select value={forceModel} onChange={e => setForceModel(e.target.value)}>
              <option value="">Select model...</option>
              {installed.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
            </select>
            <button onClick={handleForceModel}>Force Model</button>
            <button onClick={releaseForce}>Release</button>
          </div>
        </div>
      )}

      {tab === 'models' && (
        <div className="card">
          <h3>Installed Models ({installed.length})</h3>
          <table>
            <thead><tr><th>Model</th><th>Type</th><th>Capabilities</th><th>Context</th><th>Health</th><th>Actions</th></tr></thead>
            <tbody>
              {installed.map(m => {
                const h = health[m.name] || {};
                return (
                  <tr key={m.name}>
                    <td><strong>{m.name}</strong></td>
                    <td><span className="tag">{m.type}</span></td>
                    <td className="mono small">{(m.capabilities || []).join(', ')}</td>
                    <td>{(m.context || 0) > 1000 ? `${(m.context / 1024).toFixed(0)}K` : m.context}</td>
                    <td><span className="status-dot" style={{ background: statusColor(h.status) }} /> {h.status}</td>
                    <td>
                      <button onClick={() => warmUp(m.name)}>Warm</button>
                      <button onClick={() => toggleModel(m.name, true)}>Disable</button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'health' && (
        <div className="card">
          <h3>Model Health Metrics</h3>
          <button onClick={loadAll}>Refresh</button>
          <table>
            <thead><tr><th>Model</th><th>Status</th><th>Avg Latency</th><th>Tokens/s</th><th>Failure Rate</th><th>Calls</th></tr></thead>
            <tbody>
              {Object.entries(health).map(([name, h]) => (
                <tr key={name}>
                  <td><strong>{name}</strong></td>
                  <td><span className="tag" style={{ background: statusColor(h.status) }}>{h.status}</span></td>
                  <td>{h.avg_latency_ms?.toFixed(0)}ms</td>
                  <td>{h.avg_tokens_per_sec?.toFixed(1)}</td>
                  <td>{(h.failure_rate * 100).toFixed(0)}%</td>
                  <td>{h.total_calls}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'logs' && (
        <div className="card">
          <h3>Routing Logs</h3>
          <pre className="pre-wrap">{JSON.stringify(routerStatus, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
