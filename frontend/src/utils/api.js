const BASE = '/api';

async function request(path, options = {}) {
  const url = `${BASE}${path}`;
  const config = {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  };
  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }
  const res = await fetch(url, config);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res;
}

export const api = {
  // Status
  getStatus: () => request('/status').then(r => r.json()),

  // Models
  getModels: () => request('/models').then(r => r.json()),
  setModel: (model) => request('/models/set', { method: 'POST', body: { model } }).then(r => r.json()),

  // Chat
  sendMessage: (message, history = []) => {
    return request('/chat', {
      method: 'POST',
      body: { message, history, stream: true },
    });
  },

  // Memory
  getMemories: (type = '', limit = 50) =>
    request(`/memory?type=${type}&limit=${limit}`).then(r => r.json()),
  createMemory: (type, content, metadata = {}) =>
    request('/memory', { method: 'POST', body: { type, content, metadata } }).then(r => r.json()),
  searchMemory: (query, type = null, limit = 20) =>
    request('/memory/search', { method: 'POST', body: { query, type, limit } }).then(r => r.json()),
  deleteMemory: (id) => request(`/memory/${id}`, { method: 'DELETE' }).then(r => r.json()),
  clearMemory: () => request('/memory', { method: 'DELETE' }).then(r => r.json()),
  exportMemory: () => request('/memory/export').then(r => r.json()),

  // Skills
  getSkills: () => request('/skills').then(r => r.json()),
  toggleSkill: (name, enabled) =>
    request('/skills/toggle', { method: 'POST', body: { name, enabled } }).then(r => r.json()),
  installSkill: (source) =>
    request('/skills/install', { method: 'POST', body: { source } }).then(r => r.json()),
  uninstallSkill: (name) =>
    request('/skills/uninstall', { method: 'POST', body: { name } }).then(r => r.json()),
  reloadSkills: () => request('/skills/reload', { method: 'POST' }).then(r => r.json()),
  executeSkill: (skillName, command, args = {}) =>
    request('/skills/execute', { method: 'POST', body: { skill_name: skillName, command, args } }).then(r => r.json()),

  // Permissions
  getPendingPermissions: () => request('/permissions/pending').then(r => r.json()),
  respondPermission: (actionId, approved) =>
    request('/permissions/respond', { method: 'POST', body: { action_id: actionId, approved } }).then(r => r.json()),

  // Config
  getConfig: () => request('/config').then(r => r.json()),
  updateConfig: (key, value) =>
    request('/config', { method: 'POST', body: { key, value } }).then(r => r.json()),

  // System
  getSystemInfo: () => request('/system/info').then(r => r.json()),

  // Preferences
  getPreferences: () => request('/preferences').then(r => r.json()),
  setPreference: (key, value) =>
    request('/preferences', { method: 'POST', body: { key, value } }).then(r => r.json()),

  // Shell
  runShell: (command, description = '') =>
    request('/shell', { method: 'POST', body: { command, description } }).then(r => r.json()),

  // Tools (Phase 3)
  getTools: () => request('/tools').then(r => r.json()),
  getTool: (name) => request(`/tools/${name}`).then(r => r.json()),
  getToolActivity: (limit = 100) => request(`/tools/activity?limit=${limit}`).then(r => r.json()),

  // Background Daemon (Phase 2)
  getBackgroundStatus: () => request('/background/status').then(r => r.json()),
  restartBackground: () => request('/background/restart', { method: 'POST' }).then(r => r.json()),

  // Events
  getEvents: (limit = 100, type = '') => request(`/events?limit=${limit}${type ? `&type=${type}` : ''}`).then(r => r.json()),
  publishEvent: (type, payload = {}, sender = 'api') =>
    request('/events/publish', { method: 'POST', body: { type, payload, sender } }).then(r => r.json()),

  // Scheduler
  getScheduledTasks: () => request('/scheduler/tasks').then(r => r.json()),
  createScheduledTask: (data) => request('/scheduler/tasks', { method: 'POST', body: data }).then(r => r.json()),
  deleteScheduledTask: (id) => request(`/scheduler/tasks/${id}`, { method: 'DELETE' }).then(r => r.json()),

  // Observers
  getObservers: () => request('/observers').then(r => r.json()),
  toggleObserver: (name, enabled) =>
    request(`/observers/${name}/toggle`, { method: 'POST', body: { enabled } }).then(r => r.json()),

  // Notifications
  getNotifications: (limit = 50, unreadOnly = false) =>
    request(`/notifications?limit=${limit}&unread_only=${unreadOnly}`).then(r => r.json()),
  markNotificationRead: (id) => request(`/notifications/${id}/read`, { method: 'POST' }).then(r => r.json()),
  markAllNotificationsRead: () => request('/notifications/read-all', { method: 'POST' }).then(r => r.json()),
  clearNotifications: () => request('/notifications', { method: 'DELETE' }).then(r => r.json()),

  // Queue
  getQueueStatus: () => request('/queue/status').then(r => r.json()),
  getQueueCompleted: (limit = 50) => request(`/queue/completed?limit=${limit}`).then(r => r.json()),

  // Workflows (Phase 2)
  getWorkflowsV2: () => request('/workflows').then(r => r.json()),
  createWorkflowV2: (data) => request('/workflows', { method: 'POST', body: data }).then(r => r.json()),
  getWorkflowV2: (id) => request(`/workflows/${id}`).then(r => r.json()),
  deleteWorkflowV2: (id) => request(`/workflows/${id}`, { method: 'DELETE' }).then(r => r.json()),
  runWorkflowV2: (id) => request(`/workflows/${id}/run`, { method: 'POST' }).then(r => r.json()),
  cancelWorkflowV2: (id) => request(`/workflows/${id}/cancel`, { method: 'POST' }).then(r => r.json()),

  // Background Agent
  getBackgroundSuggestion: () => request('/background/suggest', { method: 'POST' }).then(r => r.json()),
  getSuggestions: (limit = 20) => request(`/background/suggestions?limit=${limit}`).then(r => r.json()),

  // MCP (Phase 5)
  getMCPServers: () => request('/mcp/servers').then(r => r.json()),
  connectMCPServer: (name) => request('/mcp/servers/connect', { method: 'POST', body: { name } }).then(r => r.json()),
  disconnectMCPServer: (name) => request('/mcp/servers/disconnect', { method: 'POST', body: { name } }).then(r => r.json()),
  registerMCPServer: (config) => request('/mcp/servers/register', { method: 'POST', body: config }).then(r => r.json()),
  removeMCPServer: (name) => request(`/mcp/servers/${name}`, { method: 'DELETE' }).then(r => r.json()),
  trustMCPServer: (name) => request(`/mcp/servers/${name}/trust`, { method: 'POST' }).then(r => r.json()),
  untrustMCPServer: (name) => request(`/mcp/servers/${name}/untrust`, { method: 'POST' }).then(r => r.json()),
  getMCPTools: () => request('/mcp/tools').then(r => r.json()),
  callMCPTool: (serverName, toolName, args) =>
    request('/mcp/tools/call', { method: 'POST', body: { server_name: serverName, tool_name: toolName, args } }).then(r => r.json()),
  discoverMCPServers: () => request('/mcp/discover').then(r => r.json()),
  installDiscoveredMCP: (type) => request('/mcp/discover/install', { method: 'POST', body: { type } }).then(r => r.json()),

  // Coding (Phase 6)
  indexProject: (path, recursive = true) => request('/coding/index', { method: 'POST', body: { path, recursive } }).then(r => r.json()),
  listIndexes: () => request('/coding/indexes').then(r => r.json()),
  searchCode: (query, path) => request('/coding/search', { method: 'POST', body: { query, path } }).then(r => r.json()),
  indexCodeSemantic: (path) => request('/coding/semantic/index', { method: 'POST', body: { path } }).then(r => r.json()),
  createPatch: (filePath, newContent, description) =>
    request('/coding/patch', { method: 'POST', body: { file_path: filePath, new_content: newContent, description } }).then(r => r.json()),
  getPatches: () => request('/coding/patches').then(r => r.json()),
  approvePatch: (id) => request(`/coding/patches/${id}/approve`, { method: 'POST' }).then(r => r.json()),
  applyPatch: (id) => request(`/coding/patches/${id}/apply`, { method: 'POST' }).then(r => r.json()),
  revertPatch: (id) => request(`/coding/patches/${id}/revert`, { method: 'POST' }).then(r => r.json()),
  validateSyntax: (code, language = 'python') => request('/coding/validate', { method: 'POST', body: { code, language } }).then(r => r.json()),
  gitStatus: (path) => request(`/coding/git/status?path=${encodeURIComponent(path)}`).then(r => r.json()),
  gitLog: (path, maxCount = 20) => request(`/coding/git/log?path=${encodeURIComponent(path)}&max_count=${maxCount}`).then(r => r.json()),
  gitDiff: (path, target = 'HEAD') => request(`/coding/git/diff?path=${encodeURIComponent(path)}&target=${target}`).then(r => r.json()),
  gitCommit: (path, message) => request('/coding/git/commit', { method: 'POST', body: { path, message } }).then(r => r.json()),
  gitCreateBranch: (path, branch) => request('/coding/git/branch', { method: 'POST', body: { path, branch } }).then(r => r.json()),
  analyzeDeps: (path) => request('/coding/deps', { method: 'POST', body: { path } }).then(r => r.json()),
  depGraph: (path) => request(`/coding/deps/graph?path=${encodeURIComponent(path)}`).then(r => r.json()),
  getWorkspaces: () => request('/coding/workspaces').then(r => r.json()),
  createWorkspace: (name, path, description) =>
    request('/coding/workspaces', { method: 'POST', body: { name, path, description } }).then(r => r.json()),
  deleteWorkspace: (id) => request(`/coding/workspaces/${id}`, { method: 'DELETE' }).then(r => r.json()),
  codeMemoryStats: () => request('/coding/memory/stats').then(r => r.json()),

  // Vision (Phase 7)
  captureScreen: (mode = 'full') => request('/vision/capture', { method: 'POST', body: { mode } }).then(r => r.json()),
  getScreenshots: (limit = 20) => request(`/vision/screenshots?limit=${limit}`).then(r => r.json()),
  deleteScreenshot: (id) => request(`/vision/screenshots/${id}`, { method: 'DELETE' }).then(r => r.json()),
  extractText: (imagePath) => request('/vision/ocr', { method: 'POST', body: { image_path: imagePath } }).then(r => r.json()),
  analyzeImage: (imagePath, prompt = 'Describe this image') =>
    request('/vision/analyze', { method: 'POST', body: { image_path: imagePath, prompt } }).then(r => r.json()),
  detectUI: (imagePath) => request('/vision/ui-detect', { method: 'POST', body: { image_path: imagePath } }).then(r => r.json()),
  getDesktopContext: () => request('/vision/context').then(r => r.json()),
  refreshDesktopContext: () => request('/vision/context/refresh', { method: 'POST' }).then(r => r.json()),
  getVisualMemory: (limit = 20) => request(`/vision/memory?limit=${limit}`).then(r => r.json()),
  storeVisualMemory: (imagePath, summary, metadata) =>
    request('/vision/memory', { method: 'POST', body: { image_path: imagePath, summary, metadata } }).then(r => r.json()),
  deleteVisualMemory: (id) => request(`/vision/memory/${id}`, { method: 'DELETE' }).then(r => r.json()),
  listWindows: () => request('/vision/windows').then(r => r.json()),
  getVisionStatus: () => request('/vision/status').then(r => r.json()),

  // Browser Worker (Phase 8)
  getBrowserSessions: () => request('/browser/sessions').then(r => r.json()),
  createBrowserSession: (headless = false) =>
    request('/browser/sessions', { method: 'POST', body: { headless } }).then(r => r.json()),
  browserGoto: (sessionId, url) =>
    request(`/browser/sessions/${sessionId}/goto`, { method: 'POST', body: { url } }).then(r => r.json()),
  browserClick: (sessionId, selector, text, xpath) =>
    request(`/browser/sessions/${sessionId}/click`, { method: 'POST', body: { selector, text, xpath } }).then(r => r.json()),
  browserFill: (sessionId, selector, value) =>
    request(`/browser/sessions/${sessionId}/fill`, { method: 'POST', body: { selector, value } }).then(r => r.json()),
  browserScreenshot: (sessionId) =>
    request(`/browser/sessions/${sessionId}/screenshot`, { method: 'POST' }).then(r => r.blob()),
  browserPageInfo: (sessionId) =>
    request(`/browser/sessions/${sessionId}/page`).then(r => r.json()),
  browserSummarize: (sessionId) =>
    request(`/browser/sessions/${sessionId}/summarize`, { method: 'POST' }).then(r => r.json()),
  browserScrape: (sessionId, selectors) =>
    request(`/browser/sessions/${sessionId}/scrape`, { method: 'POST', body: { selectors } }).then(r => r.json()),
  browserTestLinks: (sessionId) =>
    request(`/browser/sessions/${sessionId}/test-links`, { method: 'POST' }).then(r => r.json()),
  browserSeoAudit: (sessionId) =>
    request(`/browser/sessions/${sessionId}/seo-audit`, { method: 'POST' }).then(r => r.json()),
  browserLinks: (sessionId) =>
    request(`/browser/sessions/${sessionId}/links`).then(r => r.json()),
  browserForms: (sessionId) =>
    request(`/browser/sessions/${sessionId}/forms`).then(r => r.json()),
  browserFillFormSafe: (sessionId, formIndex, values, approved) =>
    request(`/browser/sessions/${sessionId}/fill-form-safe`, { method: 'POST', body: { form_index: formIndex, values, approved } }).then(r => r.json()),
  browserCheckElement: (sessionId, selector, text) =>
    request(`/browser/sessions/${sessionId}/check-element`, { method: 'POST', body: { selector, text } }).then(r => r.json()),
  browserNewPage: (sessionId) =>
    request(`/browser/sessions/${sessionId}/new-page`, { method: 'POST' }).then(r => r.json()),
  closeBrowserSession: (sessionId) =>
    request(`/browser/sessions/${sessionId}`, { method: 'DELETE' }).then(r => r.json()),
  closeAllBrowserSessions: () =>
    request('/browser/sessions', { method: 'DELETE' }).then(r => r.json()),
  browserActionHistory: (sessionId, limit = 100) =>
    request(`/browser/history?session_id=${sessionId || ''}&limit=${limit}`).then(r => r.json()),
  browserCheckUptime: (url) =>
    request('/browser/uptime', { method: 'POST', body: { url } }).then(r => r.json()),
  browserLoginSessions: () =>
    request('/browser/login-sessions').then(r => r.json()),
  browserReplay: (sessionId) =>
    request(`/browser/sessions/${sessionId}/replay`, { method: 'POST' }).then(r => r.json()),

  // Hybrid Memory (Phase 9)
  getHybridMemory: (type, project, limit = 50) =>
    request(`/hybrid-memory/entries?type=${type || ''}&project=${project || ''}&limit=${limit}`).then(r => r.json()),
  addHybridMemory: (type, content, metadata, project) =>
    request('/hybrid-memory/add', { method: 'POST', body: { type, content, metadata, project } }).then(r => r.json()),
  searchHybridMemory: (query, type, limit = 20) =>
    request('/hybrid-memory/search', { method: 'POST', body: { query, type, limit } }).then(r => r.json()),
  getHybridMemoryEntry: (id) =>
    request(`/hybrid-memory/entry/${id}`).then(r => r.json()),
  updateHybridMemory: (id, content, metadata, importance) =>
    request(`/hybrid-memory/entry/${id}`, { method: 'PUT', body: { content, metadata, importance } }).then(r => r.json()),
  deleteHybridMemory: (id) =>
    request(`/hybrid-memory/entry/${id}`, { method: 'DELETE' }).then(r => r.json()),
  clearHybridMemory: (type) =>
    request(`/hybrid-memory?type=${type || ''}`, { method: 'DELETE' }).then(r => r.json()),
  exportHybridMemory: (type, project) =>
    request(`/hybrid-memory/export?type=${type || ''}&project=${project || ''}`).then(r => r.json()),
  importHybridMemory: (entries) =>
    request('/hybrid-memory/import', { method: 'POST', body: { entries } }).then(r => r.json()),
  cleanupHybridMemory: (days = 90) =>
    request('/hybrid-memory/cleanup', { method: 'POST', body: { days } }).then(r => r.json()),
  getHybridMemoryProjects: () =>
    request('/hybrid-memory/projects').then(r => r.json()),
  getHybridMemoryCategories: () =>
    request('/hybrid-memory/categories').then(r => r.json()),
  getHybridMemoryTimeline: (days, type) =>
    request('/hybrid-memory/timeline', { method: 'POST', body: { days, type } }).then(r => r.json()),

  // Learning (Phase 10)
  getLearningFailures: () => request('/learning/failures').then(r => r.json()),
  recordFailure: (action, tool, error, context, taskId) =>
    request('/learning/failure/record', { method: 'POST', body: { action, tool, error, context, task_id: taskId } }).then(r => r.json()),
  getLearningSuggestions: () => request('/learning/suggestions').then(r => r.json()),
  getRecentWorkflows: (limit) => request(`/learning/workflows/recent?limit=${limit || 50}`).then(r => r.json()),
  recordWorkflow: (steps, source) =>
    request('/learning/workflow/record', { method: 'POST', body: { steps, source } }).then(r => r.json()),
  getLearningAutomationSuggestions: () => request('/learning/automation-suggestions').then(r => r.json()),
  getLearningWorkflowStats: () => request('/learning/workflow-stats').then(r => r.json()),
  recordPrompt: (prompt, context, taskType, outcome, quality) =>
    request('/learning/prompt/record', { method: 'POST', body: { prompt, context, task_type: taskType, outcome, response_quality: quality } }).then(r => r.json()),
  optimizePrompt: (prompt, taskType) =>
    request('/learning/prompt/optimize', { method: 'POST', body: { prompt, task_type: taskType } }).then(r => r.json()),
  getPromptTemplates: () => request('/learning/prompt/templates').then(r => r.json()),
  savePromptTemplate: (name, template) =>
    request('/learning/prompt/templates', { method: 'POST', body: { name, template } }).then(r => r.json()),
  getLearningRecommendations: () => request('/learning/recommendations').then(r => r.json()),
  dismissRecommendation: (id) =>
    request('/learning/recommendations/dismiss', { method: 'POST', body: { id } }).then(r => r.json()),
  logUsage: (category, item, context) =>
    request('/learning/usage/log', { method: 'POST', body: { category, item, context } }).then(r => r.json()),
  getLearningUsageStats: () => request('/learning/usage/stats').then(r => r.json()),
  getLearningCorrections: () => request('/learning/corrections').then(r => r.json()),
  recordCorrection: (action, correction, context) =>
    request('/learning/correction/record', { method: 'POST', body: { action, correction, context } }).then(r => r.json()),

  // Model Router (Phase 11)
  getRouterStatus: () => request('/models/router-status').then(r => r.json()),
  analyzeTask: (task, agentName) =>
    request('/models/analyze-task', { method: 'POST', body: { task, agent_name: agentName } }).then(r => r.json()),
  forceModel: (model) => request('/models/force', { method: 'POST', body: { model } }).then(r => r.json()),
  releaseForceModel: () => request('/models/release-force', { method: 'POST' }).then(r => r.json()),
  disableModel: (model) => request('/models/disable', { method: 'POST', body: { model } }).then(r => r.json()),
  enableModel: (model) => request('/models/enable', { method: 'POST', body: { model } }).then(r => r.json()),
  getModelHealth: () => request('/models/health').then(r => r.json()),
  getModelHealthDetail: (model) => request(`/models/health/${model}`).then(r => r.json()),
  setBalancerStrategy: (strategy) =>
    request('/models/balancer/strategy', { method: 'POST', body: { strategy } }).then(r => r.json()),
  getInstalledModels: () => request('/models/installed').then(r => r.json()),
  warmUpModel: (model) => request('/models/warm-up', { method: 'POST', body: { model } }).then(r => r.json()),
  getFallbackChains: () => request('/models/fallback-chains').then(r => r.json()),

  // Desktop Control (Phase 12)
  getDesktopState: () => request('/desktop/state').then(r => r.json()),
  getRunningApps: () => request('/desktop/running-apps').then(r => r.json()),
  getActiveWindow: () => request('/desktop/active-window').then(r => r.json()),
  listDesktopWindows: () => request('/desktop/windows').then(r => r.json()),
  focusWindow: (title) => request('/desktop/windows/focus', { method: 'POST', body: { title } }).then(r => r.json()),
  minimizeWindow: (title) => request('/desktop/windows/minimize', { method: 'POST', body: { title } }).then(r => r.json()),
  maximizeWindow: (title) => request('/desktop/windows/maximize', { method: 'POST', body: { title } }).then(r => r.json()),
  closeDesktopWindow: (title) => request('/desktop/windows/close', { method: 'POST', body: { title } }).then(r => r.json()),
  moveMouse: (x, y) => request('/desktop/mouse/move', { method: 'POST', body: { x, y } }).then(r => r.json()),
  clickMouse: (button, x, y) =>
    request('/desktop/mouse/click', { method: 'POST', body: { button, x, y } }).then(r => r.json()),
  doubleClickMouse: (x, y) => request('/desktop/mouse/double-click', { method: 'POST', body: { x, y } }).then(r => r.json()),
  rightClickMouse: (x, y) => request('/desktop/mouse/right-click', { method: 'POST', body: { x, y } }).then(r => r.json()),
  dragMouse: (sx, sy, ex, ey) =>
    request('/desktop/mouse/drag', { method: 'POST', body: { start_x: sx, start_y: sy, end_x: ex, end_y: ey } }).then(r => r.json()),
  scrollMouse: (clicks) => request('/desktop/mouse/scroll', { method: 'POST', body: { clicks } }).then(r => r.json()),
  getMousePosition: () => request('/desktop/mouse/position').then(r => r.json()),
  typeText: (text) => request('/desktop/keyboard/type', { method: 'POST', body: { text } }).then(r => r.json()),
  sendHotkey: (keys) => request('/desktop/keyboard/hotkey', { method: 'POST', body: { keys } }).then(r => r.json()),
  pressKey: (key, times) =>
    request('/desktop/keyboard/press', { method: 'POST', body: { key, times } }).then(r => r.json()),
  readClipboard: () => request('/desktop/clipboard').then(r => r.json()),
  writeClipboard: (text) => request('/desktop/clipboard', { method: 'POST', body: { text } }).then(r => r.json()),
  clearClipboard: () => request('/desktop/clipboard/clear', { method: 'POST' }).then(r => r.json()),
  detectDialogs: () => request('/desktop/dialogs').then(r => r.json()),
  getFocusedApp: () => request('/desktop/focused-app').then(r => r.json()),
  setDesktopMode: (mode) => request('/desktop/mode', { method: 'POST', body: { mode } }).then(r => r.json()),
  getDesktopMode: () => request('/desktop/mode').then(r => r.json()),
  launchApp: (appPath, args) =>
    request('/desktop/launch-app', { method: 'POST', body: { app_path: appPath, args } }).then(r => r.json()),
  getScreenText: () => request('/desktop/screen-text', { method: 'POST' }).then(r => r.json()),
  clickTextOnScreen: (text) => request('/desktop/click-text', { method: 'POST', body: { text } }).then(r => r.json()),
};
