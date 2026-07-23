#define NOMINMAX
#include <windows.h>
#include <d3d11.h>
#include <d2d1.h>
#include <dwrite.h>
#include <dxgi1_6.h>
#include <vector>
#include <cmath>
#include <stdint.h>
#include <iostream>

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "d2d1.lib")
#pragma comment(lib, "dxgi.lib")
#pragma comment(lib, "d3dcompiler.lib")

#include <d3dcompiler.h>
#include "hlsl_shaders.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Global Context
ID3D11Device* g_d3dDevice = nullptr;
ID3D11DeviceContext* g_d3dContext = nullptr;
ID2D1Factory* g_d2dFactory = nullptr;
ID2D1RenderTarget* g_d2dRenderTarget = nullptr;
ID3D11Texture2D* g_renderTexture = nullptr;
ID3D11Texture2D* g_stagingTextures[3] = {nullptr, nullptr, nullptr};
IDXGISurface* g_dxgiSurface = nullptr;
ID2D1SolidColorBrush* g_brush = nullptr;
uint8_t* g_pixelBuffer = nullptr;
int g_width = 0;
int g_height = 0;
uint64_t g_frameIndex = 0;

// HLSL Objects
ID3D11VertexShader* g_vsFullscreen = nullptr;
ID3D11PixelShader* g_psFerrofluid = nullptr;
ID3D11Buffer* g_cbFerrofluid = nullptr;
ID3D11RenderTargetView* g_renderTargetView = nullptr;
ID3D11SamplerState* g_samplerLinear = nullptr;

struct FerrofluidConstants {
    float bass_e;
    float mids_e;
    float treble_e;
    float time_t;
    int use_texture;
    float dominant_color[3];
    float global_op;
    float padding[3];
};


// Mosaic HLSL Objects
ID3D11VertexShader* g_vsMosaic = nullptr;
ID3D11PixelShader* g_psMosaic = nullptr;
ID3D11Buffer* g_cbMosaic = nullptr;
ID3D11Buffer* g_vbMosaic = nullptr;
ID3D11Buffer* g_ibMosaic = nullptr;
ID3D11InputLayout* g_ilMosaic = nullptr;
int g_mosaicInstanceCount = 0;
int g_mosaicInstanceCapacity = 0;
ID3D11BlendState* g_blendState = nullptr;

struct MosaicConstants {
    float bass_e;
    float mids_e;
    float treble_e;
    float ext_factor;
    float w_x;
    float w_y;
    float d_x;
    float d_y;
    float bass_phase;
    float mids_phase;
    float treble_phase;
    float global_op;
    float ring_thick_0_3[4];
    float ring_thick_4_7[4];
    float grid_dim;
    float g_blockSize;
    float grid_offset;
    float g_mosaicShape;
};

#pragma pack(push, 1)
struct MosaicInstance {
    int gpos[2];
    float dist;
    float pdir[2];
    float pa;
    float color[4];
};
#pragma pack(pop)

struct MosaicVertex {
    float pos[3];
    float norm[3];
};

extern "C" {
    __declspec(dllexport) DWORD NvOptimusEnablement = 1;
    __declspec(dllexport) int AmdPowerXpressRequestHighPerformance = 1;
}

