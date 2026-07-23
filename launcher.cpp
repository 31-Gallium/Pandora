#include <windows.h>
#include <string>
#include <shellapi.h>

extern "C" {
    // Forces Nvidia Optimus laptops to use the High Performance NVIDIA GPU
    __declspec(dllexport) DWORD NvOptimusEnablement = 0x00000001;
    
    // Forces AMD Switchable Graphics laptops to use the High Performance AMD GPU
    __declspec(dllexport) int AmdPowerXpressRequestHighPerformance = 1;
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    // Get the path of the current launcher executable
    wchar_t exePath[MAX_PATH];
    if (GetModuleFileNameW(NULL, exePath, MAX_PATH) == 0) {
        return 1;
    }
    
    std::wstring pathStr(exePath);
    size_t lastSlash = pathStr.find_last_of(L"\\/");
    if (lastSlash == std::wstring::npos) {
        return 1;
    }
    std::wstring dir = pathStr.substr(0, lastSlash);
    
    // Path to the core executable
    std::wstring corePath = dir + L"\\PandoraCore.exe";
    
    // Check if PandoraCore.exe exists
    DWORD fileAttr = GetFileAttributesW(corePath.c_str());
    if (fileAttr == INVALID_FILE_ATTRIBUTES || (fileAttr & FILE_ATTRIBUTE_DIRECTORY)) {
        MessageBoxW(NULL, L"Core executable not found (PandoraCore.exe). Please reinstall the application.", L"Pandora Launcher Error", MB_ICONERROR | MB_OK);
        return 1;
    }
    
    // Build command line string: quote the executable path and append arguments
    std::wstring cmdLine = L"\"" + corePath + L"\"";
    
    int argc = 0;
    LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (argv) {
        // Skip argv[0] (which is the launcher exe) and append all other arguments
        for (int i = 1; i < argc; ++i) {
            cmdLine += L" ";
            // Escape/quote argument
            cmdLine += L"\"";
            cmdLine += argv[i];
            cmdLine += L"\"";
        }
        LocalFree(argv);
    }
    
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    ZeroMemory(&pi, sizeof(pi));
    
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = nCmdShow;
    
    // Launch the child process
    BOOL success = CreateProcessW(
        corePath.c_str(),
        const_cast<wchar_t*>(cmdLine.c_str()),
        NULL,
        NULL,
        FALSE,
        0,
        NULL,
        dir.c_str(),
        &si,
        &pi
    );
    
    if (success) {
        // Wait for PandoraCore.exe to finish
        WaitForSingleObject(pi.hProcess, INFINITE);
        DWORD exitCode = 0;
        GetExitCodeProcess(pi.hProcess, &exitCode);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
        return exitCode;
    } else {
        DWORD err = GetLastError();
        wchar_t errMsg[256];
        wsprintfW(errMsg, L"Failed to start PandoraCore.exe. Error code: %lu", err);
        MessageBoxW(NULL, errMsg, L"Pandora Launcher Error", MB_ICONERROR | MB_OK);
    }
    
    return 1;
}
