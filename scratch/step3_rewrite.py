import os

DIR = 'electron_dashboard'

# --- ui_dashboard_hub.js ---
hub = """const { getVkName, bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue } = require('./ui_dashboard_common.js');

class HubTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
        window.getAppConfig = getConfig;
        window.sendAppUpdate = sendUpdate;
    }

    init() {
        bindInput('#hub-switching-mode select', 'hub_config.switching_mode', false, this.getConfig, this.sendUpdate);
        bindInput('#hub-scroll-region select', 'hub_config.scroll_region', false, this.getConfig, this.sendUpdate);
        bindInput('#hub-art-style select', 'hub_config.low_res_art_style', false, this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-hub-blur-strength"]', 'hub_config.low_res_blur_strength', this.getConfig, this.sendUpdate);
    }

    updateUI(cfg) {
        const hub = cfg.hub_config || {};
        
        setInputValue('#hub-switching-mode select', hub.switching_mode || 'middle_click');
        setInputValue('#hub-scroll-region select', hub.scroll_region || 'upper');
        setInputValue('#hub-art-style select', hub.low_res_art_style || 'Gaussian Blur');
        setSliderValue('[data-val="v-hub-blur-strength"]', hub.low_res_blur_strength || 25);

        if (window.updateHubLayersFromConfig) {
            window.updateHubLayersFromConfig(hub.layers || []);
        }
    }
}
module.exports = { HubTab };
"""
with open(os.path.join(DIR, 'ui_dashboard_hub.js'), 'w', encoding='utf-8') as f:
    f.write(hub)

# --- ui_dashboard_templates.js ---
templates = """const { getVkName, bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue } = require('./ui_dashboard_common.js');

class TemplatesTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
    }

    init() {
        // Prototype didn't have many active inputs for template values linked to config beyond mock ones,
        // but we will bind the standard ones here if they are in the DOM.
        // We'll leave it as a stub since template editing in prototype was mostly mock UI.
    }

    updateUI(cfg) {
        // Stub
    }
}
module.exports = { TemplatesTab };
"""
with open(os.path.join(DIR, 'ui_dashboard_templates.js'), 'w', encoding='utf-8') as f:
    f.write(templates)

# --- ui_dashboard_folders.js ---
folders = """const { getVkName, bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue } = require('./ui_dashboard_common.js');

class FoldersTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
    }

    init() {
        // Stub for folders
    }

    updateUI(cfg) {
        // Stub for folders
    }
}
module.exports = { FoldersTab };
"""
with open(os.path.join(DIR, 'ui_dashboard_folders.js'), 'w', encoding='utf-8') as f:
    f.write(folders)

print("Done step 3.")
