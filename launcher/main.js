const { app, BrowserWindow, globalShortcut, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const fs = require('fs');
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

function startBackend() {
  const isPackaged = app.isPackaged;
  const config = loadConfig();
  const env = { ...process.env };
  
  if (config.google_api_key) {
    env.GOOGLE_API_KEY = config.google_api_key;
    log.info('Using Gemini API Key from config.');
  }

  if (isPackaged) {
    const exName = process.platform === 'win32' ? 'api.exe' : 'api';
    const backendPath = path.join(process.resourcesPath, 'backend', exName);
    log.info(`Starting packaged backend at: ${backendPath}`);
    backendProcess = spawn(backendPath, [], { stdio: 'inherit', env });
  } else {
    const pythonPath = path.join(__dirname, '..', '.venv', 'bin', 'python');
    const scriptPath = path.join(__dirname, '..', 'src', 'api.py');
    log.info(`Starting local backend with: ${pythonPath} ${scriptPath}`);
    backendProcess = spawn(pythonPath, [scriptPath], { stdio: 'inherit', env });
  }


  backendProcess.on('error', (err) => {
    log.error('Failed to start backend process:', err);
  });
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
    show: false, // Start hidden
    skipTaskbar: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile('index.html');
  
  mainWindow.once('ready-to-show', () => {
    // Keep it hidden initially, wait for shortcut
    console.log('Window preloaded and ready.');
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  startBackend();
  createWindow();

  // Register command to toggle window
  const ret = globalShortcut.register('CommandOrControl+Shift+Space', () => {
    if (!mainWindow) {
      createWindow();
      setTimeout(() => {
        mainWindow.show();
        mainWindow.focus();
      }, 200);
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
  globalShortcut.unregisterAll();
  if (backendProcess) {
    log.info('Killing backend process...');
    backendProcess.kill();
  }
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
  shell.openPath(path.join(__dirname, '..', 'docs'));
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
       backendProcess.kill();
       // Small delay to ensure port is freed
       setTimeout(startBackend, 1000);
    } else {
       startBackend();
    }
  }
  return { success: true };
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