extern "C" {

char g_boundGpuName[256] = "Default Hardware GPU";

__declspec(dllexport) const char* get_bound_gpu_name() {
    return g_boundGpuName;
}

__declspec(dllexport) void destroy_visualizer();

__declspec(dllexport) bool init_visualizer(int width, int height, int gpu_preference) {
    destroy_visualizer(); // Clean up if already initialized
    
    g_width = width;
    g_height = height;

    if (FAILED(D2D1CreateFactory(D2D1_FACTORY_TYPE_SINGLE_THREADED, &g_d2dFactory))) {
        return false;
    }

    IDXGIAdapter1* selectedAdapter = nullptr;
    
    IDXGIFactory1* dxgiFactory1 = nullptr;
    if (SUCCEEDED(CreateDXGIFactory1(__uuidof(IDXGIFactory1), (void**)&dxgiFactory1))) {
        
        // For dynamically loaded DLLs in Python, EnumAdapterByGpuPreference often returns the integrated GPU
        // because the OS hasn't assigned the High Performance profile to python.exe.
        // The most reliable way to find the dedicated GPU is to check DedicatedVideoMemory.
        IDXGIAdapter1* adapter;
        SIZE_T maxVram = 0;
        SIZE_T minVram = (SIZE_T)-1;
        for (UINT i = 0; dxgiFactory1->EnumAdapters1(i, &adapter) != DXGI_ERROR_NOT_FOUND; ++i) {
            DXGI_ADAPTER_DESC1 desc;
            adapter->GetDesc1(&desc);
            if (desc.Flags & DXGI_ADAPTER_FLAG_SOFTWARE) {
                adapter->Release();
                continue;
            }
            
            if (gpu_preference == 2) { // HIGH_PERFORMANCE
                if (desc.DedicatedVideoMemory > maxVram) {
                    maxVram = desc.DedicatedVideoMemory;
                    if (selectedAdapter) selectedAdapter->Release();
                    selectedAdapter = adapter;
                } else {
                    adapter->Release();
                }
            } else if (gpu_preference == 1) { // MINIMUM_POWER
                if (desc.DedicatedVideoMemory < minVram) {
                    minVram = desc.DedicatedVideoMemory;
                    if (selectedAdapter) selectedAdapter->Release();
                    selectedAdapter = adapter;
                } else {
                    adapter->Release();
                }
            } else {
                if (!selectedAdapter) {
                    selectedAdapter = adapter;
                } else {
                    adapter->Release();
                }
            }
        }
        dxgiFactory1->Release();
    }
    if (selectedAdapter) {
        DXGI_ADAPTER_DESC1 desc;
        selectedAdapter->GetDesc1(&desc);
        size_t convertedChars = 0;
        wcstombs_s(&convertedChars, g_boundGpuName, 256, desc.Description, _TRUNCATE);
        printf("[VisEngine] Successfully bound to Dedicated GPU: %s\n", g_boundGpuName);
        fflush(stdout);
    } else {
        strcpy(g_boundGpuName, "Default Hardware GPU");
        printf("[VisEngine] Bound to Default Hardware GPU\n");
        fflush(stdout);
    }

    UINT creationFlags = D3D11_CREATE_DEVICE_BGRA_SUPPORT;
    D3D_FEATURE_LEVEL featureLevels[] = { D3D_FEATURE_LEVEL_11_0, D3D_FEATURE_LEVEL_10_1 };
    
    HRESULT hr = D3D11CreateDevice(
        selectedAdapter,
        selectedAdapter ? D3D_DRIVER_TYPE_UNKNOWN : D3D_DRIVER_TYPE_HARDWARE,
        nullptr,
        creationFlags,
        featureLevels,
        2,
        D3D11_SDK_VERSION,
        &g_d3dDevice,
        nullptr,
        &g_d3dContext
    );

    if (selectedAdapter) selectedAdapter->Release();

    if (FAILED(hr)) return false;

    D3D11_TEXTURE2D_DESC texDesc = {};
    texDesc.Width = width;
    texDesc.Height = height;
    texDesc.MipLevels = 1;
    texDesc.ArraySize = 1;
    texDesc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    texDesc.SampleDesc.Count = 1;
    texDesc.Usage = D3D11_USAGE_DEFAULT;
    texDesc.BindFlags = D3D11_BIND_RENDER_TARGET | D3D11_BIND_SHADER_RESOURCE;
    
    if (FAILED(g_d3dDevice->CreateTexture2D(&texDesc, nullptr, &g_renderTexture))) return false;

    texDesc.Usage = D3D11_USAGE_STAGING;
    texDesc.BindFlags = 0;
    texDesc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;
    for (int i = 0; i < 3; i++) {
        if (FAILED(g_d3dDevice->CreateTexture2D(&texDesc, nullptr, &g_stagingTextures[i]))) return false;
    }
    g_frameIndex = 0;

    if (FAILED(g_renderTexture->QueryInterface(__uuidof(IDXGISurface), (void**)&g_dxgiSurface))) return false;

    D2D1_RENDER_TARGET_PROPERTIES props = D2D1::RenderTargetProperties(
        D2D1_RENDER_TARGET_TYPE_DEFAULT,
        D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM, D2D1_ALPHA_MODE_PREMULTIPLIED)
    );
    
    if (FAILED(g_d2dFactory->CreateDxgiSurfaceRenderTarget(g_dxgiSurface, &props, &g_d2dRenderTarget))) return false;

    g_d2dRenderTarget->CreateSolidColorBrush(D2D1::ColorF(D2D1::ColorF::White), &g_brush);
    
    g_pixelBuffer = new uint8_t[width * height * 4];
    memset(g_pixelBuffer, 0, width * height * 4);
    
    // Create D3D11 Render Target View for the render texture
    if (FAILED(g_d3dDevice->CreateRenderTargetView(g_renderTexture, nullptr, &g_renderTargetView))) return false;

    // Compile HLSL Shaders
    ID3DBlob* blob = nullptr;
    ID3DBlob* errorBlob = nullptr;
    HRESULT hr_shader;
    
    hr_shader = D3DCompile(g_FerrofluidShaderSource, strlen(g_FerrofluidShaderSource), nullptr, nullptr, nullptr, "VS_Fullscreen", "vs_5_0", 0, 0, &blob, &errorBlob);
    if (SUCCEEDED(hr_shader)) {
        g_d3dDevice->CreateVertexShader(blob->GetBufferPointer(), blob->GetBufferSize(), nullptr, &g_vsFullscreen);
        blob->Release();
    } else if (errorBlob) {
        printf("VS Compile Error: %s\n", (char*)errorBlob->GetBufferPointer());
        errorBlob->Release();
    }

    hr_shader = D3DCompile(g_FerrofluidShaderSource, strlen(g_FerrofluidShaderSource), nullptr, nullptr, nullptr, "PS_Ferrofluid", "ps_5_0", 0, 0, &blob, &errorBlob);
    if (SUCCEEDED(hr_shader)) {
        g_d3dDevice->CreatePixelShader(blob->GetBufferPointer(), blob->GetBufferSize(), nullptr, &g_psFerrofluid);
        blob->Release();
    } else if (errorBlob) {
        printf("PS Compile Error: %s\n", (char*)errorBlob->GetBufferPointer());
        errorBlob->Release();
    }

    D3D11_BUFFER_DESC cbDesc = {};
    cbDesc.Usage = D3D11_USAGE_DEFAULT;
    cbDesc.ByteWidth = sizeof(FerrofluidConstants);
    cbDesc.BindFlags = D3D11_BIND_CONSTANT_BUFFER;
    g_d3dDevice->CreateBuffer(&cbDesc, nullptr, &g_cbFerrofluid);
    
    D3D11_SAMPLER_DESC sampDesc = {};
    sampDesc.Filter = D3D11_FILTER_MIN_MAG_MIP_LINEAR;
    sampDesc.AddressU = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampDesc.AddressV = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampDesc.AddressW = D3D11_TEXTURE_ADDRESS_CLAMP;
    sampDesc.ComparisonFunc = D3D11_COMPARISON_NEVER;
    g_d3dDevice->CreateSamplerState(&sampDesc, &g_samplerLinear);

    // Compile Mosaic Shaders
    hr_shader = D3DCompile(g_MosaicShaderSource, strlen(g_MosaicShaderSource), nullptr, nullptr, nullptr, "VS_Mosaic", "vs_5_0", 0, 0, &blob, &errorBlob);
    if (SUCCEEDED(hr_shader)) {
        g_d3dDevice->CreateVertexShader(blob->GetBufferPointer(), blob->GetBufferSize(), nullptr, &g_vsMosaic);
        D3D11_INPUT_ELEMENT_DESC layout[] = {
            { "POSITION", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 0, D3D11_INPUT_PER_VERTEX_DATA, 0 },
            { "NORMAL", 0, DXGI_FORMAT_R32G32B32_FLOAT, 0, 12, D3D11_INPUT_PER_VERTEX_DATA, 0 },
            { "TEXCOORD", 0, DXGI_FORMAT_R32G32_SINT, 1, 0, D3D11_INPUT_PER_INSTANCE_DATA, 1 },
            { "TEXCOORD", 1, DXGI_FORMAT_R32_FLOAT, 1, 8, D3D11_INPUT_PER_INSTANCE_DATA, 1 },
            { "TEXCOORD", 4, DXGI_FORMAT_R32G32_FLOAT, 1, 12, D3D11_INPUT_PER_INSTANCE_DATA, 1 },
            { "TEXCOORD", 5, DXGI_FORMAT_R32_FLOAT, 1, 20, D3D11_INPUT_PER_INSTANCE_DATA, 1 },
            { "COLOR", 0, DXGI_FORMAT_R32G32B32A32_FLOAT, 1, 24, D3D11_INPUT_PER_INSTANCE_DATA, 1 },
        };
        g_d3dDevice->CreateInputLayout(layout, 7, blob->GetBufferPointer(), blob->GetBufferSize(), &g_ilMosaic);
        blob->Release();
    } else if (errorBlob) {
        printf("Mosaic VS Compile Error: %s\n", (char*)errorBlob->GetBufferPointer());
        errorBlob->Release();
    }
    
    hr_shader = D3DCompile(g_MosaicShaderSource, strlen(g_MosaicShaderSource), nullptr, nullptr, nullptr, "PS_Mosaic", "ps_5_0", 0, 0, &blob, &errorBlob);
    if (SUCCEEDED(hr_shader)) {
        g_d3dDevice->CreatePixelShader(blob->GetBufferPointer(), blob->GetBufferSize(), nullptr, &g_psMosaic);
        blob->Release();
    } else if (errorBlob) {
        printf("Mosaic PS Compile Error: %s\n", (char*)errorBlob->GetBufferPointer());
        errorBlob->Release();
    }
    
    cbDesc.ByteWidth = sizeof(MosaicConstants);
    g_d3dDevice->CreateBuffer(&cbDesc, nullptr, &g_cbMosaic);
    
    MosaicVertex cubeVertices[] = {
        // Front Face (z=1)
        {{0.0f, 0.0f, 1.0f}, {0,0,1}}, {{1.0f, 0.0f, 1.0f}, {0,0,1}}, {{1.0f, 1.0f, 1.0f}, {0,0,1}},
        {{0.0f, 0.0f, 1.0f}, {0,0,1}}, {{1.0f, 1.0f, 1.0f}, {0,0,1}}, {{0.0f, 1.0f, 1.0f}, {0,0,1}},
        // Back Face (z=0)
        {{1.0f, 0.0f, 0.0f}, {0,0,-1}}, {{0.0f, 0.0f, 0.0f}, {0,0,-1}}, {{0.0f, 1.0f, 0.0f}, {0,0,-1}},
        {{1.0f, 0.0f, 0.0f}, {0,0,-1}}, {{0.0f, 1.0f, 0.0f}, {0,0,-1}}, {{1.0f, 1.0f, 0.0f}, {0,0,-1}},
        // Top Face (y=0) 
        {{0.0f, 0.0f, 0.0f}, {0,-1,0}}, {{1.0f, 0.0f, 0.0f}, {0,-1,0}}, {{1.0f, 0.0f, 1.0f}, {0,-1,0}},
        {{0.0f, 0.0f, 0.0f}, {0,-1,0}}, {{1.0f, 0.0f, 1.0f}, {0,-1,0}}, {{0.0f, 0.0f, 1.0f}, {0,-1,0}},
        // Bottom Face (y=1)
        {{0.0f, 1.0f, 1.0f}, {0,1,0}}, {{1.0f, 1.0f, 1.0f}, {0,1,0}}, {{1.0f, 1.0f, 0.0f}, {0,1,0}},
        {{0.0f, 1.0f, 1.0f}, {0,1,0}}, {{1.0f, 1.0f, 0.0f}, {0,1,0}}, {{0.0f, 1.0f, 0.0f}, {0,1,0}},
        // Left Face (x=0)
        {{0.0f, 0.0f, 0.0f}, {-1,0,0}}, {{0.0f, 0.0f, 1.0f}, {-1,0,0}}, {{0.0f, 1.0f, 1.0f}, {-1,0,0}},
        {{0.0f, 0.0f, 0.0f}, {-1,0,0}}, {{0.0f, 1.0f, 1.0f}, {-1,0,0}}, {{0.0f, 1.0f, 0.0f}, {-1,0,0}},
        // Right Face (x=1)
        {{1.0f, 0.0f, 1.0f}, {1,0,0}}, {{1.0f, 0.0f, 0.0f}, {1,0,0}}, {{1.0f, 1.0f, 0.0f}, {1,0,0}},
        {{1.0f, 0.0f, 1.0f}, {1,0,0}}, {{1.0f, 1.0f, 0.0f}, {1,0,0}}, {{1.0f, 1.0f, 1.0f}, {1,0,0}}
    };
    D3D11_BUFFER_DESC vbDesc = {};
    vbDesc.Usage = D3D11_USAGE_IMMUTABLE;
    vbDesc.ByteWidth = sizeof(cubeVertices);
    vbDesc.BindFlags = D3D11_BIND_VERTEX_BUFFER;
    D3D11_SUBRESOURCE_DATA vbInit = {};
    vbInit.pSysMem = cubeVertices;
    g_d3dDevice->CreateBuffer(&vbDesc, &vbInit, &g_vbMosaic);

    D3D11_BLEND_DESC blendDesc = {};
    blendDesc.RenderTarget[0].BlendEnable = TRUE;
    blendDesc.RenderTarget[0].SrcBlend = D3D11_BLEND_ONE;
    blendDesc.RenderTarget[0].DestBlend = D3D11_BLEND_INV_SRC_ALPHA;
    blendDesc.RenderTarget[0].BlendOp = D3D11_BLEND_OP_ADD;
    blendDesc.RenderTarget[0].SrcBlendAlpha = D3D11_BLEND_ONE;
    blendDesc.RenderTarget[0].DestBlendAlpha = D3D11_BLEND_INV_SRC_ALPHA;
    blendDesc.RenderTarget[0].BlendOpAlpha = D3D11_BLEND_OP_ADD;
    blendDesc.RenderTarget[0].RenderTargetWriteMask = D3D11_COLOR_WRITE_ENABLE_ALL;
    g_d3dDevice->CreateBlendState(&blendDesc, &g_blendState);

    
    return true;
}

