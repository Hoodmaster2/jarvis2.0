import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

export default function LearningDashboard() {
  const [tab, setTab] = useState('patterns');
  const [failures, setFailures] = useState([]);
  const [patterns, setPatterns] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [workflowStats, setWorkflowStats] = useState({});
  const [automationSuggestions, setAutomationSuggestions] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [corrections, setCorrections] = useState([]);
  const [usageStats, setUsageStats] = useState({});
  const [promptTemplates, setPromptTemplates] = useState({});
  const [newTemplateName, setNewTemplateName] = useState('');
  const [newTemplateContent, setNewTemplateContent] = useState('');

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      const [failData, suggestData, wfStats, autoSuggest, recData, corrData, usageData] = await Promise.all([
        api.getLearningFailures().catch(() => ({ failures: [], patterns: [] })),
        api.getLearningSuggestions().catch(() => ({ suggestions: [] })),
        api.getLearningWorkflowStats().catch(() => ({})),
        api.getLearningAutomationSuggestions().catch(() => ({ suggestions: [] })),
        api.getLearningRecommendations().catch(() => ({ recommendations: [] })),
        api.getLearningCorrections().catch(() => ({ corrections: [], banned_patterns: [] })),
        api.getLearningUsageStats().catch(() => ({})),
      ]);
      setFailures(failData.failures || []);
      setPatterns(failData.patterns || []);
      setSuggestions(suggestData.suggestions || []);
      setWorkflowStats(wfStats);
      setAutomationSuggestions(autoSuggest.suggestions || []);
      setRecommendations(recData.recommendations || []);
      setCorrections(corrData);
      setUsageStats(usageData);
    } catch (e) { console.error(e); }
  };

  const loadTemplates = async () => {
    try {
      const data = await api.getPromptTemplates();
      setPromptTemplates(data.templates || {});
    } catch (e) { console.error(e); }
  };

  const saveTemplate = async () => {
    await api.savePromptTemplate(newTemplateName, newTemplateContent);
    setNewTemplateName('');
    setNewTemplateContent('');
    loadTemplates();
  };

  const dismissRec = async (id) => {
    await api.dismissRecommendation(id);
    loadAll();
  };

  return (
    <div className="page">
      <h1>Learning Dashboard</h1>

      <div className="tab-bar">
        <button className={tab === 'patterns' ? 'active' : ''} onClick={() => setTab('patterns')}>Patterns</button>
        <button className={tab === 'failures' ? 'active' : ''} onClick={() => setTab('failures')}>Failures</button>
        <button className={tab === 'automations' ? 'active' : ''} onClick={() => setTab('automations')}>Automations</button>
        <button className={tab === 'prompts' ? 'active' : ''} onClick={() => setTab('prompts')}>Prompts</button>
        <button className={tab === 'corrections' ? 'active' : ''} onClick={() => setTab('corrections')}>Corrections</button>
        <button className={tab === 'stats' ? 'active' : ''} onClick={() => setTab('stats')}>Stats</button>
      </div>

      {tab === 'patterns' && (
        <div className="card">
          <h3>Learned Patterns</h3>
          {patterns.map((p, i) => (
            <div key={i} className="memory-entry">
              <span className="tag bg-purple">{p.type}</span>
              {p.items?.map((item, j) => (
                <div key={j} className="mono">
                  {item.action && item.tool && `${item.action} / ${item.tool}`}
                  {item.error && `"${item.error.slice(0, 100)}"`}
                  <span className="tag bg-blue">x{item.count}</span>
                </div>
              ))}
            </div>
          ))}
          {patterns.length === 0 && <p className="muted">No patterns learned yet.</p>}

          <h4>Avoidance Suggestions</h4>
          {suggestions.map((s, i) => (
            <div key={i} className="alert alert-warning">{s}</div>
          ))}

          <h4>Recommendations</h4>
          {recommendations.map(r => (
            <div key={r.id} className="card">
              <p>{r.message}</p>
              <span className="tag">{(r.confidence * 100).toFixed(0)}% confidence</span>
              <button onClick={() => dismissRec(r.id)}>Dismiss</button>
            </div>
          ))}
        </div>
      )}

      {tab === 'failures' && (
        <div className="card">
          <h3>Failed Task Reports</h3>
          <button onClick={loadAll}>Refresh</button>
          <table>
            <thead><tr><th>Time</th><th>Action</th><th>Tool</th><th>Error</th></tr></thead>
            <tbody>
              {failures.slice().reverse().map(f => (
                <tr key={f.id}>
                  <td className="mono small">{new Date(f.timestamp).toLocaleString()}</td>
                  <td>{f.action}</td>
                  <td><span className="tag">{f.tool}</span></td>
                  <td className="mono small" style={{ color: '#ef4444' }}>{f.error?.slice(0, 100)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'automations' && (
        <div className="card">
          <h3>Suggested Automations</h3>
          {automationSuggestions.map((s, i) => (
            <div key={i} className="card">
              <p>{s.suggestion}</p>
              <span className="tag bg-green">{s.type}</span>
              <span className="tag">x{s.frequency}</span>
              <div className="mono small">{s.sequence?.join(' → ')}</div>
            </div>
          ))}
          {automationSuggestions.length === 0 && <p className="muted">No automation patterns detected yet.</p>}

          <h4>Workflow Stats</h4>
          <div className="stats-grid">
            <div className="stat-card">Total: {workflowStats.total_workflows || 0}</div>
            <div className="stat-card">Completed: {workflowStats.completed || 0}</div>
            <div className="stat-card">Failed: {workflowStats.failed || 0}</div>
            <div className="stat-card">Patterns: {workflowStats.patterns_found || 0}</div>
          </div>
        </div>
      )}

      {tab === 'prompts' && (
        <div className="card">
          <h3>Prompt Templates</h3>
          <div className="form-group">
            <input value={newTemplateName} onChange={e => setNewTemplateName(e.target.value)} placeholder="Template name" />
            <textarea value={newTemplateContent} onChange={e => setNewTemplateContent(e.target.value)} rows={3} placeholder="Template content..." />
            <button onClick={saveTemplate}>Save Template</button>
          </div>
          <table>
            <thead><tr><th>Name</th><th>Preview</th></tr></thead>
            <tbody>
              {Object.entries(promptTemplates).map(([name, content]) => (
                <tr key={name}>
                  <td><strong>{name}</strong></td>
                  <td className="mono small">{content?.slice(0, 100)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button onClick={loadTemplates}>Load Templates</button>
        </div>
      )}

      {tab === 'corrections' && (
        <div className="card">
          <h3>User Corrections</h3>
          <table>
            <thead><tr><th>Time</th><th>Action</th><th>Correction</th></tr></thead>
            <tbody>
              {corrections.corrections?.slice().reverse().map(c => (
                <tr key={c.id}>
                  <td className="mono small">{new Date(c.timestamp).toLocaleString()}</td>
                  <td>{c.action}</td>
                  <td className="mono">{c.correction?.slice(0, 100)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <h4>Banned Patterns</h4>
          {corrections.banned_patterns?.map((bp, i) => (
            <div key={i} className="alert alert-warning">{bp}</div>
          ))}
          <h4>Recurring Issues</h4>
          {corrections.recurring?.map((r, i) => (
            <div key={i} className="card">
              <strong>{r.action}</strong> — corrected {r.corrections}x
            </div>
          ))}
        </div>
      )}

      {tab === 'stats' && (
        <div className="card">
          <h3>Usage Statistics</h3>
          <div className="stats-grid">
            <div className="stat-card">Events: {usageStats.total_events || 0}</div>
          </div>
          <h4>Top Skills</h4>
          {usageStats.top_skills?.map((s, i) => (
            <div key={i}>{s.name} — <span className="tag">{s.count}</span></div>
          ))}
          <h4>Top Tools</h4>
          {usageStats.top_tools?.map((t, i) => (
            <div key={i}>{t.name} — <span className="tag">{t.count}</span></div>
          ))}
          <button onClick={loadAll}>Refresh All</button>
        </div>
      )}
    </div>
  );
}
