# Requires -RunAsAdministrator

Write-Host "Pandora Desktop Integration Build Pipeline" -ForegroundColor Cyan

# 1. Check for Admin rights
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script MUST be run as Administrator to install the certificate and copy to Program Files." -ForegroundColor Red
    Write-Host "Please close this window, open PowerShell as Administrator, and run this script again." -ForegroundColor Red
    Exit
}

$WorkspaceDir = $PSScriptRoot
$VenvPython = Join-Path $WorkspaceDir "venv\Scripts\python.exe"
$VenvPip = Join-Path $WorkspaceDir "venv\Scripts\pip.exe"

# Gracefully attempt to kill any running instances so files aren't locked
Write-Host "`n[0/7] Terminating existing Pandora processes..."
Stop-Process -Name "Pandora", "PandoraUI", "PandoraCore" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Start-Sleep -Seconds 2

# 2. Install PyInstaller and dependencies
Write-Host "`n[1/7] Installing PyInstaller and dependencies..."
& $VenvPython -m pip install pyinstaller send2trash

# 2.5 Build Native Audio Engine
Write-Host "`n[2/7] Compiling Native Audio Engine (C++)..."
$NativeExe = "$WorkspaceDir\native_engine\build\Release\AudioCaptureService.exe"
if (Test-Path $NativeExe) {
    Write-Host "Native Audio Engine already exists. Skipping CMake build." -ForegroundColor Green
} else {
    Push-Location "$WorkspaceDir\native_engine"
    if (-not (Test-Path "build")) {
        New-Item -ItemType Directory -Path "build" | Out-Null
    }
    cd build
    
    # Check if cmake exists
    if (Get-Command cmake -ErrorAction SilentlyContinue) {
        cmake ..
        cmake --build . --config Release
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to compile Native Audio Engine." -ForegroundColor Red
            Exit
        }
    } else {
        Write-Host "ERROR: cmake is not installed. Please install CMake to build the Native Audio Engine." -ForegroundColor Red
        Exit
    }
    Pop-Location
}

# 3. Create Custom Manifest
Write-Host "`n[2/6] Generating Custom Application Manifest (UIAccess=true)..."
$ManifestPath = Join-Path $WorkspaceDir "Pandora.exe.manifest"
$ManifestContent = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity version="1.0.0.0" processorArchitecture="amd64" name="Pandora" type="win32"/>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="true"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity type="win32" name="Microsoft.Windows.Common-Controls" version="6.0.0.0" processorArchitecture="*" publicKeyToken="6595b64144ccf1df" language="*"/>
    </dependentAssembly>
  </dependency>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}"/>
    </application>
  </compatibility>
</assembly>
"@
Set-Content -Path $ManifestPath -Value $ManifestContent

# 3.5 Build Electron Dashboard
Write-Host "`n[3/7] Compiling Electron Dashboard to Executable..."
if (Test-Path "$WorkspaceDir\dist_electron") {
    Remove-Item -Path "$WorkspaceDir\dist_electron" -Recurse -Force
}
Push-Location "$WorkspaceDir\electron_dashboard"
# Copy assets so they are packaged into the Electron app
Copy-Item -Path "..\assets" -Destination "assets" -Recurse -Force
npx electron-packager . "PandoraUI" --platform=win32 --arch=x64 --icon="..\icon.ico" --out="..\dist_electron" --asar --overwrite
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: electron-packager failed." -ForegroundColor Red
    Exit
}
# Clean up copied assets
Remove-Item -Path "assets" -Recurse -Force
Pop-Location

# 4. Build with PyInstaller
Write-Host "`n[4/7] Compiling Python to Executable (PandoraCore)..."
& $VenvPython -m PyInstaller --clean --noconfirm PandoraCore.spec

$CoreExe = Join-Path $WorkspaceDir "dist\PandoraCore\PandoraCore.exe"
if (-not (Test-Path $CoreExe)) {
    Write-Host "ERROR: PyInstaller failed to build the core executable." -ForegroundColor Red
    Exit
}

