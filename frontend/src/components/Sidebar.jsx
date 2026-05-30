import React from 'react';

const navItems = [
  { section: 'Main', items: [
    { path: '/', label: 'Chat', icon: '💬' },
    { path: '/voice', label: 'Voice', icon: '🎤' },
  ]},
  { section: 'Tools', items: [
    { path: '/skills', label: 'Skills', icon: '🧩' },
    { path: '/agents', label: 'Agents', icon: '🤖' },
    { path: '/tools', label: 'Tool Activity', icon: '🔧' },
    { path: '/mcp', label: 'MCP Marketplace', icon: '🔌' },
    { path: '/workflows', label: 'Workflows', icon: '⏰' },
    { path: '/automations', label: 'Automations', icon: '⚡' },
    { path: '/browser-worker', label: 'Browser Worker', icon: '🌐' },
    { path: '/browser', label: 'Legacy Browser', icon: '🗺️' },
    { path: '/files', label: 'Files', icon: '📁' },
    { path: '/coding', label: 'Coding', icon: '💻' },
    { path: '/coding-explorer', label: 'Code Explorer', icon: '🔍' },
    { path: '/vision', label: 'Vision', icon: '👁️' },
    { path: '/desktop', label: 'Desktop Control', icon: '🖥️' },
  ]},
  { section: 'Intelligence', items: [
    { path: '/model-dashboard', label: 'Model Router', icon: '🧠' },
    { path: '/hybrid-memory', label: 'Hybrid Memory', icon: '💾' },
    { path: '/learning', label: 'Learning', icon: '📚' },
  ]},
  { section: 'Background', items: [
    { path: '/scheduler', label: 'Scheduler', icon: '📅' },
    { path: '/background', label: 'Background', icon: '🌀' },
    { path: '/notifications', label: 'Notifications', icon: '🔔' },
  ]},
  { section: 'Data', items: [
    { path: '/memory', label: 'Memory (Legacy)', icon: '🧠' },
    { path: '/logs', label: 'Logs', icon: '📋' },
  ]},
  { section: 'System', items: [
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ]},
];

export default function Sidebar({ currentPath, onNavigate }) {
  return (
    <nav className="sidebar">
      <div className="sidebar-nav">
        {navItems.map((section) => (
          <React.Fragment key={section.section}>
            <div className="sidebar-section-title">{section.section}</div>
            {section.items.map((item) => (
              <button
                key={item.path}
                className={`sidebar-item ${currentPath === item.path ? 'active' : ''}`}
                onClick={() => onNavigate(item.path)}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </React.Fragment>
        ))}
      </div>
    </nav>
  );
}
