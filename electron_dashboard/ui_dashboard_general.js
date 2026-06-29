const { ipcRenderer } = require('electron');
const { getVkName, bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue } = require('./ui_dashboard_common.js');

const THEME_CLASSES = ['light-theme', 'gray-theme', 'desktop-theme'];

function applyDashboardTheme(cfg) {
    const t = (cfg.general_settings || {}).dashboard_theme || 'Dark';
    
    // Remove all theme classes first
    THEME_CLASSES.forEach(c => document.body.classList.remove(c));
    

    
    if (t === 'Light') {
        document.body.classList.add('light-theme');
    } else if (t === 'Gray') {
        document.body.classList.add('gray-theme');
    } else if (t === 'Desktop') {
        document.body.classList.add('desktop-theme');
        
        // Read accent colors from config (injected by Python backend)
        const accents = (cfg.general_settings || {}).desktop_accents || [];
        if (accents.length > 0) {
            const root = document.documentElement.style;
            accents.forEach((rgb, i) => {
                const [r, g, b] = rgb;
                root.setProperty(`--desktop-accent-${i + 1}`, `rgb(${r},${g},${b})`);
            });
            // Derive glow from primary accent
            const [r0, g0, b0] = accents[0];
            root.setProperty('--desktop-glow-1', `rgba(${r0},${g0},${b0},0.15)`);
            
            // Derive surface colors: very dark tinted version of the primary accent
            const sr = Math.round(r0 * 0.08);
            const sg = Math.round(g0 * 0.08);
            const sb = Math.round(b0 * 0.08);
            root.setProperty('--desktop-surface-1', `rgb(${sr + 10},${sg + 10},${sb + 10})`);
            root.setProperty('--desktop-surface-2', `rgb(${sr + 16},${sg + 16},${sb + 16})`);
        }
    }
    // Dark = default, no class needed
}

class GeneralTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
        this.activeKeybindInput = null;
    }

    init() {
        bindSlider('[data-val="v-gs"]', 'general_settings.grid_size', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-ep-all"]', 'general_settings.edge_padding', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-ep-v"]', 'general_settings.edge_padding_v', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-ep-h"]', 'general_settings.edge_padding_h', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-ep-t"]', 'general_settings.edge_padding_t', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-ep-b"]', 'general_settings.edge_padding_b', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-ep-l"]', 'general_settings.edge_padding_l', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-ep-r"]', 'general_settings.edge_padding_r', this.getConfig, this.sendUpdate);
        bindSlider('[data-val="v-gv"]', 'general_settings.grid_opacity', this.getConfig, this.sendUpdate);
        const self = this;
        
        // Hierarchical Padding Logic
        const toggleExpand = (btnId, targetId) => {
            const btn = document.getElementById(btnId);
            const target = document.getElementById(targetId);
            if (btn && target) {
                btn.addEventListener('click', () => {
                    const isHidden = target.style.display === 'none';
                    target.style.display = isHidden ? 'block' : 'none';
                    btn.style.transform = isHidden ? 'rotate(180deg)' : '';
                    btn.classList.toggle('active', isHidden);
                });
            }
        };
        toggleExpand('expand-ep-all', 'children-ep');
        toggleExpand('expand-ep-v', 'children-ep-v');
        toggleExpand('expand-ep-h', 'children-ep-h');

        const epAll = document.querySelector('[data-val="v-ep-all"]');
        const epV = document.querySelector('[data-val="v-ep-v"]');
        const epH = document.querySelector('[data-val="v-ep-h"]');
        const epT = document.querySelector('[data-val="v-ep-t"]');
        const epB = document.querySelector('[data-val="v-ep-b"]');
        const epL = document.querySelector('[data-val="v-ep-l"]');
        const epR = document.querySelector('[data-val="v-ep-r"]');

        const handleSync = (source, children) => {
            let changed = false;
            children.forEach(child => {
                if (child.el && source.value !== child.el.value) {
                    setSliderValue('[data-val="' + child.el.getAttribute('data-val') + '"]', source.value);
                    self.getConfig().general_settings[child.key] = parseInt(source.value);
                    changed = true;
                }
            });
            if (changed) self.sendUpdate();
        };

        const collapseContainer = (btnId, targetId) => {
            const btn = document.getElementById(btnId);
            const target = document.getElementById(targetId);
            if (btn && target && target.style.display !== 'none') {
                target.style.display = 'none';
                btn.style.transform = '';
                btn.classList.remove('active');
            }
        };

        if (epAll) {
            epAll.addEventListener('input', () => {
                collapseContainer('expand-ep-all', 'children-ep');
                handleSync(epAll, [
                    {el: epV, key: 'edge_padding_v'},
                    {el: epH, key: 'edge_padding_h'},
                    {el: epT, key: 'edge_padding_t'},
                    {el: epB, key: 'edge_padding_b'},
                    {el: epL, key: 'edge_padding_l'},
                    {el: epR, key: 'edge_padding_r'}
                ]);
            });
        }
        if (epV) {
            epV.addEventListener('input', () => {
                collapseContainer('expand-ep-v', 'children-ep-v');
                handleSync(epV, [
                    {el: epT, key: 'edge_padding_t'},
                    {el: epB, key: 'edge_padding_b'}
                ]);
            });
        }
        if (epH) {
            epH.addEventListener('input', () => {
                collapseContainer('expand-ep-h', 'children-ep-h');
                handleSync(epH, [
                    {el: epL, key: 'edge_padding_l'},
                    {el: epR, key: 'edge_padding_r'}
                ]);
            });
        }
        const sendUpdateWithTheme = () => {
            applyDashboardTheme(self.getConfig());
            self.sendUpdate();
        };
        bindInput('#set-dashboard-theme select', 'general_settings.dashboard_theme', false, this.getConfig, sendUpdateWithTheme);
        bindInput('#set-theme-intensity select', 'general_settings.theme_intensity', false, this.getConfig, this.sendUpdate);
        
        // Folder Theme binding & visibility toggle
        const folderThemeSelect = document.querySelector('#set-folder-theme select');
        const customColorContainer = document.getElementById('custom-color-container');
        if (folderThemeSelect && customColorContainer) {
            bindInput('#set-folder-theme select', 'general_settings.folder_theme', false, this.getConfig, () => {
                customColorContainer.classList.toggle('expanded', folderThemeSelect.value === 'Custom');
                this.sendUpdate();
            });
        }
            
        // Advanced Color Picker Logic
        const cwArea = document.getElementById('cw-area');
        const cwThumb = document.getElementById('cw-thumb');
        const valTrack = document.getElementById('cw-val-track');
        const valThumb = document.getElementById('cw-val-thumb');
        const valOverlay = document.getElementById('cw-value-overlay');
        const alphaTrack = document.getElementById('cw-alpha-track');
        const alphaThumb = document.getElementById('cw-alpha-thumb');
        const hexInput = document.getElementById('custom-theme-hex-input');
        const hexPreview = document.getElementById('custom-hex-preview');
        
        this.currentHSV = { h: 0, s: 0, v: 1, a: 1 };
        
        const hsvToRgb = (h, s, v) => {
            let r, g, b, i, f, p, q, t;
            i = Math.floor(h * 6);
            f = h * 6 - i;
            p = v * (1 - s);
            q = v * (1 - f * s);
            t = v * (1 - (1 - f) * s);
            switch (i % 6) {
                case 0: r = v; g = t; b = p; break;
                case 1: r = q; g = v; b = p; break;
                case 2: r = p; g = v; b = t; break;
                case 3: r = p; g = q; b = v; break;
                case 4: r = t; g = p; b = v; break;
                case 5: r = v; g = p; b = q; break;
            }
            return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
        };
        
        const rgbToHex = (r, g, b, a) => {
            const toHex = (n) => n.toString(16).padStart(2, '0').toUpperCase();
            return `#${toHex(r)}${toHex(g)}${toHex(b)}${toHex(Math.round(a * 255))}`;
        };
        
        this.parseHex = (hex) => {
            hex = hex.replace('#', '');
            if (hex.length === 6) hex += 'FF';
            if (hex.length !== 8) return null;
            const r = parseInt(hex.substring(0, 2), 16);
            const g = parseInt(hex.substring(2, 4), 16);
            const b = parseInt(hex.substring(4, 6), 16);
            const a = parseInt(hex.substring(6, 8), 16) / 255;
            
            const max = Math.max(r, g, b), min = Math.min(r, g, b);
            const d = max - min;
            let h = 0, s = 0, v = max / 255;
            s = max === 0 ? 0 : d / max;
            if (max !== min) {
                switch (max) {
                    case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                    case g: h = (b - r) / d + 2; break;
                    case b: h = (r - g) / d + 4; break;
                }
                h /= 6;
            }
            return { h, s, v, a };
        };
        
        this.updatePickerVisuals = () => {
            const radius = 50;
            const angle = this.currentHSV.h * Math.PI * 2 - Math.PI/2;
            const dist = this.currentHSV.s * radius;
            const x = radius + Math.cos(angle) * dist;
            const y = radius + Math.sin(angle) * dist;
            
            if (cwThumb) {
                cwThumb.style.left = `${x}px`;
                cwThumb.style.top = `${y}px`;
            }
            
            if (valOverlay) valOverlay.style.background = `rgba(0,0,0,${1 - this.currentHSV.v})`;
            if (valThumb) valThumb.style.left = `${this.currentHSV.v * 100}%`;
            
            const [r, g, b] = hsvToRgb(this.currentHSV.h, this.currentHSV.s, this.currentHSV.v);
            if (alphaTrack) alphaTrack.style.setProperty('--alpha-color', `rgb(${r},${g},${b})`);
            if (alphaThumb) alphaThumb.style.left = `${this.currentHSV.a * 100}%`;
            
            const hex = rgbToHex(r, g, b, this.currentHSV.a);
            if (hexPreview) hexPreview.style.background = `rgba(${r},${g},${b},${this.currentHSV.a})`;
            if (hexInput && document.activeElement !== hexInput) hexInput.value = hex.substring(1);
            
            return hex;
        };
        
        this.isColorDragging = false;
        let debounceTimer;
        const notifyColorChange = () => {
            const hex = this.updatePickerVisuals();
            if (!this.getConfig().general_settings) this.getConfig().general_settings = {};
            this.getConfig().general_settings.folder_custom_color = hex;
            
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                this.sendUpdate();
            }, 50);
        };
        
        const setupDrag = (element, handler) => {
            if (!element) return;
            let isDragging = false;
            element.addEventListener('mousedown', (e) => { 
                isDragging = true; 
                this.isColorDragging = true; 
                handler(e); 
            });
            window.addEventListener('mousemove', (e) => { 
                if (isDragging) handler(e); 
            });
            window.addEventListener('mouseup', () => { 
                if (isDragging) {
                    isDragging = false;
                    this.isColorDragging = false;
                    clearTimeout(debounceTimer);
                    this.sendUpdate(); // Send final definitive update
                }
            });
        };
        
        setupDrag(cwArea, (e) => {
            const rect = cwArea.getBoundingClientRect();
            const cx = rect.width / 2;
            const cy = rect.height / 2;
            const x = e.clientX - rect.left - cx;
            const y = e.clientY - rect.top - cy;
            
            let angle = Math.atan2(y, x) + Math.PI/2;
            if (angle < 0) angle += Math.PI * 2;
            this.currentHSV.h = angle / (Math.PI * 2);
            this.currentHSV.s = Math.min(1, Math.sqrt(x*x + y*y) / cx);
            notifyColorChange();
        });
        
        setupDrag(valTrack, (e) => {
            const rect = valTrack.getBoundingClientRect();
            let v = (e.clientX - rect.left) / rect.width;
            this.currentHSV.v = Math.max(0, Math.min(1, v));
            notifyColorChange();
        });
        
        setupDrag(alphaTrack, (e) => {
            const rect = alphaTrack.getBoundingClientRect();
            let a = (e.clientX - rect.left) / rect.width;
            this.currentHSV.a = Math.max(0, Math.min(1, a));
            notifyColorChange();
        });
        
        if (hexInput) {
            hexInput.addEventListener('change', (e) => {
                let val = e.target.value.replace(/[^0-9A-Fa-f]/g, '');
                const parsed = this.parseHex(val);
                if (parsed) {
                    this.currentHSV = parsed;
                    notifyColorChange();
                } else {
                    this.updatePickerVisuals();
                }
            });
        }
        

        bindInput('#set-pagination-style select', 'general_settings.pagination_style', false, this.getConfig, this.sendUpdate);
        bindInput('#set-show-grid-drag input', 'general_settings.show_grid_on_drag', false, this.getConfig, this.sendUpdate);
        bindInput('#set-anim-grid-color input', 'general_settings.grid_animated_color', false, this.getConfig, this.sendUpdate);
        bindInput('#set-wave-ent input', 'general_settings.grid_wave_entrance', false, this.getConfig, this.sendUpdate);
        bindInput('#set-wave-color input', 'general_settings.grid_wave_fade', false, this.getConfig, this.sendUpdate);

        bindInput('#set-filter-preset select', 'display_effects.active_preset', false, this.getConfig, this.sendUpdate);
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
        setSliderValue('[data-val="v-ep-all"]', gen.edge_padding !== undefined ? gen.edge_padding : 0);
        setSliderValue('[data-val="v-ep-v"]', gen.edge_padding_v !== undefined ? gen.edge_padding_v : (gen.edge_padding || 0));
        setSliderValue('[data-val="v-ep-h"]', gen.edge_padding_h !== undefined ? gen.edge_padding_h : (gen.edge_padding || 0));
        setSliderValue('[data-val="v-ep-t"]', gen.edge_padding_t !== undefined ? gen.edge_padding_t : (gen.edge_padding || 0));
        setSliderValue('[data-val="v-ep-b"]', gen.edge_padding_b !== undefined ? gen.edge_padding_b : (gen.edge_padding || 0));
        setSliderValue('[data-val="v-ep-l"]', gen.edge_padding_l !== undefined ? gen.edge_padding_l : (gen.edge_padding || 0));
        setSliderValue('[data-val="v-ep-r"]', gen.edge_padding_r !== undefined ? gen.edge_padding_r : (gen.edge_padding || 0));
        setSliderValue('[data-val="v-gv"]', gen.grid_opacity || 100);
        
        const dashTheme = gen.dashboard_theme || 'Dark';
        setInputValue('#set-dashboard-theme select', dashTheme);
        
        // Fallback to old config name if new one doesn't exist yet
        const themeIntensity = gen.theme_intensity || (gen.folder_darkness !== undefined ? 
            (gen.folder_darkness === 'Light' ? 'Subtle' : 
             gen.folder_darkness === 'Medium' ? 'Balanced' : 
             gen.folder_darkness === 'Pitch Black' ? 'Solid' : 'Intense') 
            : 'Intense');
        setInputValue('#set-theme-intensity select', themeIntensity);
        
        const folderTheme = gen.folder_theme || 'Default';
        setInputValue('#set-folder-theme select', folderTheme);
        const customColorContainer = document.getElementById('custom-color-container');
        if (customColorContainer) {
            customColorContainer.classList.toggle('expanded', folderTheme === 'Custom');
            
            const customColor = gen.folder_custom_color || '#161B22FF';
            if (!this.isColorDragging) {
                const parsed = this.parseHex && this.parseHex(customColor);
                if (parsed) {
                    this.currentHSV = parsed;
                    if (this.updatePickerVisuals) this.updatePickerVisuals();
                }
            }
        }
        
        const pagStyle = gen.pagination_style || 'Pill & Dots';
        setInputValue('#set-pagination-style select', pagStyle);
        
        applyDashboardTheme(cfg);
        
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
        
        setInputValue('#set-filter-preset select', disp.active_preset || 'Sunset');
        setSliderValue('[data-val="v-wi"]', disp.warmth_intensity || 50);
    }
}
module.exports = { GeneralTab };
