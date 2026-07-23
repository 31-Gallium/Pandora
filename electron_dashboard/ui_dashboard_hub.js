const { bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue, syncCustomSelect } = require('./ui_dashboard_common.js');

class HubTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
    }
    
    _getWidgetSettings(cfg, widgetName, createIfMissing=false) {
        if (!cfg.hub_config) cfg.hub_config = {};
        if (!cfg.hub_config.layers) cfg.hub_config.layers = [];
        
        for (const layer of cfg.hub_config.layers) {
            if (layer && layer.type === widgetName) {
                if (!layer.settings) layer.settings = {};
                return layer.settings;
            }
        }
        
        if (createIfMissing) {
            const layer = { id: "layer_" + widgetName, type: widgetName, settings: {} };
            cfg.hub_config.layers.push(layer);
            return layer.settings;
        }
        
        return {};
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
                
                // Update --fill progress styling dynamically
                const min = parseFloat(el.min || 0);
                const max = parseFloat(el.max || 100);
                const pct = ((parseFloat(val) - min) / (max - min)) * 100;
                el.style.setProperty('--fill', pct + '%');
            }
            
            this.sendUpdate();
        });
    }

    _updateMediaVisibility(isUpdating = false) {
        const cfg = this.getConfig();
        const settings = this._getWidgetSettings(cfg, 'media');
        
        const isMosaic = settings.art_style === '8-Bit Mosaic';
        const isFerro = settings.art_style === 'Liquid Ferrofluid';
        const isReactive = settings.visualizer === 'Reactive Voxels';
        
        // Mosaic Shape setting visibility
        const mosaicGroup = document.querySelector('#set-media-mosaic-shape')?.closest('.control-row');
        if (mosaicGroup) mosaicGroup.style.display = isMosaic ? 'flex' : 'none';

        // Effect Strength label and visibilty
        const strengthLabel = document.querySelector('#set-media-strength-label');
        if (strengthLabel) {
            strengthLabel.textContent = isMosaic ? 'Block Size' : 'Blur Strength';
        }

        // Animation Style setting visibility
        const animGroup = document.querySelector('.segmented-group[name="anim_style"]')?.closest('.control-group');
        if (animGroup) animGroup.style.display = isReactive ? 'block' : 'none';
        
        // Update visualizer options
        const visSelect = document.querySelector('#set-media-vis');
        if (visSelect && isUpdating) {
            const currentValue = visSelect.value;
            visSelect.innerHTML = '';
            const options = ['None'];
            
            if (isMosaic) {
                options.push('Reactive Voxels');
            } else {
                options.push('Edge Ring EQ');
            }
            
            options.forEach(opt => {
                const el = document.createElement('option');
                el.value = opt;
                el.textContent = opt;
                visSelect.appendChild(el);
            });
            
            if (options.includes(currentValue)) {
                visSelect.value = currentValue;
            } else {
                visSelect.value = options.includes(settings.visualizer) ? settings.visualizer : 'None';
            }
            
            syncCustomSelect(visSelect);
        }
    }

    init() {
        // Display Effects (Moved from General)
        bindInput('#set-filter-preset select', 'display_effects.active_preset', false, this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-wi"]', 'display_effects.warmth_intensity', this.getConfig, this.sendUpdate);

        // Media Settings (Moved from Halo)
        const artSelect = document.querySelector('#set-media-art');
        if (artSelect) {
            artSelect.addEventListener('change', (e) => {
                const cfg = this.getConfig();
                const settings = this._getWidgetSettings(cfg, 'media', true);
                
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
                    settings.visualizer = settings.last_mosaic_vis || 'Reactive Voxels';
                } else {
                    settings.visualizer = settings.last_blur_vis || 'Edge Ring EQ';
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
                const settings = this._getWidgetSettings(cfg, 'media', true);
                const val = e.target.value;
                settings.visualizer = val;
                if (settings.art_style === '8-Bit Mosaic') {
                    settings.last_mosaic_vis = val;
                } else {
                    settings.last_blur_vis = val;
                }
                
                this._updateMediaVisibility(false);
                this.sendUpdate();
            });
        }

        this._bindWidget('#set-media-mosaic-shape', 'media', 'mosaic_shape', true);
        this._bindWidget('#i-media-strength', 'media', 'effect_strength', true, false, true);
        this._bindWidget('#set-media-timeline', 'media', 'show_timeline', false, true);
        this._bindWidget('#set-media-title', 'media', 'show_title', false, true);
        this._bindWidget('#set-media-controls', 'media', 'show_controls', false, true);
        
        const animRadios = document.querySelectorAll('input[type=radio][name=anim_style]');
        animRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.checked) {
                    const cfg = this.getConfig();
                    const settings = this._getWidgetSettings(cfg, 'media');
                    settings.animation_style = radio.value;
                    this.sendUpdate();
                }
            });
        });

        // Time Settings (Moved from Halo)
        this._bindWidget('#set-time-mode', 'time', 'clock_mode', false);
        this._bindWidget('#set-time-24h', 'time', 'format_24h', false, true);
        this._bindWidget('#set-time-date', 'time', 'show_date', false, true);
        this._bindWidget('#set-time-seconds', 'time', 'show_seconds', false, true);
    }

    updateUI(cfg) {
        const disp = cfg.display_effects || {};
        setInputValue('#set-filter-preset select', disp.active_preset || 'Sunset');
        setSliderValue('[data-val="v-wi"]', disp.warmth_intensity || 50);

        const mediaSettings = this._getWidgetSettings(cfg, 'media');
        setInputValue('#set-media-art', mediaSettings.art_style || 'Gaussian Blur');
        this._updateMediaVisibility(true);
        setInputValue('#set-media-vis', mediaSettings.visualizer || 'None');

        setInputValue('#set-media-mosaic-shape', mediaSettings.mosaic_shape || 'Square');
        setSliderValue('#i-media-strength', mediaSettings.effect_strength !== undefined ? mediaSettings.effect_strength : 25);
        
        const animStyle = mediaSettings.animation_style || 'Balanced';
        const animRadios = document.querySelectorAll('input[type=radio][name=anim_style]');
        animRadios.forEach(r => r.checked = (r.value === animStyle));
        
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
module.exports = { HubTab };
