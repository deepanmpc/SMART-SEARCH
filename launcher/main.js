const { app, BrowserWindow, globalShortcut, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const net = require('net');
const { spawn } = require('child_process');
const log = require('electron-log');

const CONFIG_PATH = path.join(app.getPath('userData'), 'config.json');

function loadConfig() {
  if (fs.existsSync(CONFIG_PATH)) {
    try {
      return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
    } catch (e) {
      log.error('Failed to parse config:', e);
    }
  }
  return {};
}

function saveConfig(config) {
  try {
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(config, null, 2));
  } catch (e) {
    log.error('Failed to save config:', e);
  }
}


// Setup logging
Object.assign(console, log.functions);
log.transports.file.level = 'info';

let mainWindow;
let backendProcess = null;
let backendPort = null;
let isBackendRestarting = false;
let isAutoRecoveringBackend = false;
let isAppQuitting = false;
let backendStatus = {
  state: 'stopped',
  executablePath: '',
  lastError: '',
  lastExitCode: null,
  lastExitSignal: null,
  pid: null,
  startedAt: null
};

function setBackendError(message) {
  backendStatus.state = 'error';
  backendStatus.lastError = message;
  log.error(message);
}

function scheduleAutoRecovery(reason) {
  if (isAppQuitting || isBackendRestarting || isAutoRecoveringBackend) return;
  isAutoRecoveringBackend = true;
  backendStatus.state = 'restarting';
  log.warn(`Scheduling backend auto-recovery: ${reason}`);
  if (backendProcess) {
    try {
      backendProcess.kill();
    } catch (_) {}
  }
  backendPort = null;
  setTimeout(() => {
    startBackend()
      .catch((err) => log.error('Backend auto-recovery failed:', err))
      .finally(() => { isAutoRecoveringBackend = false; });
  }, 1200);
}

function findAvailablePort() {
  return new Promise((resolve) => {
    const tester = net.createServer();
    tester.once('error', () => resolve(backendPort || 8000));
    tester.once('listening', () => {
      const address = tester.address();
      const port = typeof address === 'object' && address ? address.port : (backendPort || 8000);
      tester.close(() => resolve(port));
    });
    tester.listen(0, '127.0.0.1');
  });
}

async function startBackend() {
  const isPackaged = app.isPackaged;
  const config = loadConfig();
  const env = { ...process.env };
  env.SMART_SEARCH_DATA_DIR = app.getPath('userData');
  if (!backendPort) {
    backendPort = await findAvailablePort();
  }
  env.SMART_SEARCH_API_PORT = String(backendPort);
  
  if (config.google_api_key) {
    env.GOOGLE_API_KEY = config.google_api_key;
    env.GEMINI_API_KEY = config.google_api_key;
    log.info('Using Gemini API Key from config.');
  }

  if (isPackaged) {
    const exName = process.platform === 'win32' ? 'api.exe' : 'api';
    const resourcePath = path.join(process.resourcesPath, 'backend', exName);
    const unpackedPath = path.join(process.resourcesPath, 'app.asar.unpacked', 'backend', exName);
    const backendPath = fs.existsSync(resourcePath) ? resourcePath : unpackedPath;
    if (!fs.existsSync(backendPath)) {
      setBackendError(`Backend binary not found. Checked: ${resourcePath}, ${unpackedPath}`);
      return;
    }
    backendStatus.executablePath = backendPath;
    log.info(`Starting packaged backend at: ${backendPath}`);
    backendProcess = spawn(backendPath, [], { stdio: ['ignore', 'pipe', 'pipe'], env });
  } else {
    const pythonPath = path.join(__dirname, '..', '.venv', 'bin', 'python');
    const scriptPath = path.join(__dirname, '..', 'src', 'api.py');
    backendStatus.executablePath = `${pythonPath} ${scriptPath}`;
    log.info(`Starting local backend with: ${pythonPath} ${scriptPath}`);
    backendProcess = spawn(pythonPath, [scriptPath], { stdio: ['ignore', 'pipe', 'pipe'], env });
  }

  if (!backendProcess) {
    setBackendError('Backend process did not start.');
    return;
  }

  backendStatus.state = 'running';
  backendStatus.lastError = '';
  backendStatus.lastExitCode = null;
  backendStatus.lastExitSignal = null;
  backendStatus.pid = backendProcess.pid || null;
  backendStatus.startedAt = Date.now();


  backendProcess.on('error', (err) => {
    setBackendError(`Failed to start backend process: ${String(err)}`);
    backendProcess = null;
  });

  backendProcess.on('exit', (code, signal) => {
    if (isAppQuitting) {
      backendStatus.state = 'stopped';
      backendStatus.pid = null;
      backendProcess = null;
      return;
    }
    if (isBackendRestarting) {
      backendStatus.state = 'restarting';
      backendStatus.pid = null;
      log.info(`Backend process exited during restart. code=${code}, signal=${signal}`);
      backendProcess = null;
      return;
    }
    backendStatus.state = 'exited';
    backendStatus.lastExitCode = code;
    backendStatus.lastExitSignal = signal;
    backendStatus.pid = null;
    const isBadCpuType = process.platform === 'darwin' && Number(code) === 86;
    const exitHint = isBadCpuType
      ? ' This usually means architecture mismatch (Apple Silicon app on Intel Mac or vice versa).'
      : '';
    setBackendError(`Backend process exited unexpectedly. code=${code}, signal=${signal}.${exitHint}`);
    backendProcess = null;
  });

  if (backendProcess.stdout) {
    backendProcess.stdout.on('data', (chunk) => {
      log.info(`[backend] ${String(chunk).trim()}`);
    });
  }
  if (backendProcess.stderr) {
    backendProcess.stderr.on('data', (chunk) => {
      const line = String(chunk).trim();
      if (line) {
        backendStatus.lastError = line;
      }
      log.error(`[backend] ${line}`);
      if (/address already in use|errno 48|errno 98/i.test(line)) {
        scheduleAutoRecovery('port conflict detected');
      }
    });
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 180,
    minHeight: 120,
    minWidth: 600,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    hasShadow: true,
    center: true,
    movable: true,
    resizable: true,
    vibrancy: 'under-window',
    visualEffectState: 'active',
    show: true, // Start visible on first launch
    skipTaskbar: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile('index.html');
  
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
    console.log('Window preloaded and ready.');
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  await startBackend();
  createWindow();

  // Register command to toggle window
  const ret = globalShortcut.register('CommandOrControl+Shift+Space', () => {
    if (!mainWindow) {
      createWindow();
      // On creation, show immediately when ready
      mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        mainWindow.focus();
      });
      return;
    }

    if (mainWindow.isVisible()) {
      mainWindow.hide();
    } else {
      mainWindow.show();
      mainWindow.focus();
    }
  });

  if (!ret) {
    console.log('registration failed');
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  isAppQuitting = true;
  globalShortcut.unregisterAll();
  if (backendProcess) {
    log.info('Killing backend process...');
    backendProcess.kill();
  }
  backendStatus.state = 'stopped';
});

