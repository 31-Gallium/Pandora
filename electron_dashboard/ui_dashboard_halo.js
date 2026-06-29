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

    _updateMediaVisibility(fromUser = false) {
        const artSelect = document.querySelector('#set-media-art');
        if (!artSelect) return;
        const isMosaic = artSelect.value === '8-Bit Mosaic';
        const visRow = document.querySelector('#set-media-vis')?.closest('.control-row');
        const mosaicRow = document.querySelector('#set-media-mosaic')?.closest('.control-row');
        const mosaicShapeRow = document.querySelector('#set-media-mosaic-shape')?.closest('.control-row');
        const strengthRow = document.querySelector('#i-media-strength')?.closest('.control-item');
        
        if (visRow) visRow.style.display = 'flex';
        if (mosaicRow) mosaicRow.style.display = isMosaic ? 'flex' : 'none';
        if (mosaicShapeRow) mosaicShapeRow.style.display = isMosaic ? 'flex' : 'none';
        if (strengthRow) strengthRow.style.display = 'block';
        
        // Update labels
        const strengthLabel = strengthRow?.querySelector('.control-label');
        if (strengthLabel) strengthLabel.textContent = isMosaic ? 'Block Size' : 'Blur Amount';
        
        // Update visualizer options
        const visSelect = document.querySelector('#set-media-vis');
        if (visSelect) {
            Array.from(visSelect.options).forEach(opt => {
                const val = opt.value;
                let shouldShow = false;
                if (val === 'None' || val === 'Edge Ring EQ') shouldShow = true;
                else if (val === 'Breathing Blur') shouldShow = !isMosaic;
                else shouldShow = isMosaic; // Voxel Wiggle, Size Pulsing, Brightness Strobing
                
                opt.hidden = !shouldShow;
                opt.disabled = !shouldShow;
            });
            
            // Fallback if current selection is now hidden
            const selectedOpt = visSelect.options[visSelect.selectedIndex];
            if (selectedOpt && selectedOpt.hidden) {
                visSelect.value = 'None';
                if (fromUser) {
                    visSelect.dispatchEvent(new Event('change'));
                }
            }
            
            // Refresh the custom select UI DOM
            if (typeof syncCustomSelect === 'function') {
                syncCustomSelect(visSelect);
            }
        }
    }



    init() {
        bindInput('#set-halo-act-mode select', 'halo.hold_mode', false, this.getConfig, this.sendUpdate);
        bindInput('#set-halo-theme select', 'halo.theme', false, this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-hb"]', 'halo.brightness', this.getConfig, this.sendUpdate);
        bindInput('#set-halo-blur-level select', 'halo.blur_level', false, this.getConfig, this.sendUpdate);
        bindInput('#set-halo-arc select', 'halo.gap_size', true, this.getConfig, this.sendUpdate);
        bindInput('#set-halo-show-hud', 'halo.show_arc_hud', false, this.getConfig, this.sendUpdate);
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

        // Bind Media Settings
        const artSelect = document.querySelector('#set-media-art');
        if (artSelect) {
            artSelect.addEventListener('change', (e) => {
                const cfg = this.getConfig();
                const settings = this._getWidgetSettings(cfg, 'media');
                
                const oldStyle = settings.art_style || 'Gaussian Blur';
                const currentVis = settings.visualizer || 'None';
                if (oldStyle === '8-Bit Mosaic') {
                    settings.last_mosaic_vis = currentVis;
                } else {
                    settings.last_blur_vis = currentVis;
                }
                
                const val = e.target.value;
                settings.art_style = val;
                
                if (val === '8-Bit Mosaic') {
                    settings.visualizer = settings.last_mosaic_vis || 'Voxel Wiggle';
                } else {
                    settings.visualizer = settings.last_blur_vis || 'Breathing Blur';
                }
                
                const visSelect = document.querySelector('#set-media-vis');
                if (visSelect) {
                    visSelect.value = settings.visualizer;
                }
                
                this._updateMediaVisibility(true);
                this.sendUpdate();
            });
        }
        
        const visSelect = document.querySelector('#set-media-vis');
        if (visSelect) {
            visSelect.addEventListener('change', (e) => {
                const cfg = this.getConfig();
                const settings = this._getWidgetSettings(cfg, 'media');
                const val = e.target.value;
                settings.visualizer = val;
                if (settings.art_style === '8-Bit Mosaic') {
                    settings.last_mosaic_vis = val;
                } else {
                    settings.last_blur_vis = val;
                }
                this.sendUpdate();
            });
        }
        this._bindWidget('#set-media-mosaic', 'media', 'mosaic_style', false);
        this._bindWidget('#set-media-mosaic-shape', 'media', 'mosaic_shape', false);
        this._bindWidget('#i-media-strength', 'media', 'effect_strength', true, false, true);
        this._bindWidget('#set-media-timeline', 'media', 'show_timeline', false, true);
        this._bindWidget('#set-media-title', 'media', 'show_title', false, true);
        this._bindWidget('#set-media-controls', 'media', 'show_controls', false, true);

        // Bind Time Settings
        this._bindWidget('#set-time-mode', 'time', 'clock_mode', false);
        this._bindWidget('#set-time-24h', 'time', 'format_24h', false, true);
        this._bindWidget('#set-time-date', 'time', 'show_date', false, true);
        this._bindWidget('#set-time-seconds', 'time', 'show_seconds', false, true);
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

        const mediaSettings = this._getWidgetSettings(cfg, 'media');
        setInputValue('#set-media-art', mediaSettings.art_style || 'Gaussian Blur');
        this._updateMediaVisibility();
        setInputValue('#set-media-vis', mediaSettings.visualizer || 'None');
        setInputValue('#set-media-mosaic', mediaSettings.mosaic_style || 'Flat');
        setInputValue('#set-media-mosaic-shape', mediaSettings.mosaic_shape || 'Square');
        setSliderValue('#i-media-strength', mediaSettings.effect_strength !== undefined ? mediaSettings.effect_strength : 25);
        setCheckboxValue('#set-media-timeline', mediaSettings.show_timeline !== false);
        setCheckboxValue('#set-media-title', mediaSettings.show_title !== false);
        setCheckboxValue('#set-media-controls', mediaSettings.show_controls !== false);

        const timeSettings = this._getWidgetSettings(cfg, 'time');
        setInputValue('#set-time-mode', timeSettings.clock_mode || 'digital');
        setCheckboxValue('#set-time-24h', timeSettings.format_24h !== false);
        setCheckboxValue('#set-time-date', timeSettings.show_date !== false);
        setCheckboxValue('#set-time-seconds', timeSettings.show_seconds === true);
    }
}
module.exports = { HaloTab };
