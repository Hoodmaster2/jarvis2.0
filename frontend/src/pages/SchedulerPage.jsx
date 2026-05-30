import React, { useState, useEffect } from 'react';

export default function SchedulerPage() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', cron: '', interval: 3600 });

  useEffect(() => { loadTasks(); }, []);

  const loadTasks = async () => {
    try {
      const res = await fetch('/api/scheduler/tasks');
      const data = await res.json();
      setTasks(data.tasks || []);
    } catch (err) {
      console.error('Failed to load tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  const createTask = async () => {
    await fetch('/api/scheduler/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: form.name,
        cron_expr: form.cron,
        interval_seconds: form.cron ? 0 : form.interval,
      }),
    });
    setShowForm(false);
    setForm({ name: '', cron: '', interval: 3600 });
    loadTasks();
  };

  const deleteTask = async (id) => {
    await fetch(`/api/scheduler/tasks/${id}`, { method: 'DELETE' });
    loadTasks();
  };

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Loading scheduler...</p>;

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1>Scheduler</h1>
          <p>Cron and interval-based task scheduling</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          {showForm ? 'Cancel' : '+ New Task'}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, marginBottom: 12 }}>Schedule Task</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <input placeholder="Task name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
            <input placeholder="Cron expression (e.g., 0 */2 * * *)" value={form.cron}
              onChange={e => setForm({ ...form, cron: e.target.value })} />
            <input placeholder="Interval seconds (if no cron)" type="number" value={form.interval}
              onChange={e => setForm({ ...form, interval: parseInt(e.target.value) || 0 })} />
            <button className="btn btn-primary" onClick={createTask}>Schedule</button>
          </div>
        </div>
      )}

      {tasks.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <p style={{ color: 'var(--text-muted)' }}>No scheduled tasks</p>
        </div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Schedule</th>
              <th>Next Run</th>
              <th>Last Run</th>
              <th>Runs</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td style={{ fontWeight: 600 }}>{t.name}</td>
                <td><code style={{ fontSize: 12 }}>{t.cron_expr || `${t.interval_seconds}s`}</code></td>
                <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                  {t.next_run ? new Date(t.next_run * 1000).toLocaleString() : '-'}
                </td>
                <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {t.last_run ? new Date(t.last_run * 1000).toLocaleString() : 'Never'}
                </td>
                <td>{t.run_count || 0}</td>
                <td>
                  <span style={{
                    color: t.enabled ? 'var(--success)' : 'var(--text-muted)',
                    fontSize: 13,
                  }}>
                    {t.enabled ? 'Active' : 'Disabled'}
                  </span>
                </td>
                <td>
                  <button className="btn btn-sm btn-danger" onClick={() => deleteTask(t.id)}>Remove</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