# Rename dist\PandoraCore to dist\Pandora
Write-Host "Renaming distribution directory to Pandora..."
if (Test-Path "$WorkspaceDir\dist\Pandora") {
    Remove-Item -Path "$WorkspaceDir\dist\Pandora" -Recurse -Force
}
Rename-Item -Path "$WorkspaceDir\dist\PandoraCore" -NewName "Pandora"

# Build Uninstaller
Write-Host "`n[4.5/7] Compiling Python to Executable (PandoraUninstaller)..."
& $VenvPython -m PyInstaller --clean --noconfirm PandoraUninstaller.spec

$UninstallerExe = Join-Path $WorkspaceDir "dist\PandoraUninstaller\PandoraUninstaller.exe"
if (-not (Test-Path $UninstallerExe)) {
    Write-Host "ERROR: PyInstaller failed to build the uninstaller executable." -ForegroundColor Red
    Exit
}

Write-Host "Moving PandoraUninstaller to dist\Pandora\Uninstaller..."
$uninstallerDest = Join-Path "$WorkspaceDir\dist\Pandora" "Uninstaller"
New-Item -ItemType Directory -Path $uninstallerDest -Force | Out-Null
Copy-Item -Path "$WorkspaceDir\dist\PandoraUninstaller\*" -Destination $uninstallerDest -Recurse -Force


# Compile Dedicated GPU Force Launcher (Pandora.exe) with Icon
Write-Host "Compiling Dedicated GPU Force Launcher (Pandora.exe)..."
$RcPath = Join-Path $WorkspaceDir "launcher.rc"
Set-Content -Path $RcPath -Value "1 ICON `"icon.ico`""
& windres $RcPath -O coff -o "$WorkspaceDir\launcher_res.o"
& g++ -mwindows -static -o "$WorkspaceDir\dist\Pandora\Pandora.exe" "$WorkspaceDir\launcher.cpp" "$WorkspaceDir\launcher_res.o" -lshell32
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to compile Dedicated GPU Force Launcher." -ForegroundColor Red
    Exit
}

$CompiledExe = Join-Path $WorkspaceDir "dist\Pandora\Pandora.exe"
if (-not (Test-Path $CompiledExe)) {
    Write-Host "ERROR: Compiled launcher was not found at $CompiledExe." -ForegroundColor Red
    Exit
}

# Post-build cleanup
Write-Host "Post-build cleanup: Removing unused large DLLs..."
$removeList = @(
    "opengl32sw.dll", "dxcompiler.dll", "dxil.dll", "vk_swiftshader.dll", 
    "mfc140u.dll", "Qt6Pdf.dll", "D3DCOMPILER_47.dll"
)
foreach ($dll in $removeList) {
    $path = Join-Path "$WorkspaceDir\dist\Pandora\_internal" $dll
    if (Test-Path $path) { Remove-Item $path -Force }
}


# 5. Generate and Install Self-Signed Certificate
Write-Host "`n[4/6] Creating Self-Signed Code Signing Certificate..."
$CertName = "PandoraLocalDev"
$Cert = Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object { $_.Subject -match $CertName }

if (-not $Cert) {
    Write-Host "Generating new certificate..."
    $Cert = New-SelfSignedCertificate -Subject "CN=$CertName" -Type CodeSigningCert -CertStoreLocation Cert:\LocalMachine\My
}

Write-Host "Installing certificate to Trusted Root and Trusted Publisher..."
$storeRoot = New-Object System.Security.Cryptography.X509Certificates.X509Store "Root", "LocalMachine"
$storeRoot.Open("ReadWrite")
$storeRoot.Add($Cert)
$storeRoot.Close()

$storePublisher = New-Object System.Security.Cryptography.X509Certificates.X509Store "TrustedPublisher", "LocalMachine"
$storePublisher.Open("ReadWrite")
$storePublisher.Add($Cert)
$storePublisher.Close()

# 6. Sign the Executable
Write-Host "`n[5/6] Cryptographically signing Pandora.exe..."
$sig = Set-AuthenticodeSignature -FilePath $CompiledExe -Certificate $Cert
if ($sig.Status -ne 'Valid') {
    Write-Host "ERROR: Failed to sign executable. Status: $($sig.Status)" -ForegroundColor Red
    Exit
}
Write-Host "Successfully signed."

