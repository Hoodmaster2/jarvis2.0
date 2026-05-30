import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';
import { useSettings } from '../hooks/useSettings';

export default function Settings() {
  const { config, loading, updateSetting } = useSettings();
  const [models, setModels] = useState([]);

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const data = await api.getModels();
      setModels(data.models || []);
    } catch {
      // Ollama might not be running
    }
  };

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Loading settings...</p>;

  return (
    <div style={{ maxWidth: 700 }}>
      <div className="page-header">
        <h1>Settings</h1>
        <p>Configure JARVIS</p>
      </div>

      {/* Model */}
      <div className="settings-group">
        <h2>Ollama Model</h2>
        <div className="card">
          <div className="setting-row">
            <div>
              <div className="label">Model</div>
              <div className="description">Local LLM model for responses</div>
            </div>
            <select
              value={config?.ollama?.model || 'qwen3'}
              onChange={(e) => updateSetting('ollama.model', e.target.value)}
            >
              {models.length > 0 ? models.map((m) => (
                <option key={m} value={m}>{m}</option>
              )) : (
                <option value="qwen3">qwen3</option>
              )}
            </select>
          </div>
          <div className="setting-row">
            <div>
              <div className="label">Temperature</div>
              <div className="description">Creativity vs accuracy (0-2)</div>
            </div>
            <input
              type="number"
              min="0"
              max="2"
              step="0.1"
              value={config?.ollama?.temperature ?? 0.7}
              onChange={(e) => updateSetting('ollama.temperature', parseFloat(e.target.value))}
              style={{ width: 80 }}
            />
          </div>
          <div className="setting-row">
            <div>
              <div className="label">Context Size</div>
              <div className="description">Maximum context window tokens</div>
            </div>
            <input
              type="number"
              min="2048"
              max="32768"
              step="1024"
              value={config?.ollama?.context_size ?? 8192}
              onChange={(e) => updateSetting('ollama.context_size', parseInt(e.target.value))}
              style={{ width: 100 }}
            />
          </div>
        </div>
      </div>

      {/* Voice */}
      <div className="settings-group">
        <h2>Voice</h2>
        <div className="card">
          <div className="setting-row">
            <div>
              <div className="label">Speech-to-text Engine</div>
              <div className="description">Local whisper or Windows SAPI</div>
            </div>
            <select
              value={config?.voice?.stt_engine || 'whisper'}
              onChange={(e) => updateSetting('voice.stt_engine', e.target.value)}
            >
              <option value="whisper">Whisper (local)</option>
              <option value="windows">Windows SAPI</option>
            </select>
          </div>
          <div className="setting-row">
            <div>
              <div className="label">Text-to-speech Engine</div>
              <div className="description">Piper or Windows SAPI</div>
            </div>
            <select
              value={config?.voice?.tts_engine || 'windows'}
              onChange={(e) => updateSetting('voice.tts_engine', e.target.value)}
            >
              <option value="piper">Piper</option>
              <option value="windows">Windows SAPI</option>
            </select>
          </div>
          <div className="setting-row">
            <div>
              <div className="label">Wake Word</div>
              <div className="description">Listen for "Jarvis" wake word</div>
            </div>
            <label className="toggle">
              <input
                type="checkbox"
                checked={config?.voice?.wake_word_enabled || false}
                onChange={(e) => updateSetting('voice.wake_word_enabled', e.target.checked)}
              />
              <span className="toggle-slider" />
            </label>
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="settings-group">
        <h2>Security</h2>
        <div className="card">
          <div className="setting-row">
            <div>
              <div className="label">Permission Mode</div>
              <div className="description">How JARVIS handles dangerous actions</div>
            </div>
            <select
              value={config?.security?.mode || 'ask'}
              onChange={(e) => updateSetting('security.mode', e.target.value)}
            >
              <option value="ask">Ask for confirmation</option>
              <option value="auto">Auto-approve (not recommended)</option>
              <option value="strict">Strict (confirm everything)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Memory */}
      <div className="settings-group">
        <h2>Memory</h2>
        <div className="card">
          <div className="setting-row">
            <div>
              <div className="label">Memory Enabled</div>
              <div className="description">Store conversations and preferences</div>
            </div>
            <label className="toggle">
              <input
                type="checkbox"
                checked={config?.memory?.enabled !== false}
                onChange={(e) => updateSetting('memory.enabled', e.target.checked)}
              />
              <span className="toggle-slider" />
            </label>
          </div>
        </div>
      </div>

      {/* App */}
      <div className="settings-group">
        <h2>Application</h2>
        <div className="card">
          <div className="setting-row">
            <div>
              <div className="label">Start with Windows</div>
              <div className="description">Automatically launch on boot</div>
            </div>
            <label className="toggle">
              <input
                type="checkbox"
                checked={config?.app?.start_with_windows || false}
                onChange={(e) => {
                  updateSetting('app.start_with_windows', e.target.checked);
                  if (window.jarvis?.config) {
                    window.jarvis.config.set('startWithWindows', e.target.checked);
                  }
                }}
              />
              <span className="toggle-slider" />
            </label>
          </div>
          <div className="setting-row">
            <div>
              <div className="label">Minimize to Tray</div>
              <div className="description">Minimize to system tray instead of closing</div>
            </div>
            <label className="toggle">
              <input
                type="checkbox"
                checked={config?.app?.minimize_to_tray !== false}
                onChange={(e) => updateSetting('app.minimize_to_tray', e.target.checked)}
              />
              <span className="toggle-slider" />
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
