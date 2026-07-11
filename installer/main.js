const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

process.on('uncaughtException', (err) => {
  fs.writeFileSync(path.join(process.env.USERPROFILE, 'Desktop', 'installer_crash.txt'), err.stack || err.message);
  app.quit();
});

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 600,
    height: 480,
    frame: false,
    transparent: true,
    resizable: false,
    icon: path.join(__dirname, '../icon.ico'),
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile('index.html');
}

app.whenReady().then(createWindow);

ipcMain.on('close-installer', (event, options) => {
  if (options && options.launchNow) {
    const exePath = path.join(process.env.LOCALAPPDATA, 'Programs', 'Pandora', 'Pandora.exe');
    shell.openPath(exePath).then(() => {
      app.quit();
    });
  } else {
    app.quit();
  }
});

ipcMain.on('start-install', (event, options) => {
  const logFile = path.join(process.env.USERPROFILE, 'Desktop', 'installer_trace.txt');
  fs.writeFileSync(logFile, "Started install flow\n");

  const destDir = path.join(process.env.LOCALAPPDATA, 'Programs', 'Pandora');
  
  let payloadPath = path.join(process.resourcesPath, '..', 'payload.zip');
  if (!fs.existsSync(payloadPath)) {
      payloadPath = path.join(__dirname, 'payload.zip'); // Fallback for dev mode
  }
  fs.appendFileSync(logFile, "Payload path: " + payloadPath + "\n");

  // 1. Create destination if it doesn't exist
  if (!fs.existsSync(destDir)) {
      fs.mkdirSync(destDir, { recursive: true });
  }
  fs.appendFileSync(logFile, "Dest dir created\n");

  // 2. Kill any running instance then extract payload
  fs.appendFileSync(logFile, "Executing taskkill\n");
  exec(`taskkill /F /IM Pandora.exe /T`, () => {
    fs.appendFileSync(logFile, "Taskkill finished, executing Expand-Archive\n");
    const extractCmd = `powershell.exe -Command "Expand-Archive -Path '${payloadPath}' -DestinationPath '${destDir}' -Force"`;
    
    exec(extractCmd, (error, stdout, stderr) => {
    fs.appendFileSync(logFile, "Expand-Archive finished. Error: " + (error ? error.message : "none") + "\n");
    if (error) {
      console.error(`Extraction Error: ${error.message}`);
      // Send error back or continue anyway for now
    }

    // 3. Handle shortcuts and registry
    fs.appendFileSync(logFile, "Handling shortcuts\n");
    let scripts = [];
    const exePath = path.join(destDir, 'Pandora.exe');
    const iconPath = path.join(destDir, 'icon.ico');
    const uninstallBatPath = path.join(destDir, 'uninstall.bat');

    // Create uninstall.bat
    const uninstallScript = `
@echo off
:: If we are not running from TEMP, copy ourselves there and relaunch
if not "%~dp0"=="%TEMP%\\" (
    copy /y "%~f0" "%TEMP%\\Pandora_uninstall.bat" >nul
    start "" /b "%TEMP%\\Pandora_uninstall.bat"
    exit /b
)

echo Uninstalling Pandora...
taskkill /F /IM Pandora.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" /v Pandora /f >nul 2>&1
reg delete "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Pandora" /f >nul 2>&1

if exist "%APPDATA%\\Pandora\\internal_storage" (
    echo Backing up Pandora storage to Desktop...
    mkdir "%USERPROFILE%\\Desktop\\Pandora_Backup" >nul 2>&1
    xcopy "%APPDATA%\\Pandora\\internal_storage\\*" "%USERPROFILE%\\Desktop\\Pandora_Backup\\" /E /I /H /Y >nul 2>&1
)

del "%USERPROFILE%\\Desktop\\Pandora.lnk" >nul 2>&1
del "%USERPROFILE%\\OneDrive\\Desktop\\Pandora.lnk" >nul 2>&1
del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Pandora.lnk" >nul 2>&1

:: We are running from TEMP now, so we can safely delete the installation folder
rmdir /s /q "%LOCALAPPDATA%\\Programs\\Pandora" >nul 2>&1
rmdir /s /q "%APPDATA%\\Pandora" >nul 2>&1

:: Self delete this script from TEMP
del "%~f0"
    `;
    fs.writeFileSync(uninstallBatPath, uninstallScript.trim());

    if (options.desktop) {
        scripts.push(`
            $DesktopPath = [Environment]::GetFolderPath("Desktop")
            $WshShell = New-Object -comObject WScript.Shell
            $Shortcut = $WshShell.CreateShortcut("$DesktopPath\\Pandora.lnk")
            $Shortcut.TargetPath = "${exePath}"
            $Shortcut.IconLocation = "${iconPath}"
            $Shortcut.WorkingDirectory = "${destDir}"
            $Shortcut.Save()
            
            $StartMenuPath = [Environment]::GetFolderPath("Programs")
            $StartMenuShortcut = $WshShell.CreateShortcut("$StartMenuPath\\Pandora.lnk")
            $StartMenuShortcut.TargetPath = "${exePath}"
            $StartMenuShortcut.IconLocation = "${iconPath}"
            $StartMenuShortcut.WorkingDirectory = "${destDir}"
            $StartMenuShortcut.Save()
        `);
    }

    if (options.startup) {
        scripts.push(
            '$RegistryPath = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"\n' +
            'Set-ItemProperty -Path $RegistryPath -Name "Pandora" -Value "`"' + exePath + '`""'
        );
    }
    
    const today = new Date();
    const yyyymmdd = today.getFullYear() + String(today.getMonth() + 1).padStart(2, '0') + String(today.getDate()).padStart(2, '0');

    // Register Uninstaller
    scripts.push(
        '$UninstallKey = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Pandora"\n' +
        'New-Item -Path $UninstallKey -Force | Out-Null\n' +
        'Set-ItemProperty -Path $UninstallKey -Name "DisplayName" -Value "Pandora"\n' +
        'Set-ItemProperty -Path $UninstallKey -Name "DisplayIcon" -Value "`"' + iconPath + '`""\n' +
        'Set-ItemProperty -Path $UninstallKey -Name "UninstallString" -Value "`"' + uninstallBatPath + '`""\n' +
        'Set-ItemProperty -Path $UninstallKey -Name "Publisher" -Value "Pandora"\n' +
        'Set-ItemProperty -Path $UninstallKey -Name "DisplayVersion" -Value "1.0.0"\n' +
        'Set-ItemProperty -Path $UninstallKey -Name "EstimatedSize" -Value 1000000 -Type DWord\n' +
        'Set-ItemProperty -Path $UninstallKey -Name "InstallDate" -Value "' + yyyymmdd + '"\n'
    );

    if (scripts.length > 0) {
        const psScript = scripts.join('\n');
        const encoded = Buffer.from(psScript, 'utf16le').toString('base64');
        exec(`powershell.exe -EncodedCommand ${encoded}`, () => {
            event.reply('install-complete');
        });
    } else {
        event.reply('install-complete');
    }
  });
  });
});