# 7. Zip the payload
Write-Host "`n[6/8] Zipping the payload..."

Write-Host "Pruning deeply nested compilation artifacts to avoid Windows MAX_PATH errors..."
# Find and remove deep 'obj' and '.tlog' folders inside node_modules that cause >260 char paths
Get-ChildItem -Path "$WorkspaceDir\dist\Pandora\_internal" -Recurse -Filter "obj" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match "node_modules" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path "$WorkspaceDir\dist\Pandora\_internal" -Recurse -Filter "*.tlog" -Directory -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match "node_modules" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

if (Test-Path "$WorkspaceDir\dist\payload.zip") { Remove-Item "$WorkspaceDir\dist\payload.zip" -Force }

Write-Host "Generating manifest.json and version.txt for differential updates..."
$manifestScript = @"
import os
import hashlib
import json
import re

dist_dir = r'$($WorkspaceDir.Replace('\', '\\'))\\dist\\Pandora'
manifest = {}

# Extract version from config.py
version = "0.0.0"
config_path = r'$($WorkspaceDir.Replace('\', '\\'))\\config.py'
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
        match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            version = match.group(1)

with open(os.path.join(dist_dir, 'version.txt'), 'w', encoding='utf-8') as f:
    f.write(version)

for root, _, files in os.walk(dist_dir):
    for file in files:
        if file in ('manifest.json', 'version.txt'):
            continue
        filepath = os.path.join(root, file)
        relpath = os.path.relpath(filepath, dist_dir).replace('\\\\', '/')
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        manifest[relpath] = hasher.hexdigest()

with open(os.path.join(dist_dir, 'manifest.json'), 'w') as f:
    json.dump(manifest, f, indent=2)
"@
Set-Content -Path "$WorkspaceDir\dist\gen_manifest.py" -Value $manifestScript
& $VenvPython "$WorkspaceDir\dist\gen_manifest.py"

Compress-Archive -Path "$WorkspaceDir\dist\Pandora\*" -DestinationPath "$WorkspaceDir\dist\payload.zip"

# 8. Build Custom Python Installer
Write-Host "`n[7/8] Compiling Custom Python Installer with bundled payload..."
& $VenvPython -m PyInstaller --clean --noconfirm --onefile --windowed --name "PandoraInstaller" --icon "icon.ico" --add-data "assets;assets" --add-data "dist\payload.zip;." installer.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyInstaller failed to build the installer." -ForegroundColor Red
    Exit
}
$finalInstaller = "$WorkspaceDir\dist\PandoraInstaller.exe"

# 9. Sign the Installer
Write-Host "`n[8/8] Signing the Setup Executable..."
$SetupExe = $finalInstaller
if (Test-Path $SetupExe) {
    # Windows Defender often temporarily locks newly compiled executables. Add a retry loop.
    $maxRetries = 5
    $retryCount = 0
    $signed = $false
    
    while (-not $signed -and $retryCount -lt $maxRetries) {
        try {
            $sig2 = Set-AuthenticodeSignature -FilePath $SetupExe -Certificate $Cert -ErrorAction Stop
            if ($sig2.Status -eq 'Valid') {
                $signed = $true
            } else {
                throw "Status: $($sig2.Status)"
            }
        } catch {
            $retryCount++
            Write-Host "File locked or signing failed. Retrying in 2 seconds... ($retryCount/$maxRetries)" -ForegroundColor Yellow
            Start-Sleep -Seconds 2
        }
    }
    
    if (-not $signed) {
        Write-Host "Warning: Failed to sign setup executable after $maxRetries retries." -ForegroundColor Red
    }
    
    Write-Host "`n=== DEPLOYMENT COMPLETE ===" -ForegroundColor Green
    Write-Host "1. Installer Payload Zipped Successfully." -ForegroundColor Cyan
    Write-Host "2. Custom Python Installer generated at: '$SetupExe'" -ForegroundColor Cyan
} else {
    Write-Host "ERROR: Compiled setup was not found at $SetupExe." -ForegroundColor Red
}
