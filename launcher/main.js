const { app, BrowserWindow, globalShortcut, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { exec } = require('child_process');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 900,
    height: 140,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    hasShadow: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile('index.html');
  // mainWindow.hide();

  // mainWindow.webContents.openDevTools({ mode: 'detach' });
}

app.whenReady().then(() => {
  createWindow();

  // Register command to toggle window
  const ret = globalShortcut.register('CommandOrControl+Shift+Space', () => {
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