// Helper to draw a path geometry
void drawRing(float* radii, float* fluids, int pts, float scale, float cxx, float cyy, float thickOffset, float thickMult, float r, float g, float b, float a) {
    if (a <= 0.001f) return;
    
    g_brush->SetColor(D2D1::ColorF(r, g, b, a));

    ID2D1PathGeometry* path = nullptr;
    g_d2dFactory->CreatePathGeometry(&path);
    if (path) {
        ID2D1GeometrySink* sink = nullptr;
        path->Open(&sink);
        if (sink) {
            std::vector<D2D1_POINT_2F> outPts(pts + 1);
            std::vector<D2D1_POINT_2F> inPts(pts + 1);
            
            for (int i = 0; i <= pts; i++) {
                float angle = ((float)i / pts) * 2.0f * M_PI;
                float rad = radii[i];
                float t = thickOffset + (fluids[i] * thickMult);
                
                float r_out = rad + t / 2.0f;
                float r_in = rad - t / 2.0f;
                
                outPts[i] = D2D1::Point2F(cxx + cosf(angle) * r_out * scale, cyy + sinf(angle) * r_out * scale);
                inPts[i] = D2D1::Point2F(cxx + cosf(angle) * r_in * scale, cyy + sinf(angle) * r_in * scale);
            }
            
            sink->BeginFigure(outPts[0], D2D1_FIGURE_BEGIN_FILLED);
            for (int i = 1; i <= pts; i++) sink->AddLine(outPts[i]);
            for (int i = pts; i >= 0; i--) sink->AddLine(inPts[i]);
            sink->EndFigure(D2D1_FIGURE_END_CLOSED);
            sink->Close();
            sink->Release();
        }
        g_d2dRenderTarget->FillGeometry(path, g_brush);
        path->Release();
    }
}

