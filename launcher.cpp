#include <windows.h>
#include <string>
#include <shellapi.h>
#include <vector>

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
    
    // Look for app-* directories (Discord-style versioning)
    WIN32_FIND_DATAW findData;
    std::wstring searchPath = dir + L"\\app-*";
    HANDLE hFind = FindFirstFileW(searchPath.c_str(), &findData);
    
    std::wstring highestVersion = L"";
    std::wstring targetAppDir = L"";
    
    // Helper lambda: parse "app-X.Y.Z" into a vector of ints for proper semver comparison
    auto parseSemVer = [](const std::wstring& name) -> std::vector<int> {
        std::vector<int> parts;
        // Strip "app-" prefix
        size_t start = name.find(L'-');
        if (start == std::wstring::npos) return parts;
        std::wstring ver = name.substr(start + 1);
        // Split on '.' and parse each segment as int
        size_t pos = 0;
        while (pos < ver.size()) {
            size_t dot = ver.find(L'.', pos);
            if (dot == std::wstring::npos) dot = ver.size();
            try { parts.push_back(std::stoi(ver.substr(pos, dot - pos))); }
            catch (...) { parts.push_back(0); }
            pos = dot + 1;
        }
        return parts;
    };
    
    if (hFind != INVALID_HANDLE_VALUE) {
        std::vector<int> highestParts;
        do {
            if (findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                std::wstring folderName = findData.cFileName;
                // Only consider the folder if PandoraCore.exe actually exists inside it (not a partial extraction)
                std::wstring testCore = dir + L"\\" + folderName + L"\\PandoraCore.exe";
                DWORD attr = GetFileAttributesW(testCore.c_str());
                if (attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY)) {
                    std::vector<int> thisParts = parseSemVer(folderName);
                    if (thisParts > highestParts) {
                        highestParts = thisParts;
                        highestVersion = folderName;
                    }
                }
            }
        } while (FindNextFileW(hFind, &findData));
        FindClose(hFind);
    }
    
    std::wstring corePath;
    std::wstring workingDir;
    
    if (!highestVersion.empty()) {
        // We are at the root, launch the highest version payload
        targetAppDir = dir + L"\\" + highestVersion;
        corePath = targetAppDir + L"\\PandoraCore.exe";
        workingDir = targetAppDir;
    } else {
        // We are inside the payload, launch the local core
        corePath = dir + L"\\PandoraCore.exe";
        workingDir = dir;
    }
    
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
        workingDir.c_str(),
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
