/**
 * JARVIS Electron Main Process
 * Window management, system tray, IPC, voice wake word, auto-start
 */
const { app, BrowserWindow, Tray, Menu, ipcMain, nativeImage, Notification, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const Store = require('electron-store');

const store = new Store({
  defaults: {
    startWithWindows: false,
    minimizeToTray: true,
    windowBounds: { width: 1200, height: 800 },
    backendPort: 8765,
    theme: 'dark'
  }
});

let mainWindow = null;
let tray = null;
let backendProcess = null;
let isQuitting = false;

// --- Backend Management ---

function startBackend() {
  const backendPath = path.join(__dirname, '..', '..', 'backend', 'main.py');
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  backendProcess = spawn(pythonCmd, [backendPath, '--port', store.get('backendPort').toString()], {
    cwd: path.join(__dirname, '..', '..', 'backend'),
    stdio: ['pipe', 'pipe', 'pipe']
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`[Backend] ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[Backend] ${data}`);
  });

  backendProcess.on('close', (code) => {
    console.log(`Backend exited with code ${code}`);
    if (!isQuitting) {
      setTimeout(startBackend, 2000);
    }
  });
}

function stopBackend() {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
}

// --- Window ---

function createWindow() {
  const bounds = store.get('windowBounds');

  mainWindow = new BrowserWindow({
    width: bounds.width,
    height: bounds.height,
    minWidth: 800,
    minHeight: 600,
    frame: false,
    transparent: false,
    backgroundColor: '#0a0a0f',
    icon: path.join(__dirname, '..', 'assets', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    },
    title: 'JARVIS'
  });

  // Load the React frontend
  const isDev = process.argv.includes('--dev');
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  } else {
    const frontendPath = path.join(__dirname, '..', '..', 'frontend', 'dist', 'index.html');
    mainWindow.loadFile(frontendPath);
  }

  mainWindow.on('close', (e) => {
    if (!isQuitting && store.get('minimizeToTray')) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('resize', () => {
    const [width, height] = mainWindow.getSize();
    store.set('windowBounds', { width, height });
  });
}

// --- System Tray ---

function createTray() {
  // Create a simple 16x16 tray icon
  const icon = nativeImage.createEmpty();
  tray = new Tray(icon);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open JARVIS',
      click: () => {
        if (mainWindow) mainWindow.show();
      }
    },
    { type: 'separator' },
    {
      label: 'Start with Windows',
      type: 'checkbox',
      checked: store.get('startWithWindows'),
      click: (item) => {
        store.set('startWithWindows', item.checked);
        app.setLoginItemSettings({ openAtLogin: item.checked });
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        isQuitting = true;
        stopBackend();
        app.quit();
      }
    }
  ]);

  tray.setToolTip('JARVIS - Local AI Assistant');
  tray.setContextMenu(contextMenu);

  tray.on('double-click', () => {
    if (mainWindow) mainWindow.show();
  });
}

// --- IPC Handlers ---

function setupIPC() {
  ipcMain.handle('window:minimize', () => {
    if (mainWindow) mainWindow.minimize();
  });

  ipcMain.handle('window:maximize', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
      } else {
        mainWindow.maximize();
      }
    }
  });

  ipcMain.handle('window:close', () => {
    if (mainWindow && store.get('minimizeToTray')) {
      mainWindow.hide();
    } else {
      mainWindow.close();
    }
  });

  ipcMain.handle('window:is-maximized', () => {
    return mainWindow ? mainWindow.isMaximized() : false;
  });

  ipcMain.handle('app:get-config', () => {
    return store.store;
  });

  ipcMain.handle('app:set-config', (event, key, value) => {
    store.set(key, value);
    if (key === 'startWithWindows') {
      app.setLoginSettings({ openAtLogin: value });
    }
    return { success: true };
  });

  ipcMain.handle('app:get-backend-url', () => {
    return `http://127.0.0.1:${store.get('backendPort')}`;
  });

  ipcMain.handle('app:notify', (event, title, body) => {
    new Notification({ title, body }).show();
  });

  ipcMain.handle('app:open-external', (event, url) => {
    shell.openExternal(url);
  });

  ipcMain.handle('app:stop-backend', () => {
    stopBackend();
    return { success: true };
  });

  ipcMain.handle('app:restart-backend', () => {
    stopBackend();
    setTimeout(startBackend, 1000);
    return { success: true };
  });
}

// --- App Lifecycle ---

app.whenReady().then(() => {
  setupIPC();
  startBackend();
  createWindow();
  createTray();

  // Auto-start with Windows
  if (store.get('startWithWindows')) {
    app.setLoginItemSettings({ openAtLogin: true });
  }

  app.on('activate', () => {
    if (mainWindow) mainWindow.show();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin' && !store.get('minimizeToTray')) {
    app.quit();
  }
});

app.on('before-quit', () => {
  isQuitting = true;
  stopBackend();
});

app.on('will-quit', () => {
  stopBackend();
});
