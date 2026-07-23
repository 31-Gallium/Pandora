import os
import re

file_path = r"c:\Users\Base\Desktop\Seb\Pandora\engine_src\visualizer_core.cpp"
with open(file_path, "r") as f:
    code = f.read()

# 1. Add Mosaic Globals and Blend State
globals_addition = """
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

extern "C" {"""

code = code.replace('extern "C" {\n    __declspec(dllexport) DWORD NvOptimusEnablement = 1;', globals_addition + '\n    __declspec(dllexport) DWORD NvOptimusEnablement = 1;')

# 2. Add Mosaic init in init_visualizer
mosaic_init = """
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
        printf("Mosaic VS Compile Error: %s\\n", (char*)errorBlob->GetBufferPointer());
        errorBlob->Release();
    }
    
    hr_shader = D3DCompile(g_MosaicShaderSource, strlen(g_MosaicShaderSource), nullptr, nullptr, nullptr, "PS_Mosaic", "ps_5_0", 0, 0, &blob, &errorBlob);
    if (SUCCEEDED(hr_shader)) {
        g_d3dDevice->CreatePixelShader(blob->GetBufferPointer(), blob->GetBufferSize(), nullptr, &g_psMosaic);
        blob->Release();
    } else if (errorBlob) {
        printf("Mosaic PS Compile Error: %s\\n", (char*)errorBlob->GetBufferPointer());
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
"""

code = code.replace('g_d3dDevice->CreateSamplerState(&sampDesc, &g_samplerLinear);', 'g_d3dDevice->CreateSamplerState(&sampDesc, &g_samplerLinear);\n' + mosaic_init)

# 3. Add to destroy_visualizer
destroy_addition = """
    if (g_blendState) { g_blendState->Release(); g_blendState = nullptr; }
    if (g_vbMosaic) { g_vbMosaic->Release(); g_vbMosaic = nullptr; }
    if (g_ibMosaic) { g_ibMosaic->Release(); g_ibMosaic = nullptr; }
    if (g_cbMosaic) { g_cbMosaic->Release(); g_cbMosaic = nullptr; }
    if (g_psMosaic) { g_psMosaic->Release(); g_psMosaic = nullptr; }
    if (g_vsMosaic) { g_vsMosaic->Release(); g_vsMosaic = nullptr; }
    if (g_ilMosaic) { g_ilMosaic->Release(); g_ilMosaic = nullptr; }"""

code = code.replace('if (g_samplerLinear) { g_samplerLinear->Release(); g_samplerLinear = nullptr; }', 'if (g_samplerLinear) { g_samplerLinear->Release(); g_samplerLinear = nullptr; }' + destroy_addition)

# 4. Replace init_mosaic and render_mosaic logic
old_init_mosaic = """
__declspec(dllexport) void init_mosaic(const uint8_t* rgba_pixels, int img_width, int img_height, float block_size, int shape) {
    g_blocks.clear();
    g_blockSize = block_size;
    g_mosaicShape = shape;
    
    int grid_dim = img_width; // Python pre-scales the image to grid_dim x grid_dim
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
            b.gx = gx;
            b.gy = gy;
            b.dist = dist;
            b.pdx = pdx;
            b.pdy = pdy;
            b.pa = pa;
            // PyQt ARGB32 memory layout is BGRA
            b.b = rgba_pixels[idx] / 255.0f;
            b.g = rgba_pixels[idx + 1] / 255.0f;
            b.r = rgba_pixels[idx + 2] / 255.0f;
            b.a = rgba_pixels[idx + 3] / 255.0f;
            
            g_blocks.push_back(b);
        }
    }
    
    // Sort by distance (descending) so center draws on top
    std::sort(g_blocks.begin(), g_blocks.end(), [](const MosaicBlock& a, const MosaicBlock& b) {
        return a.dist > b.dist;
    });
}"""

new_init_mosaic = """
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
"""
code = code.replace(old_init_mosaic, new_init_mosaic)

# 5. Replace render_mosaic
start_render_mosaic = code.find('__declspec(dllexport) uint8_t* render_mosaic(')
end_render_mosaic = code.find('} // extern "C"', start_render_mosaic)

new_render_mosaic = """
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
"""

code = code[:start_render_mosaic] + new_render_mosaic + "\n" + code[end_render_mosaic:]

with open(file_path, "w") as f:
    f.write(code)

print("visualizer_core.cpp patched successfully!")
