# Pandora Native Audio Engine

This is a standalone C++20 service that captures per-application audio via WASAPI Process Loopback, computes FFT and beat detection, and streams the structured data back to Pandora via Named Pipes.

## Requirements
- Windows 11 (or Windows 10 Build 20348+)
- Visual Studio 2026 (MSVC 19.51+)
- CMake 3.20+

## Build Instructions

1. Open the **Visual Studio 2026 Developer Command Prompt** (e.g. `vcvars64.bat`).
2. Navigate to this directory.
3. Generate the build files:
   ```cmd
   cmake -B build -G "Visual Studio 18 2026" -A x64
   ```
4. Build the executable:
   ```cmd
   cmake --build build --config Release
   ```
5. The output executable will be located in `build/Release/AudioCaptureService.exe`.

## Third-Party Libraries
All third-party dependencies are header-only and located in the `third_party/` directory:
- **`readerwriterqueue`**: A fast, lock-free Single-Producer Single-Consumer (SPSC) ring buffer used to pass raw PCM data from the real-time WASAPI capture thread to the FFT thread without blocking or memory allocation.
- **`spdlog`**: A highly efficient C++ logging library used for configurable debug output and error tracking.
- **`pocketfft`**: A lightweight, highly optimized FFT implementation chosen over FFTW due to its tiny footprint and lack of complex build dependencies.
