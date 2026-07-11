const { ipcRenderer } = require('electron');
const WebSocket = require('ws');
const { initGlobalUI } = require('./ui_dashboard_common.js');
const { GeneralTab } = require('./ui_dashboard_general.js');
const { HaloTab } = require('./ui_dashboard_halo.js');
const { FoldersTab } = require('./ui_dashboard_folders.js');
const { SystemTab } = require('./ui_dashboard_system.js');
const { HubTab } = require('./ui_dashboard_hub.js');


document.getElementById('close-btn').addEventListener('click', () => {
    ipcRenderer.send('close-window');
});

document.getElementById('min-btn').addEventListener('click', () => {
    ipcRenderer.send('minimize-window');
});

window.addEventListener('blur', () => {
    document.body.classList.add('out-of-focus');
});

window.addEventListener('focus', () => {
    document.body.classList.remove('out-of-focus');
});

let ws;
let isConnecting = false;
let currentConfig = { general_settings: {}, halo: {}, display_effects: {}, hub_config: {}, folders: [] };

function getConfig() {
    return currentConfig;
}

function sendConfigUpdate() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'update_config',
            data: currentConfig
        }));
    }
}

window.sendCustomCommand = function(cmd) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(cmd));
    }
};

// Instantiate Tab Modules
const generalTab = new GeneralTab(getConfig, sendConfigUpdate);
const haloTab = new HaloTab(getConfig, sendConfigUpdate);
const foldersTab = new FoldersTab(getConfig, sendConfigUpdate);
const systemTab = new SystemTab(getConfig, sendConfigUpdate);
const hubTab = new HubTab(getConfig, sendConfigUpdate);

const tabs = [generalTab, haloTab, foldersTab, systemTab, hubTab];

// Initialize DOM Bindings for all tabs
tabs.forEach(tab => {
    if (tab.init) tab.init();
});

initGlobalUI(); // Start the UI interactivity

window.showEditor = function(type, subtype, id_or_name) {
    if (type === 'fld') foldersTab.showEditor(id_or_name);
};
window.hideEditor = function(type) {
    if (type === 'fld') foldersTab.hideEditor();
};

function connectWebSocket() {
    if (isConnecting) return;
    isConnecting = true;
    const wsPort = process.env.PANDORA_WS_PORT || 8765;
    ws = new WebSocket(`ws://localhost:${wsPort}`);

    ws.on('open', () => {
        console.log('Connected to Python Core');
        isConnecting = false;
    });

    ws.on('message', (message) => {
        const parsed = JSON.parse(message);
        if (parsed.type === 'init_config' || parsed.type === 'update_config') {
            currentConfig = parsed.data;
            tabs.forEach(tab => {
                if (tab.updateUI) tab.updateUI(currentConfig);
            });
            const loader = document.getElementById('dashboard-loader');
            if (loader && loader.style.display !== 'none') {
                // Add a minimum 800ms artificial delay to give the UI time to paint
                // and to prevent the loader from instantly flashing and disappearing
                setTimeout(() => {
                    loader.style.opacity = '0';
                    setTimeout(() => loader.style.display = 'none', 300);
                }, 800);
            }
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

    ws.on('close', () => {
        console.log('WebSocket connection closed. Reconnecting in 2s...');
        isConnecting = false;
        setTimeout(connectWebSocket, 2000);
    });
}

connectWebSocket();
