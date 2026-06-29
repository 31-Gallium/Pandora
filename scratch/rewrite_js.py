import os
import re

DIR = 'electron_dashboard'

# --- renderer.js ---
renderer = """const { ipcRenderer } = require('electron');
const WebSocket = require('ws');
const { initGlobalUI } = require('./ui_dashboard_common.js');
const { GeneralTab } = require('./ui_dashboard_general.js');
const { HaloTab } = require('./ui_dashboard_halo.js');
const { HubTab } = require('./ui_dashboard_hub.js');
const { FoldersTab } = require('./ui_dashboard_folders.js');
const { TemplatesTab } = require('./ui_dashboard_templates.js');

document.getElementById('close-btn').addEventListener('click', () => {
    ipcRenderer.send('close-window');
});

const ws = new WebSocket('ws://localhost:8765');
let currentConfig = { general_settings: {}, halo: {}, display_effects: {}, hub_config: {}, folders: [], templates: { grid: {}, flower: {} } };

function getConfig() {
    return currentConfig;
}

function sendConfigUpdate() {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'update_config',
            data: currentConfig
        }));
    }
}

// Instantiate Tab Modules
const generalTab = new GeneralTab(getConfig, sendConfigUpdate);
const haloTab = new HaloTab(getConfig, sendConfigUpdate);
const hubTab = new HubTab(getConfig, sendConfigUpdate);
const foldersTab = new FoldersTab(getConfig, sendConfigUpdate);
const templatesTab = new TemplatesTab(getConfig, sendConfigUpdate);

const tabs = [generalTab, haloTab, hubTab, foldersTab, templatesTab];

// Initialize DOM Bindings for all tabs
tabs.forEach(tab => {
    if (tab.init) tab.init();
});

initGlobalUI(); // Start the UI interactivity

ws.on('open', () => {
    console.log('Connected to Python Core');
});

ws.on('message', (message) => {
    const parsed = JSON.parse(message);
    if (parsed.type === 'init_config' || parsed.type === 'update_config') {
        currentConfig = parsed.data;
        tabs.forEach(tab => {
            if (tab.updateUI) tab.updateUI(currentConfig);
        });
    } else if (parsed.type === 'show_folder') {
        // Python requested us to switch to Folders tab and open a specific folder
        const folderNav = document.querySelector('.nav-item[data-tab="folders"]');
        if(folderNav) folderNav.click();
        if (parsed.folder_id) {
            foldersTab.editingFolderId = parsed.folder_id;
            const folder = currentConfig.folders.find(f => f.id === parsed.folder_id);
            if (folder) foldersTab.renderEditor(folder);
        }
    }
});

ws.on('error', (err) => {
    console.error('WebSocket error:', err.message);
});
"""
with open(os.path.join(DIR, 'renderer.js'), 'w', encoding='utf-8') as f:
    f.write(renderer)

# --- ui_dashboard_common.js ---
# We will inject the UI interactivity from temp_inline.js here
with open(os.path.join(DIR, 'temp_inline.js'), 'r', encoding='utf-8') as f:
    temp_inline = f.read()

# Remove the inline require of ipcRenderer since we are in common.js
temp_inline = temp_inline.replace("const { ipcRenderer } = require('electron');", "")

