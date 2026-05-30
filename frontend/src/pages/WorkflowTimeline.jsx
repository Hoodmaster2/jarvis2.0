import React, { useState, useEffect } from 'react';

const API = '/api';

export default function WorkflowTimeline() {
  const [workflows, setWorkflows] = useState([]);
  const [scheduled, setScheduled] = useState([]);
  const [activeTab, setActiveTab] = useState('workflows');
  const [newWorkflow, setNewWorkflow] = useState({ name: '', steps: '' });

  useEffect(() => {
    fetchWorkflows();
    fetchScheduled();
  }, []);

  const fetchWorkflows = async () => {
    try {
      const res = await fetch(`${API}/workflows`);
      const data = await res.json();
      setWorkflows(data.workflows || []);
    } catch {}
  };

  const fetchScheduled = async () => {
    try {
      const res = await fetch(`${API}/scheduler/tasks`);
      const data = await res.json();
      setScheduled(data.scheduled_tasks || []);
    } catch {}
  };

  const createWorkflow = async () => {
    try {
      const steps = newWorkflow.steps ? JSON.parse(newWorkflow.steps) : [];
      await fetch(`${API}/workflows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newWorkflow.name, steps }),
      });
      setNewWorkflow({ name: '', steps: '' });
      fetchWorkflows();
    } catch (err) {
      alert('Error creating workflow. Steps must be valid JSON.');
    }
  };

  const runWorkflow = async (id) => {
    try {
      await fetch(`${API}/workflows/${id}/run`, { method: 'POST' });
      fetchWorkflows();
    } catch {}
  };

  const scheduleTask = async () => {
    const name = prompt('Task name:');
    if (!name) return;
    const delay = parseInt(prompt('Delay in seconds:', '60'), 10);
    try {
      await fetch(`${API}/scheduler/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, delay_seconds: delay, action_type: 'executor_agent', params: {} }),
      });
      fetchScheduled();
    } catch {}
  };

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>Workflow Timeline</h1>
            <p>Automation workflows and scheduled tasks</p>
          </div>
          <button className="btn btn-sm" onClick={() => { fetchWorkflows(); fetchScheduled(); }}>Refresh</button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '1px solid var(--border)', paddingBottom: 8 }}>
        {['workflows', 'scheduled', 'create'].map(t => (
          <button
            key={t}
            className={`btn btn-sm ${activeTab === t ? 'btn-primary' : ''}`}
            onClick={() => setActiveTab(t)}
            style={{ textTransform: 'capitalize' }}
          >
            {t === 'workflows' && '📋 '}
            {t === 'scheduled' && '⏰ '}
            {t === 'create' && '➕ '}
            {t}
          </button>
        ))}
      </div>

      {activeTab === 'workflows' && (
        <div>
          {workflows.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: 40 }}>
              <p style={{ color: 'var(--text-muted)' }}>No workflows created yet</p>
            </div>
          ) : (
            workflows.map((wf, i) => (
              <div key={wf.id || i} className="card" style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h3 style={{ fontSize: 14, fontWeight: 600 }}>{wf.name}</h3>
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      {wf.steps?.length || 0} steps · Trigger: {wf.trigger || 'manual'} · Runs: {wf.run_count || 0}
                    </p>
                  </div>
                  <button className="btn btn-sm btn-primary" onClick={() => runWorkflow(wf.id)}>Run Now</button>
                </div>
                {wf.steps && wf.steps.length > 0 && (
                  <div style={{ marginTop: 8, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {wf.steps.map((step, si) => (
                      <span key={si} style={{
                        padding: '2px 8px', borderRadius: 4, fontSize: 11,
                        background: step.requires_approval ? 'rgba(255,170,68,0.15)' : 'var(--bg-tertiary)',
                        color: step.requires_approval ? 'var(--warning)' : 'var(--accent-primary)',
                      }}>
                        {step.action || step.name || `Step ${si + 1}`}
                        {step.requires_approval && ' ⚠️'}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'scheduled' && (
        <div>
          <div style={{ marginBottom: 12 }}>
            <button className="btn btn-primary btn-sm" onClick={scheduleTask}>+ Schedule Task</button>
          </div>
          {scheduled.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: 40 }}>
              <p style={{ color: 'var(--text-muted)' }}>No scheduled tasks</p>
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr><th>Name</th><th>Next Run</th><th>Interval</th><th>Runs</th><th>Status</th></tr>
              </thead>
              <tbody>
                {scheduled.map((t, i) => (
                  <tr key={t.id || i}>
                    <td>{t.name}</td>
                    <td>{t.next_run ? new Date(t.next_run * 1000).toLocaleString() : '-'}</td>
                    <td>{t.interval ? `${t.interval}s` : 'Once'}</td>
                    <td>{t.run_count || 0}</td>
                    <td><span style={{ color: 'var(--accent-primary)' }}>{t.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {activeTab === 'create' && (
        <div className="card">
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>Create Workflow</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <input
              type="text"
              placeholder="Workflow name"
              value={newWorkflow.name}
              onChange={(e) => setNewWorkflow(prev => ({ ...prev, name: e.target.value }))}
            />
            <textarea
              placeholder='Steps as JSON array: [{"action": "web_search", "params": {"query": "..."}}]'
              value={newWorkflow.steps}
              onChange={(e) => setNewWorkflow(prev => ({ ...prev, steps: e.target.value }))}
              rows={6}
              style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
            />
            <div>
              <button className="btn btn-primary" onClick={createWorkflow}>Create Workflow</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
