const { getVkName, bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue, syncCustomSelect } = require('./ui_dashboard_common.js');

class HaloTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
        // The interactive radial renderer is bound globally in ui_dashboard_common.js via initGlobalUI,
        // but we need to inject our `getConfig` and `sendUpdate` into window so the global functions can use them!
        window.getAppConfig = getConfig;
        window.sendAppUpdate = sendUpdate;
    }



    _bindWidget(selector, typeStr, settingKey, isNumber, isCheckbox=false, isSlider=false) {
        const el = document.querySelector(selector);
        if (!el) return;
        el.addEventListener(isSlider ? 'input' : 'change', (e) => {
            const cfg = this.getConfig();
            if (!cfg.hub_config) cfg.hub_config = {};
            if (!cfg.hub_config.layers) cfg.hub_config.layers = [];
            
            let val = isCheckbox ? e.target.checked : e.target.value;
            if (isNumber && !isCheckbox) val = parseFloat(val);
            
            // Ensure at least one layer exists
            let hasLayer = false;
            for (let l of cfg.hub_config.layers) {
                if (l && l.type === typeStr) {
                    if (!l.settings) l.settings = {};
                    l.settings[settingKey] = val;
                    hasLayer = true;
                }
            }
            if (!hasLayer) {
                const layer = { id: "layer_" + typeStr, type: typeStr, settings: {} };
                layer.settings[settingKey] = val;
                cfg.hub_config.layers.push(layer);
            }
            
            if (isSlider) {
                const display = document.querySelector(`[id="${el.getAttribute('data-val')}"]`);
                if (display) display.textContent = val;
            }
            
            this.sendUpdate();
        });
    }

    _getWidgetSettings(cfg, typeStr) {
        if (!cfg.hub_config) cfg.hub_config = {};
        if (!cfg.hub_config.layers) cfg.hub_config.layers = [];
        let layer = cfg.hub_config.layers.find(l => l && l.type === typeStr);
        if (!layer) {
            layer = { id: "layer_" + typeStr, type: typeStr, settings: {} };
            cfg.hub_config.layers.push(layer);
        }
        if (!layer.settings) layer.settings = {};
        return layer.settings;
    }

    init() {
        bindInput('#set-halo-act-mode select', 'halo.hold_mode', false, this.getConfig, this.sendUpdate);
        bindInput('#set-halo-theme select', 'halo.theme', false, this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-hb"]', 'halo.brightness', this.getConfig, this.sendUpdate);
        bindInput('#set-halo-blur-level select', 'halo.blur_level', false, this.getConfig, this.sendUpdate);
        bindInput('#set-halo-arc select', 'halo.gap_size', true, this.getConfig, this.sendUpdate);
        bindInput('#set-halo-show-hud', 'halo.show_arc_hud', false, this.getConfig, this.sendUpdate);
        bindInput('#set-halo-blend-icons', 'halo.blend_app_icons', false, this.getConfig, this.sendUpdate);
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
        
        setInputValue('#set-halo-act-mode select', halo.hold_mode || 'Hold');
        setInputValue('#set-halo-theme select', halo.theme || 'Dark');
        setSliderValue('[data-val="v-hb"]', halo.brightness !== undefined ? halo.brightness : 50);
        setInputValue('#set-halo-blur-level select', halo.blur_level || 'High');
        setInputValue('#set-halo-arc select', halo.gap_size || 75);
        setInputValue('#set-halo-show-hud', halo.show_arc_hud !== false);
        setInputValue('#set-halo-blend-icons', halo.blend_app_icons === true);
        
        setSliderValue('[data-val="v-md"]', halo.max_bound || 300);
        setSliderValue('[data-val="v-hr"]', halo.hub_ratio || 50);
        setSliderValue('[data-val="v-bo"]', halo.opacity || 185);
        setSliderValue('[data-val="v-ss"]', halo.scroll_sens || 50);
        setSliderValue('[data-val="v-ms"]', halo.mouse_sens || 100);

        // Update global haloLayers
        if (window.updateHaloLayersFromConfig) {
            window.updateHaloLayersFromConfig(halo.menus || []);
        }

        // Sync Hub widget slots from the real config so hubSlots stays in sync
        const hubCfg = cfg.hub_config || {};
        if (window.updateHubLayersFromConfig && hubCfg.layers) {
            window.updateHubLayersFromConfig(hubCfg.layers);
        }

    }
}
module.exports = { HaloTab };