__declspec(dllexport) uint8_t* render_frame(float* radii, float* fluids, int pts, float size, float base_thick, 
                                            float gr, float gg, float gb, float hr, float hg, float hb, 
                                            float op_mult) {
    if (!g_d2dRenderTarget) return nullptr;

    g_d2dRenderTarget->BeginDraw();
    g_d2dRenderTarget->Clear(D2D1::ColorF(0.0f, 0.0f, 0.0f, 0.0f));

    float scale = 512.0f / (size + 150.0f);
    float cxx = 256.0f;
    float cyy = 256.0f;
    
    // LAYER 1: Rear Cushion
    drawRing(radii, fluids, pts, scale, cxx, cyy, base_thick + 6.0f, 0.0f, gr, gg, gb, 0.156f * op_mult);
    
    // LAYER 2: Core Fluid (Feather, Core, Center approximations)
    float base_a = 180.0f / 255.0f * op_mult;
    float alpha_mod = 0.8f; // Average assumption
    
    // Feather
    drawRing(radii, fluids, pts, scale, cxx, cyy, base_thick + 5.0f, 18.0f, gr, gg, gb, base_a * 0.3f * alpha_mod);
    // Core
    drawRing(radii, fluids, pts, scale, cxx, cyy, base_thick, 18.0f, gr, gg, gb, base_a * 0.7f * alpha_mod);
    // Center (Brighter)
    float cr = gr + (1.0f - gr)*0.2f; cr = cr > 1.0f ? 1.0f : cr;
    float cg = gg + (1.0f - gg)*0.2f; cg = cg > 1.0f ? 1.0f : cg;
    float cb = gb + (1.0f - gb)*0.2f; cb = cb > 1.0f ? 1.0f : cb;
    drawRing(radii, fluids, pts, scale, cxx, cyy, base_thick, 18.0f * 0.3f, cr, cg, cb, base_a * 1.2f * alpha_mod);
    
    // LAYER 3: Inner Highlight
    drawRing(radii, fluids, pts, scale, cxx, cyy, base_thick * 0.5f, 0.0f, hr, hg, hb, (100.0f / 255.0f) * op_mult);

    g_d2dRenderTarget->EndDraw();

    int writeIndex = g_frameIndex % 3;
    g_d3dContext->CopyResource(g_stagingTextures[writeIndex], g_renderTexture);
    
    // Explicitly flush the command buffer to the GPU, otherwise Map with DO_NOT_WAIT will wait forever
    g_d3dContext->Flush();
    
    int readIndex = (g_frameIndex + 1) % 3;
    if (g_frameIndex < 2) readIndex = writeIndex; 
    
    D3D11_MAPPED_SUBRESOURCE mapped;
    if (SUCCEEDED(g_d3dContext->Map(g_stagingTextures[readIndex], 0, D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped))) {
        for (int y = 0; y < g_height; y++) {
            memcpy(g_pixelBuffer + y * (g_width * 4), 
                   (uint8_t*)mapped.pData + y * mapped.RowPitch, 
                   g_width * 4);
        }
        g_d3dContext->Unmap(g_stagingTextures[readIndex], 0);
    }
    
    g_frameIndex++;
    return g_pixelBuffer;
}

