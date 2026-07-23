
#include <windows.h>
#include <dxgi1_6.h>
#include <stdio.h>

#pragma comment(lib, "dxgi.lib")

int main() {
    IDXGIFactory1* pFactory;
    if (FAILED(CreateDXGIFactory1(__uuidof(IDXGIFactory1), (void**)&pFactory))) return 1;
    
    IDXGIAdapter1* pAdapter;
    for (UINT i = 0; pFactory->EnumAdapters1(i, &pAdapter) != DXGI_ERROR_NOT_FOUND; ++i) {
        DXGI_ADAPTER_DESC1 desc;
        pAdapter->GetDesc1(&desc);
        wprintf(L"Adapter %d: %s\n", i, desc.Description);
        wprintf(L"  DedicatedVideoMemory: %llu MB\n", desc.DedicatedVideoMemory / (1024 * 1024));
        wprintf(L"  SharedSystemMemory: %llu MB\n", desc.SharedSystemMemory / (1024 * 1024));
        pAdapter->Release();
    }
    pFactory->Release();
    return 0;
}