common = f"""const {{ ipcRenderer }} = require('electron');
const vkMap = {{
    1: 'Left Click', 2: 'Right Click', 4: 'Middle Click',
    192: '~ / `', 9: 'Tab', 16: 'Shift', 17: 'Ctrl', 18: 'Alt',
    20: 'Caps Lock', 27: 'Esc', 32: 'Space', 13: 'Enter', 8: 'Backspace',
    37: '← Arrow', 38: '↑ Arrow', 39: '→ Arrow', 40: '↓ Arrow',
    46: 'Delete', 45: 'Insert', 36: 'Home', 35: 'End',
    33: 'Page Up', 34: 'Page Down'
}};

function getVkName(code) {{
    if (vkMap[code]) return vkMap[code];
    if (code >= 65 && code <= 90) return String.fromCharCode(code);
    if (code >= 48 && code <= 57) return String.fromCharCode(code);
    if (code >= 112 && code <= 123) return 'F' + (code - 111);
    if (code >= 96 && code <= 105) return 'Num ' + (code - 96);
    return `Code: ${{code}}`;
}}

function bindInput(selector, configPath, isNumber, getConfig, updateCallback) {{
    const el = document.querySelector(selector);
    if (!el) return;
    const parts = configPath.split('.');
    
    el.addEventListener('change', (e) => {{
        const cfg = getConfig();
        let target = cfg;
        for (let i = 0; i < parts.length - 1; i++) {{
            if (!target[parts[i]]) target[parts[i]] = {{}};
            target = target[parts[i]];
        }}
        const key = parts[parts.length - 1];
        
        if (el.type === 'checkbox') {{
            target[key] = e.target.checked;
        }} else {{
            target[key] = isNumber ? parseInt(e.target.value) : e.target.value;
        }}
        updateCallback();
    }});
}}

function bindSlider(selector, configPath, getConfig, updateCallback) {{
    const el = document.querySelector(selector);
    if (!el) return;
    const valId = el.getAttribute('data-val');
    const parts = configPath.split('.');
    
    el.addEventListener('input', (e) => {{
        if (valId) {{
            const valEl = document.getElementById(valId);
            if(valEl) valEl.innerText = e.target.value;
        }}
        const cfg = getConfig();
        let target = cfg;
        for (let i = 0; i < parts.length - 1; i++) {{
            if (!target[parts[i]]) target[parts[i]] = {{}};
            target = target[parts[i]];
        }}
        target[parts[parts.length - 1]] = parseInt(e.target.value);
        updateCallback();
    }});
}}

function setInputValue(selector, value) {{
    const el = document.querySelector(selector);
    if (el) el.value = value;
}}

function setCheckboxValue(selector, checked) {{
    const el = document.querySelector(selector);
    if (el) el.checked = checked;
}}

function setSliderValue(selector, value) {{
    const el = document.querySelector(selector);
    if (el) {{
        el.value = value;
        const min = parseFloat(el.min || 0);
        const max = parseFloat(el.max || 100);
        const pct = ((value - min) / (max - min)) * 100;
        el.style.setProperty('--fill', pct + '%');
        const valId = el.getAttribute('data-val');
        if (valId) {{
            const valEl = document.getElementById(valId);
            if(valEl) valEl.innerText = Math.round(value);
        }}
    }}
}}

// Global UI Initialization
function initGlobalUI() {{
    {temp_inline}
}}

module.exports = {{ vkMap, getVkName, bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue, initGlobalUI }};
"""
with open(os.path.join(DIR, 'ui_dashboard_common.js'), 'w', encoding='utf-8') as f:
    f.write(common)

# --- ui_dashboard_general.js ---
general = """const { getVkName, bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue } = require('./ui_dashboard_common.js');

class GeneralTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
        this.activeKeybindInput = null;
    }

    init() {
        bindSlider('[data-val="v-gs"]', 'general_settings.grid_size', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-ep"]', 'general_settings.edge_padding', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-gv"]', 'general_settings.grid_opacity', this.getConfig, this.sendUpdate);
        bindInput('#set-filter-preset', 'general_settings.dashboard_theme', false, this.getConfig, this.sendUpdate);
        bindInput('#set-show-grid-drag input', 'general_settings.show_grid_on_drag', false, this.getConfig, this.sendUpdate);
        bindInput('#set-anim-grid-color input', 'general_settings.grid_animated_color', false, this.getConfig, this.sendUpdate);
        bindInput('#set-wave-ent input', 'general_settings.grid_wave_entrance', false, this.getConfig, this.sendUpdate);
        bindInput('#set-wave-color input', 'general_settings.grid_wave_fade', false, this.getConfig, this.sendUpdate);

        bindInput('#set-filter-preset', 'display_effects.active_preset', false, this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-wi"]', 'display_effects.warmth_intensity', this.getConfig, this.sendUpdate);

        document.querySelectorAll('#set-kb-launch .keybind-key, #set-kb-folder .keybind-key, #set-kb-menu .keybind-key').forEach(input => {
            input.addEventListener('click', (e) => {
                if (this.activeKeybindInput) this.activeKeybindInput.classList.remove('recording');
                this.activeKeybindInput = e.target;
                this.activeKeybindInput.classList.add('recording');
                this.activeKeybindInput.textContent = 'Press key...';
            });
        });

        window.addEventListener('keydown', (e) => {
            if (!this.activeKeybindInput) return;
            if (!this.activeKeybindInput.closest('#tab-general')) return;
            e.preventDefault();
            
            const vkCode = e.keyCode;
            const id = this.activeKeybindInput.parentNode.id;
            
            this.activeKeybindInput.textContent = getVkName(vkCode);
            this.activeKeybindInput.classList.remove('recording');
            
            const cfg = this.getConfig();
            if (!cfg.general_settings.keybinds) cfg.general_settings.keybinds = {};
            if (id === 'set-kb-launch') cfg.general_settings.keybinds.launch_app = vkCode;
            if (id === 'set-kb-folder') cfg.general_settings.keybinds.open_folder = vkCode;
            if (id === 'set-kb-menu') cfg.general_settings.keybinds.show_menu = vkCode;
            
            this.sendUpdate();
            this.activeKeybindInput = null;
        });
    }

    updateUI(cfg) {
        const gen = cfg.general_settings || {};
        const disp = cfg.display_effects || {};
        
        setSliderValue('[data-val="v-gs"]', gen.grid_size || 110);
        setSliderValue('[data-val="v-ep"]', gen.edge_padding || 0);
        setSliderValue('[data-val="v-gv"]', gen.grid_opacity || 100);
        
        setInputValue('#set-filter-preset', gen.dashboard_theme || 'Untinted Glass');
        
        setCheckboxValue('#set-show-grid-drag input', gen.show_grid_on_drag !== false);
        setCheckboxValue('#set-anim-grid-color input', gen.grid_animated_color !== false);
        setCheckboxValue('#set-wave-ent input', gen.grid_wave_entrance !== false);
        setCheckboxValue('#set-wave-color input', gen.grid_wave_fade !== false);

        const kb = gen.keybinds || {};
        const kbLaunch = document.querySelector('#set-kb-launch .keybind-key');
        if (kbLaunch) kbLaunch.textContent = getVkName(kb.launch_app || 1);
        const kbFolder = document.querySelector('#set-kb-folder .keybind-key');
        if (kbFolder) kbFolder.textContent = getVkName(kb.open_folder || 4);
        const kbMenu = document.querySelector('#set-kb-menu .keybind-key');
        if (kbMenu) kbMenu.textContent = getVkName(kb.show_menu || 2);
        
        setSliderValue('[data-val="v-wi"]', disp.warmth_intensity || 50);
    }
}
module.exports = { GeneralTab };
"""
with open(os.path.join(DIR, 'ui_dashboard_general.js'), 'w', encoding='utf-8') as f:
    f.write(general)

