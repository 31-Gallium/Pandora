# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('native_engine\\build\\Release\\AudioCaptureService.exe', '.'), ('pandora_vis_engine.dll', '.')],
    datas=[('dist_electron\\PandoraUI-win32-x64', 'electron_dashboard\\PandoraUI-win32-x64'), ('assets', 'assets')],
    hiddenimports=['win32pipe', 'win32file', 'pywintypes'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PandoraCore',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
    manifest='C:\\Users\\Base\\Desktop\\Seb\\Pandora\\Pandora.exe.manifest',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PandoraCore',
)
