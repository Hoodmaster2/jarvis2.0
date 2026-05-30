import React, { useState, useEffect } from 'react';
import { api } from '../utils/api';

export default function DesktopControl() {
  const [tab, setTab] = useState('state');
  const [desktopState, setDesktopState] = useState({});
  const [activeWindow, setActiveWindow] = useState({});
  const [windows, setWindows] = useState([]);
  const [runningApps, setRunningApps] = useState([]);
  const [mousePos, setMousePos] = useState({});
  const [clipboard, setClipboard] = useState('');
  const [typeText, setTypeText] = useState('');
  const [hotkeyText, setHotkeyText] = useState('');
  const [mouseX, setMouseX] = useState(0);
  const [mouseY, setMouseY] = useState(0);
  const [appPath, setAppPath] = useState('');
  const [focusTitle, setFocusTitle] = useState('');
  const [mode, setMode] = useState('safe');
  const [dialogs, setDialogs] = useState([]);
  const [focusedApp, setFocusedApp] = useState('');
  const [screenText, setScreenText] = useState('');
  const [clickTextStr, setClickTextStr] = useState('');

  useEffect(() => {
    loadDesktopState();
    loadMode();
  }, []);

  const loadDesktopState = async () => {
    try {
      const [state, active, wList, apps, pos, clip, d, fa] = await Promise.all([
        api.getDesktopState().catch(() => ({})),
        api.getActiveWindow().catch(() => ({})),
        api.listWindows().catch(() => ({ windows: [] })),
        api.getRunningApps().catch(() => ({ apps: [] })),
        api.getMousePosition().catch(() => ({})),
        api.readClipboard().catch(() => ({ text: '' })),
        api.detectDialogs().catch(() => ({ dialogs: [] })),
        api.getFocusedApp().catch(() => ({ app_type: '' })),
      ]);
      setDesktopState(state);
      setActiveWindow(active);
      setWindows(wList.windows || []);
      setRunningApps(apps.apps || []);
      setMousePos(pos);
      setClipboard(clip.text || '');
      setDialogs(d.dialogs || []);
      setFocusedApp(fa.app_type || '');
    } catch (e) { console.error(e); }
  };

  const loadMode = async () => {
    try {
      const data = await api.getDesktopMode();
      setMode(data.mode || 'safe');
    } catch (e) { console.error(e); }
  };

  const setDesktopMode = async (m) => {
    await api.setDesktopMode(m);
    setMode(m);
  };

  const moveMouse = async () => {
    const data = await api.moveMouse(mouseX, mouseY);
    setMousePos(data);
  };

  const clickMouse = async (button = 'left') => {
    await api.clickMouse(button);
  };

  const typeKeyboard = async () => {
    await api.typeText(typeText);
  };

  const sendHotkey = async () => {
    await api.sendHotkey(hotkeyText);
  };

  const readClipboard = async () => {
    const data = await api.readClipboard();
    setClipboard(data.text || '');
  };

  const writeClipboard = async () => {
    await api.writeClipboard(clipboard);
  };

  const focusWindow = async () => {
    await api.focusWindow(focusTitle);
  };

  const launchApp = async () => {
    await api.launchApp(appPath);
  };

  const getScreenText = async () => {
    const data = await api.getScreenText();
    setScreenText(data.text || '');
  };

  const clickText = async () => {
    await api.clickTextOnScreen(clickTextStr);
  };

  return (
    <div className="page">
      <h1>Desktop Control</h1>

      <div className="mode-badge" style={{ background: mode === 'safe' ? '#10b981' : mode === 'developer' ? '#f59e0b' : '#ef4444' }}>
        Mode: {mode.toUpperCase()}
      </div>

      <div className="tab-bar">
        <button className={tab === 'state' ? 'active' : ''} onClick={() => setTab('state')}>Desktop State</button>
        <button className={tab === 'mouse' ? 'active' : ''} onClick={() => setTab('mouse')}>Mouse</button>
        <button className={tab === 'keyboard' ? 'active' : ''} onClick={() => setTab('keyboard')}>Keyboard</button>
        <button className={tab === 'windows' ? 'active' : ''} onClick={() => setTab('windows')}>Windows</button>
        <button className={tab === 'apps' ? 'active' : ''} onClick={() => setTab('apps')}>Apps</button>
        <button className={tab === 'mode' ? 'active' : ''} onClick={() => setTab('mode')}>Mode</button>
      </div>

      {tab === 'state' && (
        <div className="card">
          <h3>Current State</h3>
          <button onClick={loadDesktopState}>Refresh</button>
          <div className="stats-grid">
            <div className="stat-card">Windows: {desktopState.window_count || 0}</div>
            <div className="stat-card">Dialogs: {dialogs.length}</div>
            <div className="stat-card">Focused: {focusedApp}</div>
            <div className="stat-card">Mode: {mode}</div>
          </div>
          <h4>Active Window</h4>
          <p><strong>{activeWindow.title}</strong></p>
          {activeWindow.left !== undefined && (
            <p className="mono small">Pos: ({activeWindow.left}, {activeWindow.top}) Size: {activeWindow.width}x{activeWindow.height}</p>
          )}
          {dialogs.length > 0 && (
            <>
              <h4>Detected Dialogs</h4>
              {dialogs.map((d, i) => (
                <div key={i} className="alert alert-warning">{d.title}</div>
              ))}
            </>
          )}
        </div>
      )}

      {tab === 'mouse' && (
        <div className="card">
          <h3>Mouse Control</h3>
          <div className="row">
            <input type="number" value={mouseX} onChange={e => setMouseX(Number(e.target.value))} placeholder="X" />
            <input type="number" value={mouseY} onChange={e => setMouseY(Number(e.target.value))} placeholder="Y" />
            <button onClick={moveMouse}>Move</button>
          </div>
          <div className="row">
            <button onClick={() => clickMouse('left')}>Left Click</button>
            <button onClick={() => clickMouse('right')}>Right Click</button>
            <button onClick={() => clickMouse('middle')}>Middle Click</button>
          </div>
          <p>Position: ({mousePos.x || 0}, {mousePos.y || 0})</p>
        </div>
      )}

      {tab === 'keyboard' && (
        <div className="card">
          <h3>Keyboard Control</h3>
          <div className="form-group">
            <label>Type Text</label>
            <textarea value={typeText} onChange={e => setTypeText(e.target.value)} rows={3} placeholder="Text to type..." />
            <button onClick={typeKeyboard}>Type</button>
          </div>
          <div className="form-group">
            <label>Hotkey</label>
            <div className="row">
              <input value={hotkeyText} onChange={e => setHotkeyText(e.target.value)} placeholder="e.g., ctrl+c, alt+tab, win+d" className="flex-1" />
              <button onClick={sendHotkey}>Send</button>
            </div>
          </div>

          <h4>Clipboard</h4>
          <div className="row">
            <button onClick={readClipboard}>Read</button>
            <button onClick={writeClipboard}>Write</button>
          </div>
          <textarea value={clipboard} onChange={e => setClipboard(e.target.value)} rows={3} placeholder="Clipboard contents..." className="w-full" />
        </div>
      )}

      {tab === 'windows' && (
        <div className="card">
          <h3>Window Management</h3>
          <div className="row">
            <input value={focusTitle} onChange={e => setFocusTitle(e.target.value)} placeholder="Window title to focus" className="flex-1" />
            <button onClick={focusWindow}>Focus</button>
          </div>
          <h4>Open Windows ({windows.length})</h4>
          <table>
            <thead><tr><th>Title</th><th>Position</th><th>Size</th></tr></thead>
            <tbody>
              {windows.slice(0, 30).map((w, i) => (
                <tr key={i}>
                  <td className="mono">{w.title?.slice(0, 60)}</td>
                  <td className="mono small">{w.left !== undefined ? `(${w.left}, ${w.top})` : '-'}</td>
                  <td className="mono small">{w.width ? `${w.width}x${w.height}` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'apps' && (
        <div className="card">
          <h3>Application Management</h3>
          <div className="form-group">
            <label>Launch App</label>
            <div className="row">
              <input value={appPath} onChange={e => setAppPath(e.target.value)} placeholder="Path to executable" className="flex-1" />
              <button onClick={launchApp}>Launch</button>
            </div>
          </div>

          <h4>Screen OCR</h4>
          <div className="row">
            <button onClick={getScreenText}>Capture Screen Text</button>
            <button onClick={clickText} disabled>Click Text (OCR)</button>
          </div>
          <input value={clickTextStr} onChange={e => setClickTextStr(e.target.value)} placeholder="Text to click" />
          {screenText && <pre className="pre-wrap">{screenText}</pre>}

          <h4>Running Apps (<span className={mode !== 'autonomous' ? 'muted' : ''}>{runningApps.length})</span></h4>
          {mode === 'autonomous' ? (
            <table>
              <thead><tr><th>Name</th><th>PID</th><th>CPU%</th><th>Memory%</th></tr></thead>
              <tbody>
                {runningApps.slice(0, 20).map((a, i) => (
                  <tr key={i}>
                    <td className="mono">{a.name}</td>
                    <td>{a.pid}</td>
                    <td>{a.cpu?.toFixed(1)}</td>
                    <td>{a.memory?.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="muted">Switch to Autonomous mode to view process list.</p>
          )}
        </div>
      )}

      {tab === 'mode' && (
        <div className="card">
          <h3>Assistant Mode</h3>
          <div className="mode-selector">
            <div className="card" onClick={() => setDesktopMode('safe')} style={{ borderColor: mode === 'safe' ? '#10b981' : '#374151' }}>
              <h3>🛡️ Safe Mode</h3>
              <p>Read-only assistance. No automation. Safe for all use.</p>
              {mode === 'safe' && <span className="tag bg-green">Active</span>}
            </div>
            <div className="card" onClick={() => setDesktopMode('developer')} style={{ borderColor: mode === 'developer' ? '#f59e0b' : '#374151' }}>
              <h3>⚙️ Developer Mode</h3>
              <p>Controlled automation with approval gates. Best for development.</p>
              {mode === 'developer' && <span className="tag bg-yellow">Active</span>}
            </div>
            <div className="card" onClick={() => setDesktopMode('autonomous')} style={{ borderColor: mode === 'autonomous' ? '#ef4444' : '#374151' }}>
              <h3>🤖 Autonomous Mode</h3>
              <p>Advanced automation. All actions require approval. Use with caution.</p>
              {mode === 'autonomous' && <span className="tag bg-red">Active</span>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