ipcMain.on('resize-window', (event, width, height) => {
  mainWindow.setSize(width, height);
});

ipcMain.on('hide-window', () => {
  mainWindow.hide();
});

// Use macOS native shell to launch files
ipcMain.on('open-file', (event, filePath) => {
  shell.openPath(filePath).then((error) => {
    if (error) {
      console.error(`Error opening file: ${error}`);
      return;
    }
    mainWindow.hide();
  });
});

// Reveal in Finder
ipcMain.on('reveal-file', (event, filePath) => {
  shell.showItemInFolder(filePath);
});

ipcMain.on('open-docs', () => {
  const localDocs = path.join(__dirname, '..', 'docs');
  if (fs.existsSync(localDocs)) {
    shell.openPath(localDocs);
  } else {
    shell.openExternal('https://github.com/deepanmpc/SMART-SEARCH/tree/main/docs');
  }
});

ipcMain.handle('get-config', () => {
  return loadConfig();
});

ipcMain.handle('save-config', (event, config) => {
  const current = loadConfig();
  const updated = { ...current, ...config };
  saveConfig(updated);
  
  // If API key changed, restart backend to apply it
  if (config.google_api_key && config.google_api_key !== current.google_api_key) {
    log.info('API Key changed, restarting backend...');
    if (backendProcess) {
       isBackendRestarting = true;
       backendProcess.kill();
       // Small delay to ensure port is freed
       setTimeout(() => {
         startBackend()
           .then(() => { isBackendRestarting = false; })
           .catch((err) => {
             isBackendRestarting = false;
             log.error('Backend restart failed:', err);
           });
       }, 1000);
    } else {
       startBackend().catch((err) => log.error('Backend start failed:', err));
    }
  }
  return { success: true };
});

ipcMain.handle('get-api-base-url', () => {
  const resolvedPort = backendPort || Number(process.env.SMART_SEARCH_API_PORT || 8000);
  return `http://127.0.0.1:${resolvedPort}`;
});

ipcMain.handle('get-backend-status', () => {
  const resolvedPort = backendPort || Number(process.env.SMART_SEARCH_API_PORT || 8000);
  return { ...backendStatus, port: resolvedPort };
});

ipcMain.handle('select-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'openFile', 'multiSelections']
  });
  if (result.canceled) {
    return null;
  } else {
    return result.filePaths;
  }
});