__declspec(dllexport) void destroy_visualizer() {
    if (g_samplerLinear) { g_samplerLinear->Release(); g_samplerLinear = nullptr; }
    if (g_blendState) { g_blendState->Release(); g_blendState = nullptr; }
    if (g_vbMosaic) { g_vbMosaic->Release(); g_vbMosaic = nullptr; }
    if (g_ibMosaic) { g_ibMosaic->Release(); g_ibMosaic = nullptr; }
    if (g_cbMosaic) { g_cbMosaic->Release(); g_cbMosaic = nullptr; }
    if (g_psMosaic) { g_psMosaic->Release(); g_psMosaic = nullptr; }
    if (g_vsMosaic) { g_vsMosaic->Release(); g_vsMosaic = nullptr; }
    if (g_ilMosaic) { g_ilMosaic->Release(); g_ilMosaic = nullptr; }
    if (g_renderTargetView) { g_renderTargetView->Release(); g_renderTargetView = nullptr; }
    if (g_cbFerrofluid) { g_cbFerrofluid->Release(); g_cbFerrofluid = nullptr; }
    if (g_psFerrofluid) { g_psFerrofluid->Release(); g_psFerrofluid = nullptr; }
    if (g_vsFullscreen) { g_vsFullscreen->Release(); g_vsFullscreen = nullptr; }
    if (g_pixelBuffer) { delete[] g_pixelBuffer; g_pixelBuffer = nullptr; }
    if (g_brush) { g_brush->Release(); g_brush = nullptr; }
    if (g_d2dRenderTarget) { g_d2dRenderTarget->Release(); g_d2dRenderTarget = nullptr; }
    if (g_dxgiSurface) { g_dxgiSurface->Release(); g_dxgiSurface = nullptr; }
    for (int i = 0; i < 3; i++) {
        if (g_stagingTextures[i]) { g_stagingTextures[i]->Release(); g_stagingTextures[i] = nullptr; }
    }
    if (g_renderTexture) { g_renderTexture->Release(); g_renderTexture = nullptr; }
    if (g_d3dContext) { g_d3dContext->Release(); g_d3dContext = nullptr; }
    if (g_d3dDevice) { g_d3dDevice->Release(); g_d3dDevice = nullptr; }
    if (g_d2dFactory) { g_d2dFactory->Release(); g_d2dFactory = nullptr; }
}

}

// ---------------------------------------------------------
// GPU 8-Bit Mosaic Visualizer Engine (Hardware Rendered in C++)
// ---------------------------------------------------------
#include <algorithm>

struct MosaicBlock {
    int gx, gy;
    float dist;
    float pdx, pdy;
    float pa;
    float r, g, b, a;
};

std::vector<MosaicBlock> g_blocks;
int g_mosaicSize = 512;
float g_blockSize = 12.0f;
int g_mosaicShape = 0; // 0=Square, 1=Rounded

