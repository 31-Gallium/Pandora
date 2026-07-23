#pragma once

const char* g_FerrofluidShaderSource = R"(
cbuffer Constants : register(b0) {
    float bass_e;
    float mids_e;
    float treble_e;
    float time_t;
    int use_texture;
    float3 dominant_color;
    float global_op;
    float3 padding;
};

Texture2D texAlbum : register(t0);
SamplerState sampLinear : register(s0);

struct VS_OUT {
    float4 pos : SV_Position;
    float2 uv : TEXCOORD0;
};

VS_OUT VS_Fullscreen(uint id : SV_VertexID) {
    VS_OUT output;
    output.uv = float2((id << 1) & 2, id & 2);
    output.pos = float4(output.uv * float2(2, -2) + float2(-1, 1), 0, 1);
    return output;
}

float4 PS_Ferrofluid(VS_OUT input) : SV_Target {
    float cx = 256.0f;
    float cy = 256.0f;
    float base_radius = 180.0f;
    
    float x = input.uv.x * 512.0f;
    float y = input.uv.y * 512.0f;
    
    float dx = x - cx;
    float dy = y - cy;
    float dist = sqrt(dx*dx + dy*dy);
    
    if (dist >= base_radius * 1.5f) {
        return float4(0,0,0,0);
    }
    
    float z = 0.0f;
    if (dist < base_radius) {
        z = sqrt(base_radius * base_radius - dist * dist);
    }
    
    float angle = atan2(dy, dx);
    float bass_spikes = sin(angle * 6.0f + time_t * 2.0f) * sin(dist * 0.05f - time_t * 3.0f);
    float bass_disp = (bass_e > 0.5f ? (bass_e - 0.5f) * 2.0f : 0.0f) * 60.0f * bass_spikes;
    float mids_disp = mids_e * 15.0f * sin(dist * 0.1f - time_t * 5.0f);
    float treble_disp = treble_e * 5.0f * sin(angle * 20.0f) * sin(dist * 0.2f - time_t * 10.0f);
    
    float edge_factor = dist / base_radius;
    if (edge_factor > 1.0f) {
        float falloff = 1.0f - (dist - base_radius) / (base_radius * 0.5f);
        if (falloff < 0.0f) falloff = 0.0f;
        z = (bass_disp + mids_disp + treble_disp) * falloff * falloff;
    } else {
        z += bass_disp * edge_factor + mids_disp + treble_disp;
    }
    
    if (z <= 0.0f) {
        return float4(0,0,0,0);
    }
    
    float dzdx = ddx(z);
    float dzdy = ddy(z);
    float3 normal = normalize(float3(-dzdx, -dzdy, 2.0f));
    
    float3 ldir = normalize(float3(0.5f, -0.5f, 1.0f));
    
    float diffuse = max(0.0f, dot(normal, ldir));
    float3 rdir = reflect(-ldir, normal);
    float specular = pow(max(0.0f, rdir.z), 64.0f);
    
    float rim = pow(1.0f - max(0.0f, normal.z), 3.0f);
    
    float3 col = dominant_color;
    
    if (use_texture > 0) {
        float proj_dx = clamp((x - cx) / base_radius, -1.0f, 1.0f);
        float proj_dy = clamp((y - cy) / base_radius, -1.0f, 1.0f);
        float u = 0.5f + (asin(proj_dx) / 3.14159f);
        float v = 0.5f + (asin(proj_dy) / 3.14159f);
        
        float4 t_col = texAlbum.Sample(sampLinear, float2(u, v));
        col = t_col.rgb;
    }
    
    float ambient = 0.15f;
    float3 out_color = col * (ambient + diffuse * 0.8f) + specular + rim * col * 0.5f;
    
    out_color = min(float3(1.0f, 1.0f, 1.0f), out_color);
    
    float alpha = z / 50.0f;
    alpha = min(1.0f, alpha) * global_op;
    if (alpha <= 0.05f) return float4(0,0,0,0);
    
    return float4(out_color * alpha, alpha); // Premultiplied alpha
}
)";

const char* g_MosaicShaderSource = R"(
cbuffer Constants : register(b0) {
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
    float4 ring_thick_0_3;
    float4 ring_thick_4_7;
    float grid_dim;
    float g_blockSize;
    float grid_offset;
    float g_mosaicShape;
};

struct VS_IN {
    float3 pos : POSITION; // Cube vertices (0..1)
    float3 norm : NORMAL;
};

