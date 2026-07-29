# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['uninstaller_main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PIL', 'pycaw', 'comtypes', 'psutil', 'asyncio', 'ssl',
        'win32com', 'pythoncom', 'numpy', 'tkinter', '_tkinter', 
        'unittest', 'test', 'pydoc', 'doctest', 'xml.etree', 'xmlrpc', 'sqlite3'
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PandoraUninstaller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PandoraUninstaller',
)
