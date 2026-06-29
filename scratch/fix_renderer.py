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
    if (parsed.type === 'config_init' || parsed.type === 'update_config') {
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
with open('electron_dashboard/renderer.js', 'w', encoding='utf-8') as f:
    f.write(renderer)
print("renderer.js rewritten completely")
