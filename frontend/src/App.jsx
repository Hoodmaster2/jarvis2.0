import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import StatusPanel from './components/StatusPanel';
import Chat from './pages/Chat';
import Voice from './pages/Voice';
import Skills from './pages/Skills';
import Agents from './pages/Agents';
import AgentDashboard from './pages/AgentDashboard';
import WorkflowTimeline from './pages/WorkflowTimeline';
import Browser from './pages/Browser';
import Files from './pages/Files';
import CodingWorkspace from './pages/CodingWorkspace';
import Memory from './pages/Memory';
import Settings from './pages/Settings';
import Logs from './pages/Logs';
import ToolActivity from './pages/ToolActivity';
import Automations from './pages/Automations';
import SchedulerPage from './pages/SchedulerPage';
import BackgroundActivity from './pages/BackgroundActivity';
import NotificationsPage from './pages/NotificationsPage';
import MCPMarketplace from './pages/MCPMarketplace';
import CodingExplorer from './pages/CodingExplorer';
import VisionDashboard from './pages/VisionDashboard';
import BrowserWorker from './pages/BrowserWorker';
import HybridMemory from './pages/HybridMemory';
import LearningDashboard from './pages/LearningDashboard';
import ModelDashboard from './pages/ModelDashboard';
import DesktopControl from './pages/DesktopControl';
import './styles/theme.css';

function AppContent() {
  const navigate = useNavigate();
  const location = useLocation();
  const [backendStatus, setBackendStatus] = useState({ connected: false, model: 'qwen3', skillsCount: 0 });
  const [showStatus, setShowStatus] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);

  useEffect(() => {
    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const checkStatus = async () => {
    try {
      const res = await fetch('/api/status');
      if (res.ok) {
        const data = await res.json();
        setBackendStatus({
          connected: data.ollama_connected,
          model: data.model,
          skillsCount: data.skills_count,
          platform: data.platform,
        });
      }
    } catch {
      setBackendStatus(prev => ({ ...prev, connected: false }));
    }
  };

  const handleTitleBarAction = async (action) => {
    if (window.jarvis?.window) {
      await window.jarvis.window[action]();
      if (action === 'maximize') {
        setIsMaximized(await window.jarvis.window.isMaximized());
      }
    }
  };

  return (
    <div className="app-container">
      {/* Title Bar */}
      <div className="title-bar">
        <div className="title-bar-drag">
          <span className="title-bar-icon">◆</span>
          <span>JARVIS</span>
        </div>
        <div className="title-bar-actions">
          <button onClick={() => setShowStatus(!showStatus)} className="title-btn" title="Status">
            <span className={`status-dot ${backendStatus.connected ? 'connected' : 'disconnected'}`} />
          </button>
          <button onClick={() => handleTitleBarAction('minimize')} className="title-btn">─</button>
          <button onClick={() => handleTitleBarAction('maximize')} className="title-btn">
            {isMaximized ? '❐' : '□'}
          </button>
          <button onClick={() => handleTitleBarAction('close')} className="title-btn close">✕</button>
        </div>
      </div>

      <div className="app-layout">
        <Sidebar currentPath={location.pathname} onNavigate={navigate} />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Chat />} />
            <Route path="/voice" element={<Voice />} />
            <Route path="/skills" element={<Skills />} />
            <Route path="/agents" element={<AgentDashboard />} />
            <Route path="/workflows" element={<WorkflowTimeline />} />
            <Route path="/browser" element={<Browser />} />
            <Route path="/files" element={<Files />} />
            <Route path="/coding" element={<CodingWorkspace />} />
            <Route path="/memory" element={<Memory />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/tools" element={<ToolActivity />} />
            <Route path="/automations" element={<Automations />} />
            <Route path="/scheduler" element={<SchedulerPage />} />
            <Route path="/background" element={<BackgroundActivity />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/mcp" element={<MCPMarketplace />} />
            <Route path="/coding-explorer" element={<CodingExplorer />} />
            <Route path="/vision" element={<VisionDashboard />} />
            <Route path="/browser-worker" element={<BrowserWorker />} />
            <Route path="/hybrid-memory" element={<HybridMemory />} />
            <Route path="/learning" element={<LearningDashboard />} />
            <Route path="/model-dashboard" element={<ModelDashboard />} />
            <Route path="/desktop" element={<DesktopControl />} />
          </Routes>
        </main>
        {showStatus && (
          <StatusPanel status={backendStatus} onClose={() => setShowStatus(false)} />
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
