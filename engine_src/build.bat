@echo off
echo Building Pandora Visualizer Engine...
g++ -shared -static -o pandora_vis_engine.dll visualizer_core.cpp -ld3d11 -ld2d1 -ldwrite -ldxgi -lole32 -luuid -ld3dcompiler
if %ERRORLEVEL% equ 0 (
    echo Build successful.
    copy /Y pandora_vis_engine.dll ..\pandora_vis_engine.dll
) else (
    echo Build failed.
)