extern "C" {

__declspec(dllexport) void init_mosaic(const uint8_t* rgba_pixels, int img_width, int img_height, float block_size, int shape) {
    g_blocks.clear();
    g_blockSize = block_size;
    g_mosaicShape = shape;
    
    int grid_dim = img_width;
    float max_dist = grid_dim / 2.0f;
    float margin = 3.0f;
    
    for (int gy = 0; gy < grid_dim; gy++) {
        for (int gx = 0; gx < grid_dim; gx++) {
            float dcx = gx - grid_dim / 2.0f + 0.5f;
            float dcy = gy - grid_dim / 2.0f + 0.5f;
            float dist = sqrtf(dcx*dcx + dcy*dcy);
            
            if (dist > max_dist + margin) continue;
            
            float pdx = dist > 0 ? dcx / dist : 0.0f;
            float pdy = dist > 0 ? dcy / dist : 0.0f;
            float pa = max_dist > 0 ? (dist / max_dist) * (block_size * 0.8f) : 0.0f;
            
            int idx = (gy * img_width + gx) * 4;
            
            MosaicBlock b;
            b.gx = gx; b.gy = gy; b.dist = dist; b.pdx = pdx; b.pdy = pdy; b.pa = pa;
            b.b = rgba_pixels[idx] / 255.0f;
            b.g = rgba_pixels[idx + 1] / 255.0f;
            b.r = rgba_pixels[idx + 2] / 255.0f;
            b.a = rgba_pixels[idx + 3] / 255.0f;
            g_blocks.push_back(b);
        }
    }
    
    std::sort(g_blocks.begin(), g_blocks.end(), [](const MosaicBlock& a, const MosaicBlock& b) {
        return a.dist > b.dist;
    });
    
    g_mosaicInstanceCount = g_blocks.size();
    if (g_mosaicInstanceCount > 0) {
        std::vector<MosaicInstance> instData(g_mosaicInstanceCount);
        for (int i = 0; i < g_mosaicInstanceCount; i++) {
            instData[i].gpos[0] = g_blocks[i].gx;
            instData[i].gpos[1] = g_blocks[i].gy;
            instData[i].dist = g_blocks[i].dist;
            instData[i].pdir[0] = g_blocks[i].pdx;
            instData[i].pdir[1] = g_blocks[i].pdy;
            instData[i].pa = g_blocks[i].pa;
            instData[i].color[0] = g_blocks[i].r;
            instData[i].color[1] = g_blocks[i].g;
            instData[i].color[2] = g_blocks[i].b;
            instData[i].color[3] = g_blocks[i].a;
        }
        
        if (g_ibMosaic && g_mosaicInstanceCapacity < g_mosaicInstanceCount) {
            g_ibMosaic->Release(); g_ibMosaic = nullptr;
        }
        if (!g_ibMosaic) {
            g_mosaicInstanceCapacity = g_mosaicInstanceCount + 1000;
            D3D11_BUFFER_DESC ibDesc = {};
            ibDesc.Usage = D3D11_USAGE_DYNAMIC;
            ibDesc.ByteWidth = sizeof(MosaicInstance) * g_mosaicInstanceCapacity;
            ibDesc.BindFlags = D3D11_BIND_VERTEX_BUFFER;
            ibDesc.CPUAccessFlags = D3D11_CPU_ACCESS_WRITE;
            g_d3dDevice->CreateBuffer(&ibDesc, nullptr, &g_ibMosaic);
        }
        
        D3D11_MAPPED_SUBRESOURCE mapped;
        if (SUCCEEDED(g_d3dContext->Map(g_ibMosaic, 0, D3D11_MAP_WRITE_DISCARD, 0, &mapped))) {
            memcpy(mapped.pData, instData.data(), sizeof(MosaicInstance) * g_mosaicInstanceCount);
            g_d3dContext->Unmap(g_ibMosaic, 0);
        }
    }
}



__declspec(dllexport) uint8_t* render_mosaic(float bass_e, float mids_e, float treble_e, 
                                             float ext_factor, float w_x, float w_y, float d_x, float d_y, 
                                             float bass_phase, float mids_phase, float treble_phase,
                                             float* ring_thick, float global_op) {
    if (!g_d3dContext || !g_renderTargetView) return nullptr;
    
    float clearColor[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    g_d3dContext->ClearRenderTargetView(g_renderTargetView, clearColor);
    g_d3dContext->OMSetRenderTargets(1, &g_renderTargetView, nullptr);
    
    D3D11_VIEWPORT vp = {};
    vp.Width = 512.0f;
    vp.Height = 512.0f;
    vp.MaxDepth = 1.0f;
    g_d3dContext->RSSetViewports(1, &vp);
    
    MosaicConstants cb = {};
    cb.bass_e = bass_e; cb.mids_e = mids_e; cb.treble_e = treble_e;
    cb.ext_factor = ext_factor;
    cb.w_x = w_x; cb.w_y = w_y; cb.d_x = d_x; cb.d_y = d_y;
    cb.bass_phase = bass_phase; cb.mids_phase = mids_phase; cb.treble_phase = treble_phase;
    cb.global_op = global_op;
    for(int i=0; i<4; i++) { cb.ring_thick_0_3[i] = ring_thick[i]; cb.ring_thick_4_7[i] = ring_thick[i+4]; }
    cb.grid_dim = g_mosaicSize / g_blockSize;
    cb.g_blockSize = g_blockSize;
    cb.grid_offset = (g_mosaicSize - (cb.grid_dim * g_blockSize)) / 2.0f;
    cb.g_mosaicShape = g_mosaicShape;
    
    g_d3dContext->UpdateSubresource(g_cbMosaic, 0, nullptr, &cb, 0, 0);
    
    UINT strides[2] = { sizeof(MosaicVertex), sizeof(MosaicInstance) };
    UINT offsets[2] = { 0, 0 };
    ID3D11Buffer* buffers[2] = { g_vbMosaic, g_ibMosaic };
    
    g_d3dContext->IASetInputLayout(g_ilMosaic);
    g_d3dContext->IASetVertexBuffers(0, 2, buffers, strides, offsets);
    g_d3dContext->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    
    g_d3dContext->OMSetBlendState(g_blendState, nullptr, 0xFFFFFFFF);
    
    g_d3dContext->VSSetShader(g_vsMosaic, nullptr, 0);
    g_d3dContext->VSSetConstantBuffers(0, 1, &g_cbMosaic);
    
    g_d3dContext->PSSetShader(g_psMosaic, nullptr, 0);
    g_d3dContext->PSSetConstantBuffers(0, 1, &g_cbMosaic);
    
    g_d3dContext->DrawInstanced(36, g_mosaicInstanceCount, 0, 0);
    
    g_d3dContext->OMSetBlendState(nullptr, nullptr, 0xFFFFFFFF);
    
    int writeIndex = g_frameIndex % 3;
    g_d3dContext->CopyResource(g_stagingTextures[writeIndex], g_renderTexture);
    g_d3dContext->Flush();
    
    int readIndex = (g_frameIndex + 1) % 3;
    if (g_frameIndex < 2) readIndex = writeIndex; 
    
    D3D11_MAPPED_SUBRESOURCE mapped;
    if (SUCCEEDED(g_d3dContext->Map(g_stagingTextures[readIndex], 0, D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped))) {
        for (int y = 0; y < g_height; y++) {
            memcpy(g_pixelBuffer + y * (g_width * 4), 
                   (uint8_t*)mapped.pData + y * mapped.RowPitch, 
                   g_width * 4);
        }
        g_d3dContext->Unmap(g_stagingTextures[readIndex], 0);
    }
    
    g_frameIndex++;
    return g_pixelBuffer;
}

} // extern "C"

// ---------------------------------------------------------
// 3D Liquid Ferrofluid Sphere Visualizer (Hardware Rendered in HLSL)
// ---------------------------------------------------------

ID3D11Texture2D* g_d3dFerroTexture = nullptr;
ID3D11ShaderResourceView* g_srvFerroTexture = nullptr;
int g_ferroWidth = 512;
int g_ferroHeight = 512;

extern "C" {

__declspec(dllexport) void init_ferrofluid(const uint8_t* rgba_pixels, int img_width, int img_height) {
    if (g_srvFerroTexture) { g_srvFerroTexture->Release(); g_srvFerroTexture = nullptr; }
    if (g_d3dFerroTexture) { g_d3dFerroTexture->Release(); g_d3dFerroTexture = nullptr; }
    
    if (rgba_pixels && img_width > 0 && img_height > 0) {
        D3D11_TEXTURE2D_DESC desc = {};
        desc.Width = img_width;
        desc.Height = img_height;
        desc.MipLevels = 1;
        desc.ArraySize = 1;
        desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
        desc.SampleDesc.Count = 1;
        desc.Usage = D3D11_USAGE_DEFAULT;
        desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
        
        D3D11_SUBRESOURCE_DATA initData = {};
        initData.pSysMem = rgba_pixels;
        initData.SysMemPitch = img_width * 4;
        
        if (SUCCEEDED(g_d3dDevice->CreateTexture2D(&desc, &initData, &g_d3dFerroTexture))) {
            D3D11_SHADER_RESOURCE_VIEW_DESC srvDesc = {};
            srvDesc.Format = desc.Format;
            srvDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
            srvDesc.Texture2D.MipLevels = 1;
            g_d3dDevice->CreateShaderResourceView(g_d3dFerroTexture, &srvDesc, &g_srvFerroTexture);
        }
    }
}

__declspec(dllexport) uint8_t* render_ferrofluid(
    float bass_e, float mids_e, float treble_e, 
    float time_t, int use_texture, uint32_t dominant_color, float global_op) 
{
    if (!g_d3dContext || !g_renderTargetView) return nullptr;
    
    float clearColor[4] = {0.0f, 0.0f, 0.0f, 0.0f};
    g_d3dContext->ClearRenderTargetView(g_renderTargetView, clearColor);
    g_d3dContext->OMSetRenderTargets(1, &g_renderTargetView, nullptr);
    
    D3D11_VIEWPORT vp = {};
    vp.Width = 512.0f;
    vp.Height = 512.0f;
    vp.MaxDepth = 1.0f;
    g_d3dContext->RSSetViewports(1, &vp);
    
    FerrofluidConstants cb;
    cb.bass_e = bass_e;
    cb.mids_e = mids_e;
    cb.treble_e = treble_e;
    cb.time_t = time_t;
    cb.use_texture = use_texture;
    cb.dominant_color[0] = ((dominant_color >> 16) & 0xFF) / 255.0f;
    cb.dominant_color[1] = ((dominant_color >> 8) & 0xFF) / 255.0f;
    cb.dominant_color[2] = (dominant_color & 0xFF) / 255.0f;
    cb.global_op = global_op;
    
    g_d3dContext->UpdateSubresource(g_cbFerrofluid, 0, nullptr, &cb, 0, 0);
    
    g_d3dContext->IASetInputLayout(nullptr);
    g_d3dContext->IASetPrimitiveTopology(D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST);
    
    g_d3dContext->VSSetShader(g_vsFullscreen, nullptr, 0);
    g_d3dContext->PSSetShader(g_psFerrofluid, nullptr, 0);
    
    g_d3dContext->PSSetConstantBuffers(0, 1, &g_cbFerrofluid);
    
    if (use_texture && g_srvFerroTexture) {
        g_d3dContext->PSSetShaderResources(0, 1, &g_srvFerroTexture);
    }
    g_d3dContext->PSSetSamplers(0, 1, &g_samplerLinear);
    
    // Draw Fullscreen Quad
    g_d3dContext->Draw(3, 0);
    
    // Unbind shader resources so we don't hold locks
    ID3D11ShaderResourceView* nullSRV = nullptr;
    g_d3dContext->PSSetShaderResources(0, 1, &nullSRV);
    
    int writeIndex = g_frameIndex % 3;
    g_d3dContext->CopyResource(g_stagingTextures[writeIndex], g_renderTexture);
    g_d3dContext->Flush();
    
    int readIndex = (g_frameIndex + 1) % 3;
    if (g_frameIndex < 2) readIndex = writeIndex; 
    
    D3D11_MAPPED_SUBRESOURCE mapped;
    if (SUCCEEDED(g_d3dContext->Map(g_stagingTextures[readIndex], 0, D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped))) {
        for (int y = 0; y < g_height; y++) {
            memcpy(g_pixelBuffer + y * (g_width * 4), 
                   (uint8_t*)mapped.pData + y * mapped.RowPitch, 
                   g_width * 4);
        }
        g_d3dContext->Unmap(g_stagingTextures[readIndex], 0);
    }
    
    g_frameIndex++;
    return g_pixelBuffer;
}

// ==========================================
// DIRECT2D UI IMMEDIATE MODE API
// ==========================================
IDWriteFactory* g_dwriteFactory = nullptr;
ID2D1PathGeometry* g_ringGeometry = nullptr;

__declspec(dllexport) void init_ui_engine() {
    if (!g_dwriteFactory) {
        DWriteCreateFactory(DWRITE_FACTORY_TYPE_SHARED, __uuidof(IDWriteFactory), (IUnknown**)&g_dwriteFactory);
    }
}

__declspec(dllexport) void begin_ui_frame(float clear_r, float clear_g, float clear_b, float clear_a) {
    if (!g_d2dRenderTarget) return;
    g_d2dRenderTarget->BeginDraw();
    g_d2dRenderTarget->Clear(D2D1::ColorF(clear_r, clear_g, clear_b, clear_a));
}

__declspec(dllexport) void draw_d2d_ring(float* radii, float* fluids, int pts, float cx, float cy, float base_thick, uint32_t color, float opacity) {
    if (!g_d2dRenderTarget || !g_d2dFactory) return;

    if (g_ringGeometry) { g_ringGeometry->Release(); g_ringGeometry = nullptr; }
    g_d2dFactory->CreatePathGeometry(&g_ringGeometry);

    ID2D1GeometrySink* sink = nullptr;
    g_ringGeometry->Open(&sink);

    float PI = 3.14159265f;
    
    bool first = true;
    for (int i = 0; i <= pts; i++) {
        float angle = ((float)i / (float)pts) * 2.0f * PI - (PI / 2.0f);
        float r = radii[i];
        float t = base_thick + (fluids[i % pts] * 18.0f);
        float r_out = r + t / 2.0f;
        D2D1_POINT_2F pt = D2D1::Point2F(cx + cosf(angle) * r_out, cy + sinf(angle) * r_out);
        
        if (first) { sink->BeginFigure(pt, D2D1_FIGURE_BEGIN_FILLED); first = false; }
        else { sink->AddLine(pt); }
    }

    for (int i = pts; i >= 0; i--) {
        float angle = ((float)i / (float)pts) * 2.0f * PI - (PI / 2.0f);
        float r = radii[i];
        float t = base_thick + (fluids[i % pts] * 18.0f);
        float r_in = r - t / 2.0f;
        D2D1_POINT_2F pt = D2D1::Point2F(cx + cosf(angle) * r_in, cy + sinf(angle) * r_in);
        sink->AddLine(pt);
    }

    sink->EndFigure(D2D1_FIGURE_END_CLOSED);
    sink->Close();
    sink->Release();

    float a = (float)((color >> 24) & 0xFF) / 255.0f * opacity;
    float r_c = (float)((color >> 16) & 0xFF) / 255.0f;
    float g_c = (float)((color >> 8) & 0xFF) / 255.0f;
    float b_c = (float)(color & 0xFF) / 255.0f;

    g_brush->SetColor(D2D1::ColorF(r_c, g_c, b_c, a));
    g_d2dRenderTarget->FillGeometry(g_ringGeometry, g_brush);
}

__declspec(dllexport) void draw_d2d_image(const uint8_t* rgba, int w, int h, float cx, float cy, float scale) {
    if (!g_d2dRenderTarget || !rgba) return;

    ID2D1Bitmap* bitmap = nullptr;
    D2D1_BITMAP_PROPERTIES props = {};
    props.pixelFormat = D2D1::PixelFormat(DXGI_FORMAT_B8G8R8A8_UNORM, D2D1_ALPHA_MODE_PREMULTIPLIED);
    props.dpiX = 96.0f;
    props.dpiY = 96.0f;

    uint8_t* bgra = new uint8_t[w * h * 4];
    for (int i = 0; i < w * h * 4; i += 4) {
        bgra[i] = rgba[i+2];     
        bgra[i+1] = rgba[i+1];   
        bgra[i+2] = rgba[i];     
        bgra[i+3] = rgba[i+3];   
        float a = bgra[i+3] / 255.0f;
        bgra[i] = (uint8_t)(bgra[i] * a);
        bgra[i+1] = (uint8_t)(bgra[i+1] * a);
        bgra[i+2] = (uint8_t)(bgra[i+2] * a);
    }

    g_d2dRenderTarget->CreateBitmap(D2D1::SizeU(w, h), bgra, w * 4, &props, &bitmap);
    delete[] bgra;

    if (bitmap) {
        float fw = w * scale;
        float fh = h * scale;
        D2D1_RECT_F dest = D2D1::RectF(cx - fw/2.0f, cy - fh/2.0f, cx + fw/2.0f, cy + fh/2.0f);
        g_d2dRenderTarget->DrawBitmap(bitmap, &dest, 1.0f, D2D1_BITMAP_INTERPOLATION_MODE_LINEAR);
        bitmap->Release();
    }
}

__declspec(dllexport) uint8_t* end_ui_frame() {
    if (g_d2dRenderTarget) {
        g_d2dRenderTarget->EndDraw();
    }
    
    // Copy the rendered surface to staging and return the buffer
    int writeIndex = g_frameIndex % 3;
    g_d3dContext->CopyResource(g_stagingTextures[writeIndex], g_renderTexture);
    g_d3dContext->Flush();
    
    int readIndex = (g_frameIndex + 1) % 3;
    if (g_frameIndex < 2) readIndex = writeIndex; 
    
    D3D11_MAPPED_SUBRESOURCE mapped;
    if (SUCCEEDED(g_d3dContext->Map(g_stagingTextures[readIndex], 0, D3D11_MAP_READ, D3D11_MAP_FLAG_DO_NOT_WAIT, &mapped))) {
        for (int y = 0; y < g_height; y++) {
            memcpy(g_pixelBuffer + y * (g_width * 4), 
                   (uint8_t*)mapped.pData + y * mapped.RowPitch, 
                   g_width * 4);
        }
        g_d3dContext->Unmap(g_stagingTextures[readIndex], 0);
    }
    
    g_frameIndex++;
    return g_pixelBuffer;
}

} // extern "C"
