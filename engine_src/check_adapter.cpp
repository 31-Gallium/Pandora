#include <windows.h>
#include <d3d11.h>
#include <dxgi1_6.h>
#include <iostream>
#pragma comment(lib, "dxgi.lib")

int main() {
    IDXGIFactory1* dxgiFactory1 = nullptr;
    CreateDXGIFactory1(__uuidof(IDXGIFactory1), (void**)&dxgiFactory1);
    if (!dxgiFactory1) return 1;
    
    IDXGIFactory6* dxgiFactory6 = nullptr;
    if (SUCCEEDED(dxgiFactory1->QueryInterface(__uuidof(IDXGIFactory6), (void**)&dxgiFactory6))) {
        IDXGIAdapter1* adapter;
        for (UINT i = 0; dxgiFactory6->EnumAdapterByGpuPreference(i, DXGI_GPU_PREFERENCE_HIGH_PERFORMANCE, __uuidof(IDXGIAdapter1), (void**)&adapter) != DXGI_ERROR_NOT_FOUND; ++i) {
            DXGI_ADAPTER_DESC1 desc;
            adapter->GetDesc1(&desc);
            std::wcout << L"High Perf GPU " << i << L": " << desc.Description << L" (VRAM: " << (desc.DedicatedVideoMemory/1048576) << L" MB)" << std::endl;
            adapter->Release();
        }
        dxgiFactory6->Release();
    }
    dxgiFactory1->Release();
    return 0;
}
