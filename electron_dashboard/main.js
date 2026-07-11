const { app, BrowserWindow, ipcMain, nativeTheme } = require('electron');
const path = require('path');

function createWindow() {
    const mainWindow = new BrowserWindow({
        width: 1200,
        height: 700,
        minWidth: 900,
        minHeight: 600,
        frame: false,
        titleBarStyle: 'hidden',
        transparent: true,
        backgroundColor: '#00000000',
        resizable: true,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    mainWindow.loadFile('index.html');
    

    // Ensure it properly regains focus when restored (e.g., via Alt-Tab)
    mainWindow.on('restore', () => {
        setTimeout(() => {
            mainWindow.setAlwaysOnTop(true);
            mainWindow.show();
            mainWindow.focus();
            mainWindow.setAlwaysOnTop(false);
        }, 50);
    });
    
    ipcMain.on('close-window', () => {
        app.quit();
    });

    ipcMain.on('minimize-window', () => {
        mainWindow.minimize();
    });

    ipcMain.handle('dialog:openFile', async () => {
        const { dialog } = require('electron');
        const result = await dialog.showOpenDialog(mainWindow, {
            properties: ['openFile'],
            filters: [
                { name: 'Images', extensions: ['png', 'svg', 'jpg', 'jpeg'] }
            ]
        });
        if (!result.canceled && result.filePaths.length > 0) {
            return result.filePaths[0];
        }
        return null;
    });

    ipcMain.handle('dialog:openApp', async () => {
        const { dialog } = require('electron');
        const result = await dialog.showOpenDialog(mainWindow, {
            title: 'Select Application or Shortcut',
            properties: ['openFile'],
            filters: [
                { name: 'Applications & Shortcuts (*.exe, *.lnk, *.bat, *.cmd)', extensions: ['exe', 'lnk', 'bat', 'cmd'] },
                { name: 'All Files (*.*)', extensions: ['*'] }
            ]
        });
        if (!result.canceled && result.filePaths.length > 0) {
            return result.filePaths[0];
        }
        return null;
    });

    ipcMain.handle('app:getFileIcon', async (event, filePath) => {
        try {
            let iconTarget = filePath;

            // For .lnk files, resolve the shortcut to its target exe first.
            // This mirrors Python's IconExtractor which uses win32com to resolve
            // shortcut.TargetPath and shortcut.IconLocation before extraction.
            // Without this, Electron's app.getFileIcon returns a generic 32x32
            // document icon instead of the actual application icon.
            if (filePath.toLowerCase().endsWith('.lnk')) {
                try {
                    const { shell } = require('electron');
                    const linkData = shell.readShortcutLink(filePath);
                    if (linkData && linkData.target) {
                        iconTarget = linkData.target;
                    }
                } catch (resolveErr) {
                    console.warn('Failed to resolve .lnk target, using original path:', resolveErr.message);
                }
            }

            const icon = await app.getFileIcon(iconTarget, { size: 'large' });
            if (!icon) {
                return "ERROR: app.getFileIcon returned null/falsy";
            }
            return icon.toDataURL();
        } catch (err) {
            console.error("Error getting file icon:", err);
            return "ERROR: " + err.message + "\nStack: " + err.stack;
        }
    });


}

app.whenReady().then(() => {
    nativeTheme.themeSource = 'dark';
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});