struct INSTANCE_DATA {
    int2 gpos : TEXCOORD0;
    float dist : TEXCOORD1;
    float2 pdir : TEXCOORD4;
    float pa : TEXCOORD5;
    float4 color : COLOR0;
};

struct VS_OUT {
    float4 pos : SV_Position;
    float4 color : COLOR0;
};

VS_OUT VS_Mosaic(VS_IN input, INSTANCE_DATA inst) {
    VS_OUT output;
    
    float base_bx = inst.gpos.x * g_blockSize;
    float base_by = inst.gpos.y * g_blockSize;
    float bx = base_bx;
    float by = base_by;
    
    bx += inst.pdir.x * inst.pa * ext_factor;
    by += inst.pdir.y * inst.pa * ext_factor;
    
    float3 col = inst.color.rgb;
    float draw_size = g_blockSize - 2.0f;
    
    float total_over = max(0.0f, bass_e - 0.75f) / 0.25f + max(0.0f, mids_e - 0.90f) / 0.10f + max(0.0f, treble_e - 0.75f) / 0.25f;
    float bloom = 1.0f + (total_over / 3.0f) * 4.5f;
    
    float bass_ripple = 0.5f + 0.5f * sin(bass_phase - inst.dist * 0.8f);
    float bass_grow = (bass_e * bloom * bass_ripple) * (g_blockSize * 0.4f);
    float idle_shrink = g_blockSize * 0.4f;
    float effective_shrink = idle_shrink - bass_grow;
    effective_shrink = max(effective_shrink, -g_blockSize * 1.75f);
    
    bx += effective_shrink / 2.0f;
    by += effective_shrink / 2.0f;
    draw_size -= effective_shrink;
    draw_size = max(1.0f, draw_size);
    
    float mids_wave = 0.5f + 0.5f * sin(mids_phase - inst.dist * 0.5f);
    if (mids_e > 0.05f) {
        float light_factor = (30.0f * mids_e * mids_wave) / 255.0f;
        col = min(float3(1,1,1), col + light_factor);
    }
    
    float t_coord_scaled = (inst.gpos.x * w_x + inst.gpos.y * w_y) * 1.5f;
    float treble_ripple = 0.5f + 0.5f * sin(treble_phase - t_coord_scaled);
    float displacement = (treble_ripple - 0.5f) * 2.0f * (treble_e * treble_e) * (g_blockSize * 0.25f);
    bx += displacement * d_x;
    by += displacement * d_y;
    
    float bz = 0.0f;
    float extrusion_z = 0.0f;
    if (ext_factor > 0.01f) {
        float dist_norm = clamp(inst.dist / (grid_dim / 2.0f), 0.0f, 1.0f);
        float band_idx_float = dist_norm * 7.0f;
        int b_low = floor(band_idx_float);
        int b_high = min(7, ceil(band_idx_float));
        float b_blend = band_idx_float - b_low;
        
        float r_low = (b_low < 4) ? ring_thick_0_3[b_low] : ring_thick_4_7[b_low - 4];
        float r_high = (b_high < 4) ? ring_thick_0_3[b_high] : ring_thick_4_7[b_high - 4];
        
        float extrusion = lerp(r_low, r_high, b_blend);
        extrusion_z = (bass_e * 7.5f) + (extrusion * 2.5f);
        
        bx += inst.pdir.x * extrusion_z * ext_factor;
        by += inst.pdir.y * extrusion_z * ext_factor;
    }
    
    float px = bx + input.pos.x * draw_size;
    float py = by + input.pos.y * draw_size;
    float pz = input.pos.z;
    
    if (pz < 0.5f) {
        px = base_bx + input.pos.x * draw_size;
        py = base_by + input.pos.y * draw_size;
        col = col * 0.4f;
    } else {
        px = bx + input.pos.x * draw_size;
        py = by + input.pos.y * draw_size;
    }
    
    px += grid_offset;
    py += grid_offset;
    
    float ndc_x = (px / 512.0f) * 2.0f - 1.0f;
    float ndc_y = 1.0f - (py / 512.0f) * 2.0f;
    
    output.pos = float4(ndc_x, ndc_y, 0.5f, 1.0f);
    
    float alpha = inst.color.a * global_op;
    output.color = float4(col * alpha, alpha); // Premultiplied alpha
    
    return output;
}

float4 PS_Mosaic(VS_OUT input) : SV_Target {
    return input.color;
}
)";
