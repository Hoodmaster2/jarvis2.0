import React, { useState, useEffect } from 'react';

export default function Automations() {
  const [workflows, setWorkflows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', trigger_type: 'manual', trigger_event: '', steps: '' });

  useEffect(() => { loadWorkflows(); }, []);

  const loadWorkflows = async () => {
    try {
      const res = await fetch('/api/workflows');
      const data = await res.json();
      setWorkflows(data.workflows || []);
    } catch (err) {
      console.error('Failed to load workflows:', err);
    } finally {
      setLoading(false);
    }
  };

  const runWorkflow = async (id) => {
    await fetch(`/api/workflows/${id}/run`, { method: 'POST' });
    loadWorkflows();
  };

  const deleteWorkflow = async (id) => {
    await fetch(`/api/workflows/${id}`, { method: 'DELETE' });
    loadWorkflows();
  };

  const createWorkflow = async () => {
    const steps = form.steps.split('\n').filter(s => s.trim()).map((s, i) => ({
      name: `Step ${i + 1}`,
      action: s.trim().split(' ')[0] || 'shell',
      params: { command: s.trim() },
      permission_level: 'safe',
      depends_on: [],
    }));
    await fetch('/api/workflows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: form.name,
        description: form.description,
        trigger: { type: form.trigger_type, event_type: form.trigger_event },
        steps,
      }),
    });
    setShowForm(false);
    setForm({ name: '', description: '', trigger_type: 'manual', trigger_event: '', steps: '' });
    loadWorkflows();
  };

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Loading automations...</p>;

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Automations</h1>
          <p>Event-driven workflow automation</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ New Automation'}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, marginBottom: 12 }}>Create Automation</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <input placeholder="Name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
            <input placeholder="Description" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
            <select value={form.trigger_type} onChange={e => setForm({ ...form, trigger_type: e.target.value })}>
              <option value="manual">Manual</option>
              <option value="event">Event</option>
              <option value="schedule">Schedule</option>
            </select>
            {form.trigger_type === 'event' && (
              <input placeholder="Event type (e.g., file.created)" value={form.trigger_event}
                onChange={e => setForm({ ...form, trigger_event: e.target.value })} />
            )}
            <textarea rows={4} placeholder="One action per line (e.g., shell echo hello)" value={form.steps}
              onChange={e => setForm({ ...form, steps: e.target.value })} />
            <button className="btn btn-primary" onClick={createWorkflow}>Create</button>
          </div>
        </div>
      )}

      {workflows.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <p style={{ color: 'var(--text-muted)', marginBottom: 8 }}>No automations yet</p>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Create your first automation to get started</p>
        </div>
      ) : (
        workflows.map((wf) => (
          <div className="card" key={wf.id} style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: 16, marginBottom: 4 }}>{wf.name}</h3>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>{wf.description}</p>
                <div style={{ display: 'flex', gap: 8, fontSize: 12 }}>
                  <span style={{ color: 'var(--accent-primary)' }}>Trigger: {wf.trigger?.type}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Steps: {wf.steps?.length || 0}</span>
                  <span style={{
                    color: wf.status === 'completed' ? 'var(--success)' :
                           wf.status === 'running' ? 'var(--warning)' : 'var(--text-muted)',
                  }}>{wf.status}</span>
                  <span style={{ color: 'var(--text-muted)' }}>Run count: {wf.run_count || 0}</span>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-sm btn-primary" onClick={() => runWorkflow(wf.id)}>Run</button>
                <button className="btn btn-sm btn-danger" onClick={() => deleteWorkflow(wf.id)}>Delete</button>
              </div>
            </div>
            {wf.steps?.length > 0 && (
              <div style={{ marginTop: 12, borderTop: '1px solid var(--border)', paddingTop: 8 }}>
                {wf.steps.map((step, i) => (
                  <div key={step.id || i} style={{ display: 'flex', gap: 8, fontSize: 13, padding: '4px 0' }}>
                    <span style={{ color: 'var(--text-muted)', width: 60 }}>{step.status}</span>
                    <span style={{ color: 'var(--accent-primary)' }}>{step.action}</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{JSON.stringify(step.params)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