# --- ui_dashboard_halo.js ---
# Only bind the generic inputs; the complex logic is in common.js globally and interacts directly via sendUpdate?
# Wait, we should probably pull the global Halo functions out into HaloTab instead, but since they are intertwined in temp_inline, we'll let them stay in initGlobalUI for now, and just bind the settings.
halo = """const { getVkName, bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue } = require('./ui_dashboard_common.js');

class HaloTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
        // The interactive radial renderer is bound globally in ui_dashboard_common.js via initGlobalUI,
        // but we need to inject our `getConfig` and `sendUpdate` into window so the global functions can use them!
        window.getAppConfig = getConfig;
        window.sendAppUpdate = sendUpdate;
    }

    init() {
        bindInput('#set-halo-act-mode', 'halo.hold_mode', false, this.getConfig, this.sendUpdate);
        bindInput('#set-halo-theme', 'halo.theme', false, this.getConfig, this.sendUpdate);
        bindInput('#set-halo-arc', 'halo.gap_size', true, this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-md"]', 'halo.max_bound', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-hr"]', 'halo.hub_ratio', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-bo"]', 'halo.opacity', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-ss"]', 'halo.scroll_sens', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-ms"]', 'halo.mouse_sens', this.getConfig, this.sendUpdate);

        const haloActivationBtn = document.querySelector('#set-halo-act-key .keybind-key');
        if (haloActivationBtn) {
            haloActivationBtn.addEventListener('click', (e) => {
                haloActivationBtn.classList.add('recording');
                haloActivationBtn.textContent = 'Press key...';
                
                const handler = (ev) => {
                    ev.preventDefault();
                    haloActivationBtn.textContent = getVkName(ev.keyCode);
                    haloActivationBtn.classList.remove('recording');
                    
                    const cfg = this.getConfig();
                    if (!cfg.halo) cfg.halo = {};
                    cfg.halo.activation_key = ev.keyCode;
                    this.sendUpdate();
                    
                    window.removeEventListener('keydown', handler);
                };
                window.addEventListener('keydown', handler);
            });
        }
    }

    updateUI(cfg) {
        const halo = cfg.halo || {};
        const kbBtn = document.querySelector('#set-halo-act-key .keybind-key');
        if (kbBtn && !kbBtn.classList.contains('recording')) {
            kbBtn.textContent = getVkName(halo.activation_key || 192);
        }
        
        setInputValue('#set-halo-act-mode', halo.hold_mode || 'Hold');
        setInputValue('#set-halo-theme', halo.theme || 'Dark');
        setInputValue('#set-halo-arc', halo.gap_size || 75);
        
        setSliderValue('[data-val="v-md"]', halo.max_bound || 300);
        setSliderValue('[data-val="v-hr"]', halo.hub_ratio || 50);
        setSliderValue('[data-val="v-bo"]', halo.opacity || 185);
        setSliderValue('[data-val="v-ss"]', halo.scroll_sens || 50);
        setSliderValue('[data-val="v-ms"]', halo.mouse_sens || 100);

        // Update global haloLayers
        if (window.updateHaloLayersFromConfig) {
            window.updateHaloLayersFromConfig(halo.menus || []);
        }
    }
}
module.exports = { HaloTab };
"""
with open(os.path.join(DIR, 'ui_dashboard_halo.js'), 'w', encoding='utf-8') as f:
    f.write(halo)

print("Done generating base files.")
