import os
import re

DIR = 'electron_dashboard'

with open(os.path.join(DIR, 'temp_inline.js'), 'r', encoding='utf-8') as f:
    js = f.read()

# Remove IPC renderer require since we will do it at the top of common.js
js = js.replace("const { ipcRenderer } = require('electron');", "")

# 1. Halo sync hook
halo_hook = """
function refreshHalo() {
    updateLayerDropdown();
    renderHaloRadial();
    
    // Sync to Python
    if (window.getAppConfig && window.sendAppUpdate) {
        const cfg = window.getAppConfig();
        if (!cfg.halo) cfg.halo = {};
        
        // Convert haloLayers to python expected format (array of {name, tools: [{id, icon, label}]})
        // But only if we are the ones who originated the change (avoid infinite loop)
        if (!window.isUpdatingFromPython) {
            cfg.halo.menus = haloLayers.map((l, i) => {
                return {
                    name: `L${i+1}`,
                    tools: l.slices.filter(s => s.name).map(s => {
                        // Find original ID from HALO_TOOLS
                        const toolDef = HALO_TOOLS.find(t => t.name === s.name);
                        return { id: toolDef ? toolDef.name.toLowerCase() : s.name.toLowerCase(), icon: s.icon, label: s.name };
                    })
                };
            });
            window.sendAppUpdate();
        }
    }
}

window.updateHaloLayersFromConfig = function(menus) {
    window.isUpdatingFromPython = true;
    haloLayers = Array.from({ length: 9 }, (_, i) => {
        if (menus[i] && menus[i].tools && menus[i].tools.length > 0) {
            return { slices: menus[i].tools.map(t => ({ icon: t.icon, name: t.label })) };
        }
        return { slices: [{ icon: '', name: '' }] };
    });
    updateLayerDropdown();
    renderHaloRadial();
    window.isUpdatingFromPython = false;
};
"""
js = js.replace("function refreshHalo() {\n    updateLayerDropdown();\n    renderHaloRadial();\n}", halo_hook)

# 2. Hub sync hook
hub_hook = """
function renderHubGrid() {
    const container = document.getElementById('hub-grid-container');
    if (!container) return;
    container.innerHTML = '';

    hubSlots.forEach((slot, i) => {
        const slotEl = document.createElement('div');
        const isSelected = i === selectedHubSlotIndex;
        
        if (slot) {
            const mod = HUB_MODULES[slot.type];
            slotEl.className = `hub-slot filled${isSelected ? ' selected' : ''}`;
            slotEl.style.setProperty('--slot-glow-color', mod.color + '30'); 
            slotEl.style.borderColor = isSelected ? mod.color : 'rgba(255,255,255,0.03)';
            
            slotEl.innerHTML = `
                <span class="mod-icon" style="font-size:24px; margin-bottom:8px; display:block;">${mod.icon}</span>
                <span class="mod-name" style="color:${mod.color};">${mod.name}</span>
                <span class="slot-n">Slot ${i + 1}</span>
                <button class="del-btn" title="Remove Module">×</button>
            `;
            
            slotEl.querySelector('.del-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                deleteHubSlot(i);
            });
        } else {
            slotEl.className = `hub-slot empty${isSelected ? ' selected' : ''}`;
            slotEl.style.borderColor = isSelected ? 'var(--accent-hub)' : 'rgba(255,255,255,0.1)';
            slotEl.innerHTML = `
                <span style="font-size:24px;color:var(--text-3);font-weight:300;">+</span>
                <span class="slot-n">Slot ${i + 1}</span>
            `;
        }

        slotEl.addEventListener('click', () => selectHubSlot(i));
        container.appendChild(slotEl);
    });
    
    // Sync Hub Slots to Python
    if (window.getAppConfig && window.sendAppUpdate && !window.isUpdatingHubFromPython) {
        const cfg = window.getAppConfig();
        if (!cfg.hub_config) cfg.hub_config = {};
        
        cfg.hub_config.layers = hubSlots.map(s => {
            if (!s) return null;
            const mod = HUB_MODULES[s.type];
            return { type: s.type, name: mod.name, icon: mod.icon, settings: s.settings };
        });
        window.sendAppUpdate();
    }
}

window.updateHubLayersFromConfig = function(layers) {
    window.isUpdatingHubFromPython = true;
    for(let i=0; i<9; i++) {
        if (layers[i]) {
            hubSlots[i] = { type: layers[i].type, settings: layers[i].settings || {} };
        } else {
            hubSlots[i] = null;
        }
    }
    const container = document.getElementById('hub-grid-container');
    if(container) {
        // Redraw without triggering a sendUpdate
        const bk = window.sendAppUpdate;
        window.sendAppUpdate = null;
        renderHubGrid();
        window.sendAppUpdate = bk;
    }
    window.isUpdatingHubFromPython = false;
};
"""
js = js.replace("function renderHubGrid() {", hub_hook + "\nfunction renderHubGridOld() {")

with open(os.path.join(DIR, 'temp_inline.js'), 'w', encoding='utf-8') as f:
    f.write(js)
print("Hooks injected into temp_inline.js")
