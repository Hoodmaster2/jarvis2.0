/**
 * JARVIS Preload Script
 * Exposes safe IPC methods to the renderer process.
 */
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('jarvis', {
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    maximize: () => ipcRenderer.invoke('window:maximize'),
    close: () => ipcRenderer.invoke('window:close'),
    isMaximized: () => ipcRenderer.invoke('window:is-maximized'),
  },
  config: {
    get: () => ipcRenderer.invoke('app:get-config'),
    set: (key, value) => ipcRenderer.invoke('app:set-config', key, value),
  },
  backend: {
    getUrl: () => ipcRenderer.invoke('app:get-backend-url'),
    stop: () => ipcRenderer.invoke('app:stop-backend'),
    restart: () => ipcRenderer.invoke('app:restart-backend'),
  },
  notify: (title, body) => ipcRenderer.invoke('app:notify', title, body),
  openExternal: (url) => ipcRenderer.invoke('app:open-external', url),
});
