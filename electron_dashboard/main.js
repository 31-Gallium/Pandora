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
    
    if (process.argv.includes('--uninstall')) {
        createUninstallWindow();
    } else {
        createWindow();
    }

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

ipcMain.on('close-window', () => {
    app.quit();
});

ipcMain.on('minimize-window', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) win.minimize();
});



function createUninstallWindow() {
    const uninstallWindow = new BrowserWindow({
        width: 600,
        height: 500,
        frame: false,
        titleBarStyle: 'hidden',
        transparent: true,
        backgroundColor: '#00000000',
        resizable: false,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    uninstallWindow.loadFile('uninstaller.html');

    ipcMain.once('execute-uninstall', (event, options) => {
        const fs = require('fs');
        const os = require('os');
        const { exec } = require('child_process');

        const tempBat = path.join(os.tmpdir(), 'pandora_execute_uninstall.bat');
        const appData = path.join(process.env.APPDATA, 'Pandora');
        const localAppData = path.join(process.env.LOCALAPPDATA, 'Programs', 'Pandora');
        const internalStorage = path.join(appData, 'internal_storage');
        const desktop = path.join(process.env.USERPROFILE, 'Desktop', 'Pandora_Backup');

        let batContent = `@echo off\n`;
        batContent += `cd /d "%USERPROFILE%"\n`;
        batContent += `echo Uninstalling Pandora...\n`;
        batContent += `timeout /t 3 /nobreak >nul\n`; // Wait for app to close
        batContent += `taskkill /F /IM Pandora.exe /T >nul 2>&1\n`;
        batContent += `taskkill /F /IM PandoraUI.exe /T >nul 2>&1\n`;

        if (options.backupStorage === 'desktop') {
            batContent += `if exist "${internalStorage}" (xcopy "${internalStorage}\\*" "${desktop}\\" /E /I /Y >nul)\n`;
        }

        if (options.deleteAppData) {
            batContent += `rmdir /S /Q "${appData}" >nul 2>&1\n`;
        } else {
            batContent += `rmdir /S /Q "${internalStorage}" >nul 2>&1\n`;
        }

        batContent += `rmdir /S /Q "${localAppData}" >nul 2>&1\n`;
        batContent += `del "%USERPROFILE%\\Desktop\\Pandora.lnk" >nul 2>&1\n`;
        batContent += `del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Pandora.lnk" >nul 2>&1\n`;
        batContent += `reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Pandora" /f >nul 2>&1\n`;
        batContent += `(goto) 2>nul & del "%~f0"\n`;

        fs.writeFileSync(tempBat, batContent);
        
        exec(`start "" /b "${tempBat}"`);
        app.quit();
    });
}
