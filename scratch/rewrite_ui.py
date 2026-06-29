import re
import os

filepath = r'c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\prototype.html'
with open(filepath, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update CSS block
css_new = """
/* ═══════════════════════════════════════════════════════════════
   RESET & TOKENS
   ═══════════════════════════════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    /* Surfaces */
    --bg: #0a0a0c;
    --panel-bg: rgba(18, 18, 22, 0.4);
    --panel-border: rgba(255,255,255,0.04);
    --card-bg: rgba(255,255,255,0.015);
    --card-border: rgba(255,255,255,0.03);
    --card-hover-bg: rgba(255,255,255,0.03);
    --card-hover-border: rgba(255,255,255,0.06);

    /* Accents per section */
    --accent: #26c0d3;
    --accent-glow: rgba(38, 192, 211, 0.15); /* Softer, lower opacity */
    --accent-general: #26c0d3;
    --accent-templates: #a580e2;
    --accent-folders: #43d06a;
    --accent-halo: #e86ab4;
    --accent-hub: #e2a058;
    --accent-display: #e2a058;

    /* Text */
    --text-1: #e2e2e2;
    --text-2: #8a8a93;
    --text-3: #5a5a64;

    /* Misc */
    --green: #43d06a;
    --purple: #a580e2;
    --pink: #e86ab4;
    --orange: #e2a058;
    --yellow: #d8df70;
    --red: #e04f4f;
    --cyan: #26c0d3;

    --radius: 16px;
    --radius-sm: 8px;
    --radius-xs: 4px;
    --sidebar-w: 64px;
    --sidebar-exp: 220px;
    --header-h: 48px;
    --transition: cubic-bezier(0.4, 0, 0.2, 1);
}

html, body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: var(--bg);
    color: var(--text-1);
    height: 100vh;
    overflow: hidden;
    user-select: none;
    -webkit-font-smoothing: antialiased;
}

/* ═══════════════════════════════════════════════════════════════
   NOISE TEXTURE OVERLAY
   ═══════════════════════════════════════════════════════════════ */
body::after {
    content: '';
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 9999;
    opacity: 0.02;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    background-size: 180px;
}

/* ═══════════════════════════════════════════════════════════════
   SHELL LAYOUT
   ═══════════════════════════════════════════════════════════════ */
.shell {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

/* ─── Title Bar ─── */
.titlebar {
    height: var(--header-h);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    flex-shrink: 0;
    -webkit-app-region: drag;
    z-index: 10;
}

/* Page pill */
.page-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 24px;
    padding: 6px 16px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    color: var(--text-2);
    backdrop-filter: blur(12px);
    transition: all 0.3s var(--transition);
    cursor: grab;
}
.page-pill .pill-dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--text-3);
    transition: background 0.3s, box-shadow 0.3s;
}

.close-btn {
    -webkit-app-region: no-drag;
    position: absolute;
    right: 24px;
    width: 28px; height: 28px;
    border: none;
    background: transparent;
    color: var(--text-2);
    border-radius: 50%;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
}
.close-btn:hover { background: rgba(255,255,255,0.05); color: var(--text-1); }

/* ─── Body ─── */
.body-wrap {
    display: flex;
    flex: 1;
    min-height: 0;
    padding: 0 16px 16px 16px;
    gap: 16px;
}

/* ═══════════════════════════════════════════════════════════════
   SIDEBAR
   ═══════════════════════════════════════════════════════════════ */
.sidebar {
    width: var(--sidebar-w);
    background: var(--panel-bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    backdrop-filter: blur(24px);
    display: flex;
    flex-direction: column;
    padding: 16px 0;
    gap: 4px;
    transition: width 0.35s var(--transition);
    overflow: hidden;
    flex-shrink: 0;
    position: relative;
}
.sidebar.expanded { width: var(--sidebar-exp); }

/* Ambient glow - Softer */
.sidebar::before {
    content: '';
    position: absolute;
    right: -60px;
    top: 50%;
    width: 120px;
    height: 300px;
    transform: translateY(-50%);
    background: radial-gradient(ellipse, var(--accent-glow) 0%, transparent 60%);
    pointer-events: none;
    transition: opacity 0.3s;
    opacity: 0.3;
    filter: blur(20px);
}

/* Logo */
.logo-area {
    display: flex;
    align-items: center;
    padding: 8px 0;
    padding-left: 20px;
    height: 48px;
    cursor: pointer;
    margin-bottom: 16px;
    flex-shrink: 0;
    gap: 16px;
    overflow: hidden;
}
.logo-area svg { flex-shrink: 0; transition: transform 0.3s var(--transition); width: 24px; height: 24px; }
.logo-name {
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 2px;
    color: var(--text-1);
    white-space: nowrap;
    opacity: 0;
    transform: translateX(-8px);
    transition: opacity 0.25s 0.05s, transform 0.25s 0.05s;
}
.sidebar.expanded .logo-name { opacity: 1; transform: translateX(0); }

/* Nav Items */
.nav-item {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 10px 0;
    padding-left: 22px;
    margin: 2px 8px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: all 0.15s;
    color: var(--text-2);
    position: relative;
    white-space: nowrap;
    font-size: 13px;
    font-weight: 500;
}
.nav-item:hover { background: rgba(255,255,255,0.03); color: var(--text-1); }
.nav-item.active { color: var(--text-1); }
.nav-item.active svg { color: var(--accent); }
.nav-item.active::before {
    content: '';
    position: absolute;
    left: -8px; top: 50%; transform: translateY(-50%);
    width: 4px; height: 16px;
    border-radius: 0 4px 4px 0;
    background: var(--accent);
    box-shadow: 0 0 16px var(--accent-glow);
}
.nav-item svg { flex-shrink: 0; width: 20px; height: 20px; }
.nav-label {
    opacity: 0;
    transform: translateX(-6px);
    transition: opacity 0.2s 0.08s, transform 0.2s 0.08s;
    pointer-events: none;
}
.sidebar.expanded .nav-label { opacity: 1; transform: translateX(0); pointer-events: auto; }

/* Tooltip on collapsed sidebar */
.nav-item[data-tooltip]:not(.sidebar.expanded .nav-item)::after {
    content: attr(data-tooltip);
}

/* ═══════════════════════════════════════════════════════════════
   MAIN CONTENT PANEL
   ═══════════════════════════════════════════════════════════════ */
.main {
    flex: 1;
    background: var(--panel-bg);
    border: 1px solid var(--panel-border);
    border-radius: var(--radius);
    backdrop-filter: blur(24px);
    overflow-y: auto;
    overflow-x: hidden;
    padding: 48px 64px; /* More generous padding */
    min-width: 0;
    position: relative;
}
.main::-webkit-scrollbar { width: 5px; }
.main::-webkit-scrollbar-track { background: transparent; }
.main::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.05); border-radius: 10px; }
.main::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.1); }

/* ═══════════════════════════════════════════════════════════════
   TAB PAGES
   ═══════════════════════════════════════════════════════════════ */
.tab-page {
    display: none;
    animation: tabEnter 0.35s var(--transition);
    max-width: 800px;
    margin: 0 auto;
}
.tab-page.active { display: block; }
@keyframes tabEnter {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ═══════════════════════════════════════════════════════════════
   SECTION HEADERS
   ═══════════════════════════════════════════════════════════════ */
.section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 24px;
    color: var(--text-3);
    position: relative;
}
.section-header:not(:first-child) {
    margin-top: 56px;
}
.section-header .sh-text { color: var(--text-2); }

/* ═══════════════════════════════════════════════════════════════
   CONTROLS (Minimal, no big cards)
   ═══════════════════════════════════════════════════════════════ */
.control-group {
    display: flex;
    flex-direction: column;
    gap: 24px; /* 8px grid based */
    margin-bottom: 32px;
}

.control-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.control-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.control-label {
    font-size: 14px;
    font-weight: 500;
    color: var(--text-1);
    letter-spacing: 0.2px;
}
.control-label.has-tip {
    border-bottom: 1px dotted rgba(255,255,255,0.2);
    cursor: help;
}

/* ─── Range Slider ─── */
input[type=range] {
    -webkit-appearance: none;
    width: 100%;
    background: transparent;
    padding: 8px 0;
}
input[type=range]::-webkit-slider-runnable-track {
    height: 3px;
    border-radius: 2px;
    background: linear-gradient(to right,
        var(--section-accent, var(--accent)) 0%,
        var(--section-accent, var(--accent)) var(--fill, 50%),
        rgba(255,255,255,0.06) var(--fill, 50%),
        rgba(255,255,255,0.06) 100%
    );
}
input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none;
    height: 12px; width: 12px;
    border-radius: 50%;
    background: #fff;
    margin-top: -4px;
    cursor: pointer;
    box-shadow: 0 0 10px rgba(0,0,0,0.5);
    transition: transform 0.1s;
}
input[type=range]::-webkit-slider-thumb:hover {
    transform: scale(1.2);
}

.range-val {
    font-size: 13px;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-variant-numeric: tabular-nums;
    color: var(--text-2);
    min-width: 32px;
    text-align: right;
}

/* ─── Select (minimal) ─── */
select {
    -webkit-appearance: none;
    background: transparent;
    border: none;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    padding: 4px 24px 4px 0;
    border-radius: 0;
    font-size: 13px;
    font-family: inherit;
    font-weight: 500;
    color: var(--text-1);
    cursor: pointer;
    outline: none;
    transition: border-color 0.2s;
    background-image: url("data:image/svg+xml,%3Csvg fill='%238a8a93' viewBox='0 0 24 24' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 0 center;
    background-size: 16px;
}
select:hover, select:focus { border-color: var(--section-accent, var(--accent)); }
select option { background: #14141f; color: white; }

/* ─── Toggle Switch (Minimal) ─── */
.toggle-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid rgba(255,255,255,0.03);
}
.toggle-row:last-child {
    border-bottom: none;
}
.toggle {
    position: relative;
    width: 36px; height: 20px;
    flex-shrink: 0;
}
.toggle input { opacity: 0; width: 0; height: 0; position: absolute; }
.toggle .track {
    position: absolute;
    inset: 0;
    background: rgba(255,255,255,0.05);
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.05);
    cursor: pointer;
    transition: background 0.2s, border-color 0.2s;
}
.toggle .track::after {
    content: '';
    position: absolute;
    left: 2px; top: 2px;
    width: 14px; height: 14px;
    background: var(--text-2);
    border-radius: 50%;
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.2s;
}
.toggle input:checked + .track {
    background: color-mix(in srgb, var(--section-accent, var(--accent)) 15%, transparent);
    border-color: color-mix(in srgb, var(--section-accent, var(--accent)) 30%, transparent);
}
.toggle input:checked + .track::after {
    transform: translateX(16px);
    background: var(--section-accent, var(--accent));
    box-shadow: 0 0 10px var(--accent-glow);
}

/* ─── Keybind — Minimal ─── */
.keybind-key {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    padding: 6px 12px;
    border-radius: var(--radius-xs);
    font-size: 12px;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-weight: 600;
    color: var(--text-1);
    cursor: pointer;
    text-align: center;
    transition: all 0.1s;
}
.keybind-key:hover {
    background: rgba(255,255,255,0.06);
}
.keybind-key.recording {
    border-color: var(--section-accent, var(--accent));
    color: var(--section-accent, var(--accent));
}

/* ─── Info Tooltip ─── */
.has-tip::after {
    content: attr(data-tip);
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%) scale(0.95);
    background: rgba(20,20,25,0.95);
    border: 1px solid rgba(255,255,255,0.05);
    color: var(--text-2);
    padding: 6px 12px;
    border-radius: var(--radius-xs);
    font-size: 11px;
    white-space: nowrap;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.2s, transform 0.2s;
    z-index: 100;
    backdrop-filter: blur(12px);
}
.has-tip:hover::after {
    opacity: 1;
    transform: translateX(-50%) scale(1);
}

/* ═══════════════════════════════════════════════════════════════
   LIST ITEMS (Templates / Folders)
   ═══════════════════════════════════════════════════════════════ */
.list-item {
    padding: 16px 20px;
    background: rgba(255,255,255,0.015);
    border: 1px solid rgba(255,255,255,0.03);
    border-radius: var(--radius-sm);
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    transition: all 0.15s;
}
.list-item:hover {
    background: rgba(255,255,255,0.03);
    border-color: rgba(255,255,255,0.06);
}
.list-item .item-name { font-weight: 500; font-size: 14px; }
.list-item .item-meta {
    font-size: 12px;
    color: var(--text-3);
    font-weight: 400;
}
.list-item .item-arrow {
    color: var(--text-3);
    font-size: 16px;
    transition: transform 0.15s, color 0.15s;
}
.list-item:hover .item-arrow { transform: translateX(4px); color: var(--section-accent, var(--accent)); }

/* ─── Editor Layout ─── */
.editor-2col {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 32px;
}
.editor-section {
    display: flex;
    flex-direction: column;
    gap: 24px;
}
.editor-section h4 {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 2px;
    color: var(--text-3);
    margin-bottom: 8px;
    text-transform: uppercase;
}
.back-btn {
    background: transparent;
    border: none;
    color: var(--text-2);
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
    display: flex;
    align-items: center;
    gap: 6px;
}
.back-btn:hover { color: var(--text-1); }

/* ═══════════════════════════════════════════════════════════════
   HALO LAYER GRID
   ═══════════════════════════════════════════════════════════════ */
.layer-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}
.layer-card {
    background: rgba(255,255,255,0.015);
    border: 1px solid rgba(255,255,255,0.03);
    border-radius: var(--radius-sm);
    padding: 16px;
    transition: border-color 0.2s;
}
.layer-card:hover { border-color: rgba(255,255,255,0.06); }
.layer-card h5 {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    color: var(--text-3);
    margin-bottom: 12px;
    text-transform: uppercase;
}
.layer-tools {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    min-height: 24px;
}
.tool-chip {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06);
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-1);
    display: flex;
    align-items: center;
    gap: 6px;
}
.tool-chip .rm { color: var(--text-3); cursor: pointer; font-weight: bold; transition: color 0.15s; }
.tool-chip .rm:hover { color: var(--red); }
.tool-chip.bank {
    cursor: grab;
    transition: all 0.15s;
    background: transparent;
}
.tool-chip.bank:hover {
    background: rgba(255,255,255,0.06);
}
.empty-layer { color: var(--text-3); font-size: 12px; font-style: italic; }

/* ═══════════════════════════════════════════════════════════════
   HUB MODULE GRID (3×3)
   ═══════════════════════════════════════════════════════════════ */
.hub-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}
.hub-slot {
    border-radius: var(--radius-sm);
    padding: 24px 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    min-height: 120px;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
}
.hub-slot.filled {
    background: rgba(255,255,255,0.015);
    border: 1px solid rgba(255,255,255,0.03);
}
.hub-slot.filled:hover { border-color: rgba(255,255,255,0.06); }
.hub-slot.empty {
    background: transparent;
    border: 1px dashed rgba(255,255,255,0.1);
}
.hub-slot.empty:hover { border-color: rgba(255,255,255,0.2); }
.hub-slot .mod-name { font-weight: 500; font-size: 14px; }
.hub-slot .slot-n { font-size: 11px; color: var(--text-3); margin-top: 8px; }
.hub-slot .del-btn {
    position: absolute; top: 8px; right: 8px;
    width: 20px; height: 20px;
    border-radius: 50%;
    background: transparent;
    color: var(--text-3);
    font-size: 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
    border: none;
}
.hub-slot.filled:hover .del-btn { color: var(--text-2); }
.hub-slot .del-btn:hover { background: rgba(255,85,85,0.1); color: var(--red); }

/* ═══════════════════════════════════════════════════════════════
   UTILITIES
   ═══════════════════════════════════════════════════════════════ */
.flex-col { display: flex; flex-direction: column; }
.gap-8 { gap: 8px; }
.gap-16 { gap: 16px; }
.mt-16 { margin-top: 16px; }
.mt-24 { margin-top: 24px; }
.mt-32 { margin-top: 32px; }
"""

# We replace the entire <style> block
html = re.sub(r'<style>.*?</style>', f'<style>\n{css_new}\n</style>', html, flags=re.DOTALL)

# 2. Update the HTML structure of controls (from cards to clean lists/rows)

# GENERAL TAB
html_general = """
            <div class="tab-page active" id="tab-general" data-accent="var(--accent-general)" style="--section-accent: var(--accent-general);">

                <div class="section-header">
                    <span class="sh-text">Appearance</span>
                </div>
                
                <div class="control-group">
                    <div class="control-item">
                        <div class="control-row"><span class="control-label has-tip" data-tip="Size of the alignment grid on your desktop">Grid Size</span><span class="range-val" id="v-gs">110</span></div>
                        <input type="range" min="40" max="200" value="110" data-val="v-gs">
                    </div>
                    
                    <div class="control-item">
                        <div class="control-row"><span class="control-label has-tip" data-tip="Gap from the screen edges">Edge Padding</span><span class="range-val" id="v-ep">15</span></div>
                        <input type="range" min="0" max="100" value="15" data-val="v-ep">
                    </div>
                    
                    <div class="control-item">
                        <div class="control-row"><span class="control-label has-tip" data-tip="Opacity of the grid overlay">Grid Visibility</span><span class="range-val" id="v-gv">100</span></div>
                        <input type="range" min="10" max="100" value="100" data-val="v-gv">
                    </div>

                    <div class="control-item mt-16">
                        <div class="control-row">
                            <span class="control-label">Dashboard Theme</span>
                            <select><option selected>Default (Glass)</option><option>Classic Dark</option><option>Classic Light</option><option>Untinted Glass</option></select>
                        </div>
                    </div>
                </div>

                <div class="control-group mt-32">
                    <div class="toggle-row">
                        <span class="control-label has-tip" data-tip="Show the alignment grid when dragging folders">Show Grid on Drag</span>
                        <label class="toggle"><input type="checkbox" checked><span class="track"></span></label>
                    </div>
                    <div class="toggle-row">
                        <span class="control-label has-tip" data-tip="Animate the grid color with a hue cycle">Animated Grid Color</span>
                        <label class="toggle"><input type="checkbox" checked><span class="track"></span></label>
                    </div>
                    <div class="toggle-row">
                        <span class="control-label has-tip" data-tip="Staggered ripple animation when grid appears">Wave Entrance</span>
                        <label class="toggle"><input type="checkbox" checked><span class="track"></span></label>
                    </div>
                    <div class="toggle-row">
                        <span class="control-label has-tip" data-tip="Fade grid color during wave animation">Wave Color Fade</span>
                        <label class="toggle"><input type="checkbox" checked><span class="track"></span></label>
                    </div>
                </div>

                <div class="section-header">
                    <span class="sh-text">Keybinds</span>
                </div>
                <div class="control-group">
                    <div class="control-row">
                        <span class="control-label">Launch App</span>
                        <button class="keybind-key">Left Click</button>
                    </div>
                    <div class="control-row">
                        <span class="control-label">Open Folder</span>
                        <button class="keybind-key">Middle Click</button>
                    </div>
                    <div class="control-row">
                        <span class="control-label">Show Menu</span>
                        <button class="keybind-key">Right Click</button>
                    </div>
                </div>

                <div class="section-header" style="--section-accent: var(--accent-display);">
                    <span class="sh-text">Display Effects</span>
                </div>
                <div class="control-group" style="--section-accent: var(--accent-display);">
                    <div class="control-row">
                        <span class="control-label">Filter Preset</span>
                        <select><option>Reading</option><option selected>Sunset</option><option>Movie</option><option>Eye Saver</option></select>
                    </div>
                    <div class="control-item mt-16">
                        <div class="control-row"><span class="control-label">Warmth Intensity</span><span class="range-val" id="v-wi">50</span></div>
                        <input type="range" min="0" max="100" value="50" data-val="v-wi">
                    </div>
                </div>
            </div>"""

# Substitute the old tab-general block
html = re.sub(r'<div class="tab-page active" id="tab-general" data-accent="var\(--accent-general\)">.*?</div>\s+<!-- ════════════════════════════════════════════════\s+TEMPLATES', html_general + '\n\n            <!-- ════════════════════════════════════════════════\n                 TEMPLATES', html, flags=re.DOTALL)

# TEMPLATES TAB (Simplifying editors)
html_tpl_editor = """
                <div id="tpl-editor" style="display:none; --section-accent: var(--accent-templates);">
                    <div style="display:flex;align-items:center;margin-bottom:32px;">
                        <button class="back-btn" onclick="hideEditor('tpl')"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg> Back</button>
                        <h3 style="font-size:16px;font-weight:500;margin-left:16px;" id="tpl-title">Editing GRID: Default</h3>
                    </div>
                    <div class="editor-2col">
                        <div class="editor-section">
                            <h4>Behavior</h4>
                            <div class="control-group">
                                <div class="toggle-row"><span class="control-label">Show Folder Name</span><label class="toggle"><input type="checkbox" checked><span class="track"></span></label></div>
                                <div class="toggle-row"><span class="control-label">Snap to Grid</span><label class="toggle"><input type="checkbox"><span class="track"></span></label></div>
                                <div class="toggle-row"><span class="control-label">Show Cover Image</span><label class="toggle"><input type="checkbox"><span class="track"></span></label></div>
                            </div>
                            <div class="control-group">
                                <div class="control-row"><span class="control-label">Highlight Shape</span><select><option>Circle</option><option>Square</option><option selected>Rounded Square</option></select></div>
                                <div class="control-row mt-16"><span class="control-label">Hover Speed</span><select><option>Snappy</option><option selected>Fluid</option><option>Relaxed</option></select></div>
                                <div class="control-row mt-16"><span class="control-label">Morph Speed</span><select><option>Snappy</option><option selected>Fluid</option><option>Relaxed</option></select></div>
                            </div>
                        </div>
                        <div class="editor-section">
                            <h4>Styling</h4>
                            <div class="control-group">
                                <div class="control-row"><span class="control-label">Size Preset</span><select><option>Small</option><option selected>Medium</option><option>Large</option><option>Custom</option></select></div>
                                <div class="control-item mt-16">
                                    <div class="control-row"><span class="control-label">Opacity</span><span class="range-val">80</span></div>
                                    <input type="range" min="0" max="255" value="80">
                                </div>
                                <div class="control-item mt-16">
                                    <div class="control-row"><span class="control-label">Radius</span><span class="range-val">20</span></div>
                                    <input type="range" min="0" max="50" value="20">
                                </div>
                                <div class="control-item mt-16">
                                    <div class="control-row"><span class="control-label">Glow Intensity</span><span class="range-val">20</span></div>
                                    <input type="range" min="0" max="100" value="20">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>"""
html = re.sub(r'<div id="tpl-editor".*?</div>\s*</div>\s*<!-- ════════════════════════════════════════════════\s+FOLDERS', html_tpl_editor + '\n            </div>\n\n            <!-- ════════════════════════════════════════════════\n                 FOLDERS', html, flags=re.DOTALL)

# FOLDERS TAB (Simplifying editors)
html_fld_editor = """
                <div id="fld-editor" style="display:none; --section-accent: var(--accent-folders);">
                    <div style="display:flex;align-items:center;margin-bottom:32px;">
                        <button class="back-btn" onclick="hideEditor('fld')"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg> Back</button>
                        <h3 style="font-size:16px;font-weight:500;margin-left:16px;" id="fld-title">Editing: Games</h3>
                    </div>
                    <div class="editor-2col">
                        <div class="editor-section">
                            <h4>General</h4>
                            <div class="control-group">
                                <div class="toggle-row"><span class="control-label">Show Folder Name</span><label class="toggle"><input type="checkbox" checked><span class="track"></span></label></div>
                                <div class="toggle-row"><span class="control-label">Snap to Grid</span><label class="toggle"><input type="checkbox"><span class="track"></span></label></div>
                                <div class="toggle-row"><span class="control-label">Show Cover Image</span><label class="toggle"><input type="checkbox"><span class="track"></span></label></div>
                                <div class="control-row mt-16"><span class="control-label">Template Type</span><span style="color:var(--text-3);font-size:13px;font-weight:500;">GRID</span></div>
                            </div>
                        </div>
                        <div class="editor-section">
                            <h4>Styling</h4>
                            <div class="control-group">
                                <div class="control-row"><span class="control-label">Base Template</span><select><option selected>Default</option><option>Compact</option></select></div>
                                <div class="toggle-row mt-16"><span class="control-label">Use Custom Styling</span><label class="toggle" id="custom-toggle"><input type="checkbox"><span class="track"></span></label></div>
                            </div>
                            <div id="custom-panel" style="opacity:0.35;pointer-events:none;transition:opacity 0.25s;">
                                <div class="control-group">
                                    <div class="control-row"><span class="control-label">Size Preset</span><select><option>Small</option><option selected>Medium</option><option>Large</option><option>Custom</option></select></div>
                                    <div class="control-item mt-16">
                                        <div class="control-row"><span class="control-label">Opacity</span><span class="range-val">80</span></div>
                                        <input type="range" min="0" max="255" value="80">
                                    </div>
                                    <div class="control-item mt-16">
                                        <div class="control-row"><span class="control-label">Radius</span><span class="range-val">20</span></div>
                                        <input type="range" min="0" max="50" value="20">
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>"""
html = re.sub(r'<div id="fld-editor".*?</div>\s*</div>\s*<!-- ════════════════════════════════════════════════\s+HALO', html_fld_editor + '\n            </div>\n\n            <!-- ════════════════════════════════════════════════\n                 HALO', html, flags=re.DOTALL)

# HALO TAB
html_halo = """
            <div class="tab-page" id="tab-halo" data-accent="var(--accent-halo)" style="--section-accent: var(--accent-halo);">

                <div class="section-header">
                    <span class="sh-text">Activation & Behavior</span>
                </div>
                <div class="control-group">
                    <div class="control-row"><span class="control-label">Activation Key</span><button class="keybind-key" style="color:var(--accent-halo);border-color:var(--accent-halo);">~ / `</button></div>
                    <div class="control-row"><span class="control-label">Activation Mode</span><select><option selected>Hold</option><option>Toggle</option></select></div>
                    <div class="control-row"><span class="control-label">Visual Theme</span><select><option selected>Dark</option><option>Light</option><option>Glass</option></select></div>
                    <div class="control-row"><span class="control-label">HUD Arc Gap</span><select><option>0</option><option>15</option><option>30</option><option>45</option><option>60</option><option selected>75</option><option>90</option></select></div>
                </div>

                <div class="section-header">
                    <span class="sh-text">Dimensions & Feel</span>
                </div>
                <div class="control-group">
                    <div class="control-item">
                        <div class="control-row"><span class="control-label has-tip" data-tip="Overall diameter of the radial menu">Menu Diameter</span><span class="range-val" id="v-md">300</span></div>
                        <input type="range" min="100" max="800" value="300" data-val="v-md">
                    </div>
                    <div class="control-item">
                        <div class="control-row"><span class="control-label has-tip" data-tip="Ratio of the inner dead zone to outer ring">Hub Ratio (%)</span><span class="range-val" id="v-hr">50</span></div>
                        <input type="range" min="0" max="95" value="50" data-val="v-hr">
                    </div>
                    <div class="control-item">
                        <div class="control-row"><span class="control-label has-tip" data-tip="Background opacity of the halo overlay">BG Opacity</span><span class="range-val" id="v-bo">185</span></div>
                        <input type="range" min="50" max="255" value="185" data-val="v-bo">
                    </div>
                    <div class="control-item">
                        <div class="control-row"><span class="control-label has-tip" data-tip="How quickly the menu responds to mouse wheel">Scroll Sensitivity</span><span class="range-val" id="v-ss">50</span></div>
                        <input type="range" min="1" max="100" value="50" data-val="v-ss">
                    </div>
                    <div class="control-item">
                        <div class="control-row"><span class="control-label has-tip" data-tip="Multiplier for mouse movement in the halo">Mouse Sensitivity</span><span class="range-val" id="v-ms">100</span></div>
                        <input type="range" min="10" max="200" value="100" data-val="v-ms">
                    </div>
                </div>

                <div class="section-header">
                    <span class="sh-text">Tool Bank</span>
                </div>
                <div class="control-group" style="margin-bottom: 24px;">
                    <div style="display:flex;flex-wrap:wrap;gap:8px;">
                        <span class="tool-chip bank">🌐 Browser</span>
                        <span class="tool-chip bank">📁 Files</span>
                        <span class="tool-chip bank">📷 Snip</span>
                        <span class="tool-chip bank">🌙 Night Light</span>
                        <span class="tool-chip bank">🔇 Mute</span>
                        <span class="tool-chip bank">🗑️ Trash</span>
                        <span class="tool-chip bank">⚙️ Pandora</span>
                        <span class="tool-chip bank">🔍 Search</span>
                        <span class="tool-chip bank">📊 Tasks</span>
                        <span class="tool-chip bank">📝 Notes</span>
                        <span class="tool-chip bank">⏻ Power</span>
                        <span class="tool-chip bank">▦ Grid</span>
                    </div>
                </div>

                <div class="section-header">
                    <span class="sh-text">Layer Assignments (9 Layers)</span>
                </div>
                <div class="layer-grid">
                    <div class="layer-card"><h5>Layer 1</h5><div class="layer-tools"><span class="tool-chip">🌐 Browser <span class="rm">×</span></span><span class="tool-chip">📁 Files <span class="rm">×</span></span></div></div>
                    <div class="layer-card"><h5>Layer 2</h5><div class="layer-tools"><span class="tool-chip">📷 Snip <span class="rm">×</span></span></div></div>
                    <div class="layer-card"><h5>Layer 3</h5><div class="layer-tools"><span class="tool-chip">🌙 Night <span class="rm">×</span></span><span class="tool-chip">🔇 Mute <span class="rm">×</span></span></div></div>
                    <div class="layer-card"><h5>Layer 4</h5><div class="layer-tools"><span class="empty-layer">Empty</span></div></div>
                    <div class="layer-card"><h5>Layer 5</h5><div class="layer-tools"><span class="tool-chip">⚙️ Pandora <span class="rm">×</span></span></div></div>
                    <div class="layer-card"><h5>Layer 6</h5><div class="layer-tools"><span class="empty-layer">Empty</span></div></div>
                    <div class="layer-card"><h5>Layer 7</h5><div class="layer-tools"><span class="tool-chip">🗑️ Trash <span class="rm">×</span></span></div></div>
                    <div class="layer-card"><h5>Layer 8</h5><div class="layer-tools"><span class="empty-layer">Empty</span></div></div>
                    <div class="layer-card"><h5>Layer 9</h5><div class="layer-tools"><span class="tool-chip">⏻ Power <span class="rm">×</span></span></div></div>
                </div>
            </div>"""
html = re.sub(r'<div class="tab-page" id="tab-halo".*?</div>\s+<!-- ════════════════════════════════════════════════\s+HUB HUD', html_halo + '\n\n            <!-- ════════════════════════════════════════════════\n                 HUB HUD', html, flags=re.DOTALL)

# HUB TAB
html_hub = """
            <div class="tab-page" id="tab-hub" data-accent="var(--accent-hub)" style="--section-accent: var(--accent-hub);">
                <div class="section-header">
                    <span class="sh-text">Hub HUD Globals</span>
                </div>
                <div class="control-group">
                    <div class="control-row"><span class="control-label">Switching Mode</span><select><option selected>Middle Click</option><option>Region Scroll</option><option>Custom Buttons</option></select></div>
                    <div class="control-row"><span class="control-label">Scroll Region</span><select><option selected>Upper Screen</option><option>Lower Screen</option><option>Left Edge</option><option>Right Edge</option></select></div>
                    <div class="control-row"><span class="control-label">Low Res Art Style</span><select><option selected>Gaussian Blur</option><option>Pixelate</option><option>Monochrome</option></select></div>
                    <div class="control-item mt-16">
                        <div class="control-row"><span class="control-label">Blur Strength</span><span class="range-val" id="v-bs">25</span></div>
                        <input type="range" min="0" max="100" value="25" data-val="v-bs">
                    </div>
                </div>

                <div class="section-header">
                    <span class="sh-text">Active Widget Modules (3×3 Grid)</span>
                </div>
                <div class="hub-grid">
                    <div class="hub-slot filled"><span class="mod-name" style="color:var(--text-1);">Pandora Logo</span><span class="slot-n">Slot 1</span><button class="del-btn">×</button></div>
                    <div class="hub-slot filled"><span class="mod-name" style="color:var(--purple);">Media Player</span><span class="slot-n">Slot 2</span><button class="del-btn">×</button></div>
                    <div class="hub-slot filled"><span class="mod-name" style="color:var(--cyan);">Clock</span><span class="slot-n">Slot 3</span><button class="del-btn">×</button></div>
                    <div class="hub-slot filled"><span class="mod-name" style="color:var(--pink);">Stopwatch</span><span class="slot-n">Slot 4</span><button class="del-btn">×</button></div>
                    <div class="hub-slot filled"><span class="mod-name" style="color:var(--orange);">Timer</span><span class="slot-n">Slot 5</span><button class="del-btn">×</button></div>
                    <div class="hub-slot filled"><span class="mod-name" style="color:var(--yellow);">Weather</span><span class="slot-n">Slot 6</span><button class="del-btn">×</button></div>
                    <div class="hub-slot filled"><span class="mod-name" style="color:var(--green);">Launcher</span><span class="slot-n">Slot 7</span><button class="del-btn">×</button></div>
                    <div class="hub-slot empty"><span style="font-size:24px;color:var(--text-3);font-weight:300;">+</span><span class="slot-n">Slot 8</span></div>
                    <div class="hub-slot empty"><span style="font-size:24px;color:var(--text-3);font-weight:300;">+</span><span class="slot-n">Slot 9</span></div>
                </div>
            </div>"""
html = re.sub(r'<div class="tab-page" id="tab-hub".*?</div>\s*</main>', html_hub + '\n\n        </main>', html, flags=re.DOTALL)

# Custom Styling Toggle JS script
js_custom = """
/* ═══ Custom Styling Toggle ═══ */
const customToggle = document.querySelector('#custom-toggle input');
if (customToggle) {
    customToggle.addEventListener('change', e => {
        const panel = document.getElementById('custom-panel');
        panel.style.opacity = e.target.checked ? '1' : '0.35';
        panel.style.pointerEvents = e.target.checked ? 'auto' : 'none';
    });
}
"""
html = re.sub(r'// Handled inline via onclick for prototype', js_custom, html)

# Clean up stray section header dots in templates/folders tab lists
html = html.replace('<span class="sh-dot"></span>', '')


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(html)
