const { app, BrowserWindow, globalShortcut, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { exec } = require('child_process');

let mainWindow;

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

