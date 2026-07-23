
function renderSvgIcon(src, width, height, extraStyle="") {
    return `<div style="-webkit-mask-image: url('${src}'); -webkit-mask-size: contain; -webkit-mask-repeat: no-repeat; -webkit-mask-position: center; background-color: currentColor; width: ${width}px; height: ${height}px; display: inline-block; ${extraStyle}"></div>`;
}
const { ipcRenderer } = require('electron');
const vkMap = {
    1: 'Left Click', 2: 'Right Click', 4: 'Middle Click',
    192: '~ / `', 9: 'Tab', 16: 'Shift', 17: 'Ctrl', 18: 'Alt',
    20: 'Caps Lock', 27: 'Esc', 32: 'Space', 13: 'Enter', 8: 'Backspace',
    37: '← Arrow', 38: '↑ Arrow', 39: '→ Arrow', 40: '↓ Arrow',
    46: 'Delete', 45: 'Insert', 36: 'Home', 35: 'End',
    33: 'Page Up', 34: 'Page Down'
};

function getVkName(code) {
    if (vkMap[code]) return vkMap[code];
    if (code >= 65 && code <= 90) return String.fromCharCode(code);
    if (code >= 48 && code <= 57) return String.fromCharCode(code);
    if (code >= 112 && code <= 123) return 'F' + (code - 111);
    if (code >= 96 && code <= 105) return 'Num ' + (code - 96);
    return `Code: ${code}`;
}

function bindInput(selector, configPath, isNumber, getConfig, updateCallback) {
    const el = document.querySelector(selector);
    if (!el) return;
    const parts = configPath.split('.');
    
    el.addEventListener('change', (e) => {
        const cfg = getConfig();
        let target = cfg;
        for (let i = 0; i < parts.length - 1; i++) {
            if (!target[parts[i]]) target[parts[i]] = {};
            target = target[parts[i]];
        }
        const key = parts[parts.length - 1];
        
        if (el.type === 'checkbox') {
            target[key] = e.target.checked;
        } else {
            target[key] = isNumber ? parseInt(e.target.value) : e.target.value;
        }
        updateCallback();
    });
}

function bindSlider(selector, configPath, getConfig, updateCallback) {
    const el = document.querySelector(selector);
    if (!el) return;
    const valId = el.getAttribute('data-val');
    const parts = configPath.split('.');
    
    el.addEventListener('input', (e) => {
        if (valId) {
            const valEl = document.getElementById(valId);
            if(valEl) valEl.innerText = e.target.value;
        }
        
        // Update --fill progress styling dynamically
        const min = parseFloat(el.min || 0);
        const max = parseFloat(el.max || 100);
        const pct = ((parseFloat(e.target.value) - min) / (max - min)) * 100;
        el.style.setProperty('--fill', pct + '%');
        
        const cfg = getConfig();
        let target = cfg;
        for (let i = 0; i < parts.length - 1; i++) {
            if (!target[parts[i]]) target[parts[i]] = {};
            target = target[parts[i]];
        }
        target[parts[parts.length - 1]] = parseInt(e.target.value);
        updateCallback();
    });
}

function setInputValue(selector, value) {
    const el = document.querySelector(selector);
    if (el) {
        el.value = value;
        if (el.tagName === 'SELECT') syncCustomSelect(el);
    }
}

function setCheckboxValue(selector, checked) {
    const el = document.querySelector(selector);
    if (el) el.checked = checked;
}

function setSliderValue(selector, value) {
    const el = document.querySelector(selector);
    if (el) {
        el.value = value;
        const min = parseFloat(el.min || 0);
        const max = parseFloat(el.max || 100);
        const pct = ((value - min) / (max - min)) * 100;
        el.style.setProperty('--fill', pct + '%');
        const valId = el.getAttribute('data-val');
        if (valId) {
            const valEl = document.getElementById(valId);
            if(valEl) valEl.innerText = Math.round(value);
        }
    }
}

// Global UI Initialization
function initGlobalUI() {
    /* ═══ Accent color mapping ═══ */
const accentMap = {
    general: 'var(--accent-general)',
    templates: 'var(--accent-templates)',
    folders: 'var(--accent-folders)',
    halo: 'var(--accent-halo)',
    hub: 'var(--accent-hub)',
    system: 'var(--accent-system)'
};
const rawMap = {
    general: '#00f0ff',
    templates: '#BD93F9',
    folders: '#50FA7B',
    halo: '#FF79C6',
    hub: '#FACC15',
    system: '#F472B6'
};

/* ═══ Tab Switching ═══ */
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        closeCmdBank();
        const tab = item.dataset.tab;
        const label = item.dataset.label;
        const cssVar = accentMap[tab];

        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        item.classList.add('active');
        document.querySelectorAll('.tab-page').forEach(t => t.classList.remove('active'));
        document.getElementById('tab-' + tab).classList.add('active');

        // Update pill
        document.getElementById('pill-text').textContent = label;
        
        // Remove old inline styles in case they were set previously
        const pill = document.getElementById('page-pill');
        pill.style.color = '';
        pill.style.borderColor = '';
        const dot = pill.querySelector('.pill-dot');
        if(dot) {
            dot.style.background = '';
            dot.style.boxShadow = '';
        }

        // Update sidebar active indicator, glow, pill, and sliders by setting --accent globally
        document.body.style.setProperty('--accent', cssVar);
        item.style.setProperty('--accent', cssVar);

        // Scroll main to top
        document.getElementById('main-panel').scrollTop = 0;
        
        // Notify Python panel about tab changes (so it hides if we leave the templates tab)
        if (typeof updateSandboxRect === 'function') {
            setTimeout(updateSandboxRect, 50);
        }
    });
});

/* ═══ Sidebar Toggle ═══ */
document.getElementById('toggle-sidebar').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('expanded');
});

// Title Pill Dropdown Logic
const pagePill = document.getElementById('page-pill');
const pillDropdown = document.getElementById('pill-dropdown');
// Title Pill Dropdown Search Logic
const searchIndex = [
    { id: "v-gs", name: "Grid Size", tab: "general", group: "Appearance" },
    { id: "v-ep-all", name: "Edge Padding", tab: "general", group: "Appearance" },
    { id: "v-ep-v", name: "Vertical Padding", tab: "general", group: "Appearance" },
    { id: "v-ep-h", name: "Horizontal Padding", tab: "general", group: "Appearance" },
    { id: "v-ep-t", name: "Padding Top", tab: "general", group: "Appearance" },
    { id: "v-ep-b", name: "Padding Bottom", tab: "general", group: "Appearance" },
    { id: "v-ep-l", name: "Padding Left", tab: "general", group: "Appearance" },
    { id: "v-ep-r", name: "Padding Right", tab: "general", group: "Appearance" },
    { id: "v-gv", name: "Grid Visibility", tab: "general", group: "Appearance" },
    { id: "set-theme-intensity", name: "Theme Intensity", tab: "general", group: "Appearance" },
    { id: "set-folder-theme", name: "Folder Theme", tab: "general", group: "Appearance" },
    { id: "custom-theme-hex-input", name: "Custom Base Color", tab: "general", group: "Appearance" },
    { id: "set-dashboard-theme", name: "Dashboard Theme", tab: "general", group: "Appearance" },
    { id: "set-pagination-style", name: "Pagination Style", tab: "general", group: "Appearance" },
    { id: "set-show-grid-drag", name: "Show Grid on Drag", tab: "general", group: "Grid Behavior" },
    { id: "set-anim-grid-color", name: "Animated Grid Color", tab: "general", group: "Grid Behavior" },
    { id: "set-wave-ent", name: "Wave Entrance", tab: "general", group: "Grid Behavior" },
    { id: "set-wave-color", name: "Wave Color Fade", tab: "general", group: "Grid Behavior" },
    { id: "set-launch-startup", name: "Launch at Startup", tab: "system", group: "System" },
    { id: "set-open-dash-startup", name: "Open Dashboard at Startup", tab: "system", group: "System" },
    { id: "set-system-gpu-pref", name: "Hardware Acceleration", tab: "system", group: "System" },
    { id: "set-filter-preset", name: "Filter Preset", tab: "hub", group: "Display Effects" },
    { id: "v-wi", name: "Warmth Intensity", tab: "hub", group: "Display Effects" },
    { id: "set-halo-act-key", name: "Halo Activation Key", tab: "halo", group: "Activation & Behavior" },
    { id: "set-halo-act-mode", name: "Halo Activation Mode", tab: "halo", group: "Activation & Behavior" },
    { id: "set-halo-theme", name: "Visual Theme", tab: "halo", group: "Activation & Behavior" },
    { id: "v-hb", name: "Brightness", tab: "halo", group: "Activation & Behavior" },
    { id: "set-halo-blur-level", name: "Blur Level", tab: "halo", group: "Activation & Behavior" },
    { id: "set-halo-blur-mode", name: "Blur Mode", tab: "halo", group: "Activation & Behavior" },
    { id: "set-halo-arc", name: "HUD Arc Gap", tab: "halo", group: "Activation & Behavior" },
    { id: "set-halo-show-hud", name: "Show HUD Text", tab: "halo", group: "Activation & Behavior" },
    { id: "set-halo-blend-icons", name: "Blend Custom App Icons", tab: "halo", group: "Activation & Behavior" },
    { id: "v-md", name: "Menu Diameter", tab: "halo", group: "Dimensions & Feel" },
    { id: "v-hr", name: "Hub Ratio (%)", tab: "halo", group: "Dimensions & Feel" },
    { id: "v-bo", name: "BG Opacity", tab: "halo", group: "Dimensions & Feel" },
    { id: "v-ss", name: "Scroll Sensitivity", tab: "halo", group: "Dimensions & Feel" },
    { id: "v-ms", name: "Mouse Sensitivity", tab: "halo", group: "Dimensions & Feel" },
    { id: "set-media-art", name: "Art Style", tab: "hub", group: "Media Widget Settings" },
    { id: "set-media-vis", name: "Visualizer", tab: "hub", group: "Media Widget Settings" },
    { id: "set-media-mosaic-shape", name: "Mosaic Shape", tab: "hub", group: "Media Widget Settings" },
    { id: "v-media-strength", name: "Effect Strength", tab: "hub", group: "Media Widget Settings" },
    { id: "set-media-animation", name: "Animation Style", tab: "hub", group: "Media Widget Settings" },
    { id: "set-media-timeline", name: "Show Timeline", tab: "hub", group: "Media Widget Settings" },
    { id: "set-media-title", name: "Show Title", tab: "hub", group: "Media Widget Settings" },
    { id: "set-media-controls", name: "Show Controls", tab: "hub", group: "Media Widget Settings" },
    { id: "set-time-mode", name: "Clock Mode", tab: "hub", group: "Time Widget Settings" },
    { id: "set-time-24h", name: "24-Hour Format", tab: "hub", group: "Time Widget Settings" },
    { id: "set-time-date", name: "Show Date", tab: "hub", group: "Time Widget Settings" },
    { id: "set-time-seconds", name: "Show Seconds", tab: "hub", group: "Time Widget Settings" }
];

const pillSearchInput = document.getElementById('pill-search-input');
const pillDropdownDefault = document.getElementById('pill-dropdown-default');
const pillDropdownResults = document.getElementById('pill-dropdown-results');
const scrollBorderRect = document.getElementById('scroll-border-rect');
let currentSelectedIndex = -1;
let currentResults = [];

function updatePerimeterScroll() {
    const el = pillDropdownResults;
    if (el.scrollHeight > el.clientHeight && el.style.display !== 'none') {
        const viewRatio = el.clientHeight / el.scrollHeight;
        const thumbLen = viewRatio * 100;
        const gapLen = 100 - thumbLen;
        const scrollRatio = el.scrollTop / (el.scrollHeight - el.clientHeight);
        const offset = -(scrollRatio * gapLen);
        
        scrollBorderRect.style.opacity = '1';
        scrollBorderRect.style.strokeDasharray = `${thumbLen} ${gapLen}`;
        scrollBorderRect.style.strokeDashoffset = offset;
    } else {
        scrollBorderRect.style.opacity = '0';
    }
}

pillDropdownResults.addEventListener('scroll', updatePerimeterScroll);
new ResizeObserver(updatePerimeterScroll).observe(pillDropdownResults);

function updateSearchSelection() {
    const items = pillDropdownResults.querySelectorAll('.search-result-item');
    items.forEach((item, idx) => {
        if (idx === currentSelectedIndex) {
            item.classList.add('keyboard-focus');
            item.scrollIntoView({ block: 'nearest' });
        } else {
            item.classList.remove('keyboard-focus');
        }
    });
}

pillSearchInput.addEventListener('keydown', (e) => {
    if (pillDropdownResults.style.display === 'none') return;
    
    const items = pillDropdownResults.querySelectorAll('.search-result-item');
    if (items.length === 0) return;

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        currentSelectedIndex = currentSelectedIndex >= items.length - 1 ? 0 : currentSelectedIndex + 1;
        updateSearchSelection();
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        currentSelectedIndex = currentSelectedIndex <= 0 ? items.length - 1 : currentSelectedIndex - 1;
        updateSearchSelection();
    } else if (e.key === 'Enter') {
        e.preventDefault();
        let idx = currentSelectedIndex >= 0 ? currentSelectedIndex : 0;
        if (idx < items.length) {
            items[idx].click();
            // Optional: reset input and close
            pillSearchInput.blur();
        }
    }
});

pillSearchInput.addEventListener('input', (e) => {
    const q = e.target.value.toLowerCase().trim();
    currentSelectedIndex = -1;
    if (!q) {
        pillDropdownDefault.style.display = 'block';
        pillDropdownResults.style.display = 'none';
        return;
    }
    
    pillDropdownDefault.style.display = 'none';
    pillDropdownResults.style.display = 'flex';
    pillDropdownResults.innerHTML = '';
    
    currentResults = searchIndex.filter(item => 
        item.name.toLowerCase().includes(q) ||
        item.group.toLowerCase().includes(q) ||
        item.tab.toLowerCase().includes(q)
    );
    
    if (currentResults.length === 0) {
        pillDropdownResults.innerHTML = '<div style="padding: 8px 12px; color: var(--text-3); font-size: 11px;">No settings found</div>';
        return;
    }
    
    currentResults.forEach((match, index) => {
        const div = document.createElement('div');
        div.className = 'search-result-item';
        div.innerHTML = `
            <span class="search-result-name">${match.name}</span>
            <span class="search-result-tab">${match.group}</span>
        `;
        
        div.addEventListener('mousemove', () => {
            currentSelectedIndex = index;
            updateSearchSelection();
        });
        
        div.addEventListener('click', () => {
            // Switch Tab
            const navItem = document.querySelector(`.nav-item[data-tab="${match.tab}"]`);
            if (navItem) navItem.click();
            
            // Hide dropdown
            pillDropdown.classList.remove('show');
            pillSearchInput.value = '';
            pillDropdownDefault.style.display = 'block';
            pillDropdownResults.style.display = 'none';
            currentSelectedIndex = -1;
            
            // Highlight element
            setTimeout(() => {
                let target = document.getElementById(match.id);
                if (target && target.classList.contains('range-val')) {
                    target = target.closest('.control-item');
                }
                if (target) {
                    // Expand any hidden parents (e.g. padding dropdowns)
                    let parent = target.parentElement;
                    while (parent && parent.id !== 'dashboard-tabs') {
                        if (parent.classList.contains('slider-children') && parent.style.display === 'none') {
                            parent.style.display = 'block';
                            if (parent.parentElement) {
                                const btnSvg = parent.parentElement.querySelector('.link-btn svg');
                                if (btnSvg) btnSvg.style.transform = 'rotate(180deg)';
                            }
                        }
                        parent = parent.parentElement;
                    }
                    
                    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    target.classList.remove('highlight-pulse');
                    // Trigger reflow
                    void target.offsetWidth;
                    target.classList.add('highlight-pulse');
                    
                    // Remove the class after animation completes so it doesn't replay on tab switch
                    setTimeout(() => {
                        if (target && target.classList.contains('highlight-pulse')) {
                            target.classList.remove('highlight-pulse');
                        }
                    }, 3500);
                }
            }, 100);
        });
        pillDropdownResults.appendChild(div);
    });
    
    // Update scroll indicator after injecting results
    setTimeout(updatePerimeterScroll, 10);
});

pagePill.addEventListener('click', (e) => {
    e.stopPropagation();
    pillDropdown.classList.toggle('show');
    if (pillDropdown.classList.contains('show')) {
        pillSearchInput.focus();
    }
});
document.addEventListener('click', (e) => {
    if (!pagePill.contains(e.target) && !pillDropdown.contains(e.target)) {
        pillDropdown.classList.remove('show');
    }
});
document.querySelectorAll('.pill-dropdown-item').forEach(item => {
    item.addEventListener('click', () => {
        const targetTab = item.getAttribute('data-target');
        const navItem = document.querySelector(`.nav-item[data-tab="${targetTab}"]`);
        if (navItem) navItem.click();
    });
});



/* ═══ Slider Fill + Value ═══ */
function updateSlider(el) {
    const min = parseFloat(el.min);
    const max = parseFloat(el.max);
    const val = parseFloat(el.value);
    const pct = ((val - min) / (max - min)) * 100;
    el.style.setProperty('--fill', pct + '%');
    const valId = el.getAttribute('data-val');
    if (valId) document.getElementById(valId).textContent = Math.round(val);
}
document.querySelectorAll('input[type=range]').forEach(el => {
    updateSlider(el);
    el.addEventListener('input', () => updateSlider(el));
});

/* ═══ Card Parallax Tilt ═══ */
document.querySelectorAll('.card').forEach(card => {
    card.addEventListener('mousemove', e => {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        card.style.transform = `perspective(600px) rotateY(${x * 4}deg) rotateX(${-y * 4}deg)`;
    });
    card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(600px) rotateY(0) rotateX(0)';
    });
});

/* ═══ Editor Toggles ═══ */
function showEditor(prefix, type, name) {
    document.getElementById(prefix + '-list').style.display = 'none';
    document.getElementById(prefix + '-editor').style.display = 'block';
    const title = document.getElementById(prefix + '-title');
    if (prefix === 'tpl') title.textContent = `Editing ${type.toUpperCase()}: ${name}`;
    else title.textContent = `Editing: ${name}`;
    if (typeof updateSandboxRect === 'function') setTimeout(updateSandboxRect, 50);
}
function hideEditor(prefix) {
    document.getElementById(prefix + '-list').style.display = 'block';
    document.getElementById(prefix + '-editor').style.display = 'none';
    if (typeof updateSandboxRect === 'function') setTimeout(updateSandboxRect, 50);
}

/* ═══ Custom Styling Toggle ═══ */

/* ═══ Custom Styling Toggle ═══ */
const customToggle = document.querySelector('#custom-toggle input');
if (customToggle) {
    customToggle.addEventListener('change', e => {
        const panel = document.getElementById('custom-panel');
        panel.style.opacity = e.target.checked ? '1' : '0.35';
        panel.style.pointerEvents = e.target.checked ? 'auto' : 'none';
    });
}


/* ═══ Keybind Recording ═══ */
document.querySelectorAll('.keybind-key').forEach(btn => {
    btn.addEventListener('click', function() {
        this.classList.add('recording');
        this.textContent = 'Press key…';
        const handler = (e) => {
            e.preventDefault();
            const name = e.key.length === 1 ? e.key.toUpperCase() : e.key;
            this.textContent = name;
            this.classList.remove('recording');
            window.removeEventListener('keydown', handler);
        };
        window.addEventListener('keydown', handler);
    });
});

/* ═══ Native Sandbox Logic ═══ */


function updateSandboxRect() {
    const editor = document.getElementById('tpl-editor');
    // offsetParent is null if the element or any ancestor is display: none
    if(editor && editor.offsetParent !== null) {
        const rect = document.getElementById('main-panel').getBoundingClientRect();
        ipcRenderer.send('sandbox-cmd', { 
            action: 'update_rect', 
            rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height } 
        });
    } else {
        ipcRenderer.send('sandbox-cmd', { action: 'update_rect', rect: { width: 0 } });
    }
}

// Ensure sandbox rect is accurate whenever the window resizes or we switch to templates tab
window.addEventListener('resize', () => {
    const tabTemplates = document.getElementById('tab-templates');
    const tplEditor = document.getElementById('tpl-editor');
    if (tabTemplates && tabTemplates.classList.contains('active') && 
        tplEditor && tplEditor.style.display !== 'none') {
        updateSandboxRect();
    }
});

// We request to show the sandbox when entering the templates tab or editing
document.querySelectorAll('.nav-item[data-tab="tab-templates"]').forEach(item => {
    item.addEventListener('click', () => {
        setTimeout(updateSandboxRect, 50);
    });
});

ipcRenderer.on('request-sandbox-rect', () => {
    updateSandboxRect();
});

/* ═══════════════════════════════════════════════════════════════
   HALO SANDBOX — State & Rendering
   ═══════════════════════════════════════════════════════════════ */
const HALO_TOOLS = [
    { icon: 'assets/Pandora.svg', name: 'Pandora' },
    { icon: 'assets/browser.svg', name: 'Browser' },
    { icon: 'assets/file explorer.svg', name: 'Files' },
    { icon: 'assets/screenshot.svg', name: 'Snip' },
    { icon: 'assets/night light.svg', name: 'Night Light' },
    { icon: 'assets/mute.svg', name: 'Mute' },
    { icon: 'assets/brightness.svg', name: 'Brightness' },
    { icon: 'assets/empty recycle bin.svg', name: 'Empty Trash' },
    { icon: 'assets/search.svg', name: 'Search' },
    { icon: 'assets/task manager.svg', name: 'Tasks' },
    { icon: 'assets/sticky notes.svg', name: 'Sticky Notes' },
    { icon: 'assets/power.svg', name: 'Power' },
    { icon: 'assets/toggle grid.svg', name: 'Toggle Grid' },
    { icon: 'assets/calculator.svg', name: 'Calculator' },
    { icon: 'assets/terminal.svg', name: 'Terminal' },
    { icon: 'assets/notepad.svg', name: 'Notepad' },
    { icon: 'assets/prev.svg', name: 'Prev Media' },
    { icon: 'assets/next.svg', name: 'Next Media' },
    { icon: 'assets/bluetooth on.svg', name: 'Bluetooth' },
    { icon: 'assets/wifi on.svg', name: 'Wi-Fi' },
    { icon: 'assets/mic on.svg', name: 'Microphone' },
    { icon: 'assets/lock.svg', name: 'Lock PC' },
    { icon: 'assets/sleep.svg', name: 'Sleep' },
    { icon: 'assets/clipboard.svg', name: 'Clipboard' },
    { icon: 'assets/task view.svg', name: 'Task View' },
    { icon: 'assets/emoji picker.svg', name: 'Emoji Picker' },
    { icon: 'assets/play.svg', name: 'Play/Pause' },
    { icon: 'assets/windows settings.svg', name: 'Windows Settings' },
    { icon: 'assets/windows defender.svg', name: 'Windows Defender' }
];

const MAX_LAYERS = 9;
const MAX_SLICES = 8;

// State: 9 layers pre-created, first layer has Pandora slice
let haloLayers = Array.from({ length: 9 }, (_, i) => ({
    slices: i === 0 ? [{ icon: 'assets/Pandora.svg', name: 'Pandora' }] : [{ icon: '', name: '' }]
}));
let haloCurrentLayer = 0;
let haloCmdSliceIndex = -1;
let haloCmdPage = 0;
const HALO_TOOLS_PER_PAGE = 10;
let haloDragIndex = -1; // drag source slice index

function getCurrentLayer() {
    return haloLayers[haloCurrentLayer];
}

/* ── SVG arc helpers ── */
function polarToCart(cx, cy, r, angleDeg) {
    const rad = (angleDeg - 90) * Math.PI / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(cx, cy, outerR, innerR, startAngle, endAngle) {
    const gap = 1.2;
    const s = startAngle + gap / 2;
    const e = endAngle - gap / 2;
    if (e <= s) return '';
    const outerStart = polarToCart(cx, cy, outerR, s);
    const outerEnd = polarToCart(cx, cy, outerR, e);
    const innerStart = polarToCart(cx, cy, innerR, e);
    const innerEnd = polarToCart(cx, cy, innerR, s);
    const largeArc = (e - s) > 180 ? 1 : 0;
    return [
        'M', outerStart.x, outerStart.y,
        'A', outerR, outerR, 0, largeArc, 1, outerEnd.x, outerEnd.y,
        'L', innerStart.x, innerStart.y,
        'A', innerR, innerR, 0, largeArc, 0, innerEnd.x, innerEnd.y,
        'Z'
    ].join(' ');
}

/* ── Render the SVG radial ── */
function renderHaloRadial() {
    const svg = document.getElementById('halo-radial-svg');
    if (!svg) return;
    
    // Apply theme colors to the wrapper
    const wrap = svg.closest('.halo-radial-wrap');
    if (wrap) {
        const currentTheme = window.dashboardConfig?.halo?.theme || 'Dark';
        let sliceBg, sliceBorder, emptyBg, emptyBorder, hubBg, labelColor;
        if (currentTheme === 'Light') {
            sliceBg = 'transparent';
            sliceBorder = 'transparent';
            emptyBg = 'transparent';
            emptyBorder = 'rgba(15, 15, 22, 0.15)'; // faint dashed for editor
            hubBg = 'rgba(245, 245, 250, 0.95)';
            labelColor = 'rgba(15, 15, 22, 0.6)';
            wrap.style.setProperty('--ring-bg', 'rgba(245, 245, 250, 0.9)');
            wrap.style.setProperty('--ring-border', 'rgba(15, 15, 22, 0.1)');
        } else if (currentTheme === 'Glass') {
            sliceBg = 'transparent';
            sliceBorder = 'transparent';
            emptyBg = 'transparent';
            emptyBorder = 'rgba(255, 255, 255, 0.15)';
            hubBg = 'rgba(255, 255, 255, 0.1)';
            labelColor = 'rgba(255, 255, 255, 0.7)';
            wrap.style.setProperty('--ring-bg', 'rgba(255, 255, 255, 0.1)');
            wrap.style.setProperty('--ring-border', 'rgba(255, 255, 255, 0.2)');
        } else if (currentTheme === 'Gray') {
            sliceBg = 'transparent';
            sliceBorder = 'transparent';
            emptyBg = 'transparent';
            emptyBorder = 'rgba(255, 255, 255, 0.15)';
            hubBg = '#282828';
            labelColor = 'rgba(255, 255, 255, 0.6)';
            wrap.style.setProperty('--ring-bg', 'rgba(40, 40, 40, 0.72)');
            wrap.style.setProperty('--ring-border', 'rgba(255, 255, 255, 0.12)');
        } else { // Dark or Desktop
            sliceBg = 'transparent';
            sliceBorder = 'transparent';
            emptyBg = 'transparent';
            emptyBorder = 'rgba(255, 255, 255, 0.1)';
            hubBg = '#0a0a0c';
            labelColor = 'rgba(255, 255, 255, 0.45)';
            // Matches Python app: QColor(10, 10, 14, 185) with QColor(255, 255, 255, 30) pen
            wrap.style.setProperty('--ring-bg', 'rgba(10, 10, 14, 0.72)');
            wrap.style.setProperty('--ring-border', 'rgba(255, 255, 255, 0.12)');
        }

        wrap.style.setProperty('--slice-bg', sliceBg);
        wrap.style.setProperty('--slice-border', sliceBorder);
        wrap.style.setProperty('--empty-bg', emptyBg);
        wrap.style.setProperty('--empty-border', emptyBorder);
        wrap.style.setProperty('--hub-bg', hubBg);
        wrap.style.setProperty('--label-color', labelColor);
        // Force SVG assets which are natively dark to pure white if on Dark/Glass themes, or pure black if Light
        wrap.style.setProperty('--icon-filter', currentTheme === 'Light' ? 'brightness(0)' : 'brightness(0) invert(1)');
    }

    // Preserve defs (glow filter)
    const defs = svg.querySelector('defs');
    svg.innerHTML = '';
    if (defs) svg.appendChild(defs);

    const layer = getCurrentLayer();
    const slices = layer.slices;
    const n = slices.length;
    const cx = 250, cy = 250;
    const outerR = 240, innerR = 96;
    const anglePerSlice = 360 / n;
    const ns = 'http://www.w3.org/2000/svg';

    // Outer glow ring
    const outerCircle = document.createElementNS(ns, 'circle');
    outerCircle.setAttribute('cx', cx);
    outerCircle.setAttribute('cy', cy);
    outerCircle.setAttribute('r', outerR + 4);
    outerCircle.setAttribute('class', 'halo-outer-ring');
    svg.appendChild(outerCircle);

    // Single continuous background Donut (matches Python app)
    const bgDonut = document.createElementNS(ns, 'path');
    bgDonut.setAttribute('d', `M ${cx} ${cy - outerR} A ${outerR} ${outerR} 0 1 1 ${cx} ${cy + outerR} A ${outerR} ${outerR} 0 1 1 ${cx} ${cy - outerR} Z M ${cx} ${cy - innerR} A ${innerR} ${innerR} 0 1 0 ${cx} ${cy + innerR} A ${innerR} ${innerR} 0 1 0 ${cx} ${cy - innerR} Z`);
    bgDonut.style.fill = 'var(--ring-bg)';
    bgDonut.style.stroke = 'var(--ring-border)';
    bgDonut.style.strokeWidth = '1.5';
    svg.appendChild(bgDonut);

    for (let i = 0; i < n; i++) {
        // Offset by half a slice so the slice center aligns with the exact angle
        // This matches the Python app's atan2 top-center orientation.
        const startAngle = (i * anglePerSlice) - (anglePerSlice / 2);
        const endAngle = ((i + 1) * anglePerSlice) - (anglePerSlice / 2);
        const midAngle = i * anglePerSlice;
        const slice = slices[i];
        const isEmpty = !slice.name;

        const g = document.createElementNS(ns, 'g');
        g.style.cursor = 'pointer';
        g.dataset.sliceIndex = i;
        g.setAttribute('class', 'halo-slice-group');

        const bgPath = document.createElementNS(ns, 'path');
        bgPath.setAttribute('d', describeArc(cx, cy, outerR, innerR, startAngle, endAngle));
        bgPath.setAttribute('class', 'halo-slice-base' + (isEmpty ? ' empty' : ''));
        g.appendChild(bgPath);

        const path = document.createElementNS(ns, 'path');
        path.setAttribute('d', describeArc(cx, cy, outerR, innerR, startAngle, endAngle));
        path.setAttribute('class', 'halo-slice-path' + (isEmpty ? ' empty' : ''));
        path.dataset.sliceIndex = i;

        // Right click → delete slice
        path.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            deleteSlice(i);
        });
        
        let dragMoved = false;

        // Drag-and-drop
        path.setAttribute('draggable', 'false'); // SVG doesn't use HTML drag
        path.addEventListener('mousedown', (e) => {
            if (e.button !== 0) return;
            haloDragIndex = i;
            dragMoved = false;
            path.classList.add('dragging');
            g.classList.add('dragging');
            // Bring group to front to avoid occlusion when scaled
            svg.appendChild(g);
        });
        path.addEventListener('mousemove', () => {
            if (haloDragIndex === i) dragMoved = true;
        });
        path.addEventListener('mouseenter', () => {
            if (haloDragIndex >= 0 && haloDragIndex !== i) {
                path.classList.add('drag-over');
                g.classList.add('drag-over');
            }
        });
        path.addEventListener('mouseleave', () => {
            path.classList.remove('drag-over');
            g.classList.remove('drag-over');
        });
        path.addEventListener('mouseup', (e) => {
            if (e.button === 0 && haloDragIndex === i && !dragMoved) {
                // If it was a clean click without dragging
                openCmdBank(i);
            } else if (haloDragIndex >= 0 && haloDragIndex !== i) {
                swapSlices(haloDragIndex, i);
            }
            haloDragIndex = -1;
            svg.querySelectorAll('.dragging, .drag-over').forEach(el => {
                el.classList.remove('dragging', 'drag-over');
            });
        });
        g.appendChild(path);

        // Label position
        const labelR = (outerR + innerR) / 2;
        const labelPos = polarToCart(cx, cy, labelR, midAngle);

        if (!isEmpty) {
            let displayIcon = slice.icon || '';
            // Force mapping to SVG from HALO_TOOLS if matching name
            const matchedTool = HALO_TOOLS.find(t => t.name === slice.name);
            if (matchedTool && matchedTool.icon) {
                displayIcon = matchedTool.icon;
                slice.icon = displayIcon; // upgrade config
            } else if (displayIcon && !displayIcon.includes('.svg') && !displayIcon.startsWith('data:')) {
                displayIcon = `assets/${displayIcon}.svg`;
            }

            if (displayIcon && (displayIcon.endsWith('.svg') || displayIcon.startsWith('data:') || displayIcon.includes('/'))) {
                const iconImg = document.createElementNS(ns, 'image');
                iconImg.setAttribute('x', labelPos.x - 12);
                iconImg.setAttribute('y', labelPos.y - 18);
                iconImg.setAttribute('width', '24');
                iconImg.setAttribute('height', '24');
                iconImg.setAttribute('class', 'halo-slice-icon-img');
                iconImg.setAttribute('href', displayIcon);
                iconImg.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', displayIcon);
                const isBase64 = displayIcon.startsWith('data:');
                if (!isBase64) {
                    iconImg.style.filter = 'var(--icon-filter)';
                } else if (window.getAppConfig().halo.blend_app_icons === true) {
                    iconImg.style.filter = 'grayscale(100%) brightness(150%) contrast(120%)';
                }
                g.appendChild(iconImg);
            } else {
                const iconText = document.createElementNS(ns, 'text');
                iconText.setAttribute('x', labelPos.x);
                iconText.setAttribute('y', labelPos.y - 6);
                iconText.setAttribute('class', 'halo-slice-icon');
                iconText.textContent = displayIcon;
                g.appendChild(iconText);
            }

            const nameText = document.createElementNS(ns, 'text');
            nameText.setAttribute('x', labelPos.x);
            nameText.setAttribute('y', labelPos.y + 14);
            nameText.setAttribute('class', 'halo-slice-label');
            nameText.textContent = slice.name.length > 9 ? slice.name.substring(0, 8) + '…' : slice.name;
            g.appendChild(nameText);
        } else {
            const plus = document.createElementNS(ns, 'text');
            plus.setAttribute('x', labelPos.x);
            plus.setAttribute('y', labelPos.y);
            plus.setAttribute('class', 'halo-slice-label');
            plus.setAttribute('style', 'font-size:22px; fill:var(--text-3);');
            plus.textContent = '+';
            g.appendChild(plus);
        }

        svg.appendChild(g);
    }

    // Global mouseup to cancel drag
    document.addEventListener('mouseup', () => {
        if (haloDragIndex >= 0) {
            haloDragIndex = -1;
            svg.querySelectorAll('.dragging, .drag-over').forEach(el => {
                el.classList.remove('dragging', 'drag-over');
            });
        }
    }, { once: true });

    // Update center hub
    document.getElementById('halo-center-num').textContent = haloCurrentLayer + 1;
    document.getElementById('halo-add-slice').disabled = slices.length >= MAX_SLICES;
}

/* ── Slice management ── */
function deleteSlice(index) {
    const layer = getCurrentLayer();
    if (layer.slices.length <= 1) {
        // Can't delete the last slice, just clear it
        layer.slices[0] = { icon: '', name: '' };
    } else {
        layer.slices.splice(index, 1);
    }
    refreshHalo();
}

function swapSlices(a, b) {
    const slices = getCurrentLayer().slices;
    [slices[a], slices[b]] = [slices[b], slices[a]];
    refreshHalo();
}

function addHaloSlice() {
    const layer = getCurrentLayer();
    if (layer.slices.length >= MAX_SLICES) return;
    layer.slices.push({ icon: '', name: '' });
    refreshHalo();
}

/* ── Layer management (center hub) ── */
function updateLayerDropdown() {
    const dd = document.getElementById('halo-layer-dropdown');
    if (!dd) return;
    dd.innerHTML = '';
    for (let i = 0; i < 9; i++) {
        const opt = document.createElement('div');
        opt.textContent = 'Layer ' + (i + 1);
        if (i === haloCurrentLayer) opt.classList.add('active');
        opt.addEventListener('click', (e) => {
            e.stopPropagation();
            haloCurrentLayer = i;
            dd.classList.remove('show');
            refreshHalo();
        });
        dd.appendChild(opt);
    }
}


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
                    tools: l.slices.map(s => {
                        if (!s.name) return { id: '', icon: '', label: '' };
                        if (s.path) {
                            return { id: s.path, icon: s.icon, label: s.name };
                        }
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
    closeCmdBank();
    haloLayers = Array.from({ length: 9 }, (_, i) => {
        if (menus[i] && menus[i].tools && menus[i].tools.length > 0) {
            return {
                slices: menus[i].tools.slice(0, MAX_SLICES).map(t => {
                    const isPath = t.id && (t.id.includes('/') || t.id.includes('\\') || t.id.includes(':'));
                    const sliceObj = {
                        icon: t.icon || 'assets/launcher.svg',
                        name: t.label,
                        path: isPath ? t.id : ''
                    };
                    // Always re-extract icons for path-based tools.
                    // The Python halo uses IconExtractor.get_icon_pixmap(tid, 32)
                    // which resolves .lnk targets via win32com — our app:getFileIcon
                    // handler now does the same. Previously cached base64 may be a
                    // stale generic document icon from before the fix.
                    if (isPath) {
                        ipcRenderer.invoke('app:getFileIcon', t.id).then(extractedIcon => {
                            if (extractedIcon && !extractedIcon.startsWith('ERROR:')) {
                                sliceObj.icon = extractedIcon;
                                renderHaloRadial();
                            }
                        }).catch(err => console.error("On-the-fly icon extract failed:", err));
                    }
                    return sliceObj;
                })
            };
        }
        return { slices: [{ icon: '', name: '' }] };
    });
    updateLayerDropdown();
    renderHaloRadial();
    window.isUpdatingFromPython = false;
};


function switchHaloLayer(index) {
    haloCurrentLayer = index;
    refreshHalo();
}

/* ── Command Bank ── */
/* ── Command Bank ── */
function openCmdBank(sliceIndex) {
    try {
        haloCmdSliceIndex = sliceIndex;
        const overlay = document.getElementById('halo-cmd-overlay');
        const slice = getCurrentLayer().slices[sliceIndex];

        // Detect which page has the currently assigned tool and open directly to it
        let targetPage = 0;
        const currentToolName = (slice && slice.name) ? slice.name : '';
        if (currentToolName) {
            const activeIdx = HALO_TOOLS.findIndex(t => t.name === currentToolName);
            if (activeIdx !== -1) {
                targetPage = Math.floor(activeIdx / HALO_TOOLS_PER_PAGE);
            }
        }
        haloCmdPage = targetPage;

        renderCmdBankGrid(sliceIndex);

        const rmBtn = document.getElementById('halo-cmd-remove');
        rmBtn.style.display = (slice && slice.name) ? 'flex' : 'none';
        overlay.classList.add('show');
    } catch (err) {
        console.error("Error opening Command Bank:", err);
    }
}

function renderCmdBankGrid(sliceIndex) {
    try {
        const grid = document.getElementById('halo-cmd-grid');
        const pagContainer = document.getElementById('halo-cmd-pagination');
        const slice = getCurrentLayer().slices[sliceIndex];

        grid.innerHTML = '';

        const startIdx = haloCmdPage * HALO_TOOLS_PER_PAGE;
        const endIdx = Math.min(startIdx + HALO_TOOLS_PER_PAGE, HALO_TOOLS.length);
        const pageTools = HALO_TOOLS.slice(startIdx, endIdx);

        pageTools.forEach(tool => {
            const item = document.createElement('div');
            item.className = 'halo-cmd-item';
            if (slice && slice.name === tool.name) item.classList.add('active');
            const iconHtml = tool.icon.endsWith('.svg') ? renderSvgIcon(tool.icon, 24, 24) : tool.icon;
            item.innerHTML = `<span class="cmd-icon">${iconHtml}</span><span class="cmd-name">${tool.name}</span>`;
            item.addEventListener('click', () => assignTool(sliceIndex, tool));
            grid.appendChild(item);
        });

        // Animate the items sliding and fading in (staggered)
        Array.from(grid.children).forEach((item, idx) => {
            item.animate([
                { opacity: 0, transform: 'translateY(8px) scale(0.96)' },
                { opacity: 1, transform: 'translateY(0) scale(1)' }
            ], {
                duration: 250,
                delay: idx * 15,
                easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)',
                fill: 'both'
            });
        });

        // Render pagination dots
        pagContainer.innerHTML = '';
        const totalPages = Math.ceil(HALO_TOOLS.length / HALO_TOOLS_PER_PAGE);
        if (totalPages > 1) {
            for (let p = 0; p < totalPages; p++) {
                const dot = document.createElement('span');
                dot.className = 'dot';
                if (p === haloCmdPage) dot.classList.add('active');
                dot.addEventListener('click', (e) => {
                    e.stopPropagation();
                    haloCmdPage = p;
                    renderCmdBankGrid(sliceIndex);
                });
                pagContainer.appendChild(dot);
            }
        }
    } catch (err) {
        console.error("Error rendering Command Bank Grid:", err);
    }
}

function closeCmdBank() {
    document.getElementById('halo-cmd-overlay').classList.remove('show');
    haloCmdSliceIndex = -1;
}

function assignTool(sliceIndex, tool) {
    getCurrentLayer().slices[sliceIndex] = { icon: tool.icon, name: tool.name };
    closeCmdBank();
    refreshHalo();
}

function removeToolFromSlice() {
    if (haloCmdSliceIndex < 0) return;
    deleteSlice(haloCmdSliceIndex);
    closeCmdBank();
}

async function selectCustomApp() {
    if (haloCmdSliceIndex < 0) return;
    try {
        const filePath = await ipcRenderer.invoke('dialog:openApp');
        if (!filePath) return; // cancelled
        
        // Extract display name from filepath
        const parts = filePath.split(/[\\/]/);
        let fileName = parts[parts.length - 1];
        if (fileName.includes('.')) {
            const dotParts = fileName.split('.');
            dotParts.pop();
            fileName = dotParts.join('.');
        }
        const displayName = fileName.charAt(0).toUpperCase() + fileName.slice(1);
        
        let iconUrl = 'assets/launcher.svg';
        try {
            const extractedIcon = await ipcRenderer.invoke('app:getFileIcon', filePath);
            if (extractedIcon && !extractedIcon.startsWith('ERROR:')) {
                iconUrl = extractedIcon;
            }
        } catch (err) {
            console.error("Failed to extract file icon:", err);
        }
        
        // Assign to current slice
        getCurrentLayer().slices[haloCmdSliceIndex] = {
            icon: iconUrl,
            name: displayName,
            path: filePath
        };
        closeCmdBank();
        refreshHalo();
    } catch (err) {
        console.error("Error picking custom app:", err);
    }
}

/* ── Wire up event listeners ── */
document.getElementById('halo-add-slice')?.addEventListener('click', addHaloSlice);
document.getElementById('halo-cmd-close')?.addEventListener('click', closeCmdBank);
document.getElementById('halo-cmd-remove')?.addEventListener('click', removeToolFromSlice);
document.getElementById('halo-cmd-custom-app')?.addEventListener('click', selectCustomApp);
document.getElementById('halo-cmd-overlay')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeCmdBank();
});

let lastCmdScrollTime = 0;
const CMD_SCROLL_COOLDOWN = 180; // ms
document.getElementById('halo-cmd-overlay')?.addEventListener('wheel', (e) => {
    e.preventDefault();
    const now = Date.now();
    if (now - lastCmdScrollTime < CMD_SCROLL_COOLDOWN) return;
    
    const totalPages = Math.ceil(HALO_TOOLS.length / HALO_TOOLS_PER_PAGE);
    if (totalPages <= 1) return;
    
    if (Math.abs(e.deltaY) > 5) {
        if (e.deltaY > 0) {
            haloCmdPage = (haloCmdPage + 1) % totalPages;
        } else {
            haloCmdPage = (haloCmdPage - 1 + totalPages) % totalPages;
        }
        lastCmdScrollTime = now;
        renderCmdBankGrid(haloCmdSliceIndex);
    }
}, { passive: false });

// Layer selector in center hub
const layerTrigger = document.getElementById('halo-layer-trigger');
const layerDD = document.getElementById('halo-layer-dropdown');
if (layerTrigger && layerDD) {
    layerTrigger.addEventListener('click', (e) => {
        e.stopPropagation();
        layerDD.classList.toggle('show');
    });
    document.addEventListener('click', () => layerDD.classList.remove('show'));
}

// Scroll to switch layers in center hub
const haloCenterHub = document.querySelector('.halo-center-hub');
if (haloCenterHub) {
    haloCenterHub.addEventListener('wheel', (e) => {
        e.preventDefault();
        if (haloLayers.length <= 1) return;
        if (e.deltaY > 0) {
            haloCurrentLayer = (haloCurrentLayer - 1 + haloLayers.length) % haloLayers.length;
        } else {
            haloCurrentLayer = (haloCurrentLayer + 1) % haloLayers.length;
        }
        refreshHalo();
    });
}

// Initial render
refreshHalo();

/* ═══════════════════════════════════════════════════════════════
   HUB HUD SANDBOX — Centralized State, Dynamic Grid & Settings mapping
   ═══════════════════════════════════════════════════════════════ */
const HUB_MODULES = {
    'default': { name: 'Pandora Logo', icon: 'assets/Pandora.svg', color: '#ffffff', description: 'Quick access and launch controls for the core Pandora App and Dashboard services.' },
    'media': { name: 'Media Player', icon: 'assets/music.svg', color: '#BD93F9', description: 'System-wide music controller and dynamic metadata visualizer.' },
    'time': { name: 'Clock', icon: 'assets/clock.svg', color: '#8BE9FD', description: 'Elegant time display with support for multiple clock modes and active timezone mappings.' },
    'stopwatch': { name: 'Stopwatch', icon: 'assets/stopwatch.svg', color: '#FF79C6', description: 'High-precision stopwatch module. No configuration required.' },
    'timer': { name: 'Timer', icon: 'assets/timer.svg', color: '#FFB86C', description: 'Visual countdown timer featuring configurable alarms and custom presets.' },
    'weather': { name: 'Weather', icon: 'assets/sun.svg', color: '#F1FA8C', description: 'Local meteorological updates, temperature indicators, and weather API provider controls.' },
    'launcher': { name: 'Launcher', icon: 'assets/launcher.svg', color: '#50FA7B', description: 'Quick-launch application grid with custom size overlays.' }
};

let hubSlots = [
    { type: 'default', settings: {} },
    { type: 'media', settings: { art_style: 'Gaussian Blur', effect_strength: 25, visualizer: 'None', mosaic_shape: 'Square', show_timeline: true, show_title: true, show_controls: true } },
    { type: 'time', settings: { clock_mode: 'digital', active_clock_tz: '', active_clock_label: 'LOCAL TIME', format_24h: false, show_date: true, show_seconds: true, world_clocks: [] } },
    { type: 'stopwatch', settings: {} },
    { type: 'timer', settings: { default_duration: 300, auto_repeat: false, sound_enabled: true, presets: [60, 180, 300, 600, 1500] } },
    { type: 'weather', settings: { provider: 'free', location: '', use_metric: true, api_key: '' } },
    { type: 'launcher', settings: { show_labels: true, icon_size: 24, items: [{ label: 'Browser', path: 'C:\\Program Files\\Internet Explorer\\iexplore.exe', icon_mode: 'auto', icon: '' }] } },
    null,
    null
];

let selectedHubSlotIndex = -1;


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
            
            const iconHtml = mod.icon.endsWith('.svg') ? renderSvgIcon(mod.icon, 24, 24, "margin-bottom:8px; display:block;") : `<span class="mod-icon" style="font-size:24px; margin-bottom:8px; display:block;">${mod.icon}</span>`;
            slotEl.innerHTML = `
                ${iconHtml}
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
            if (!s.id) s.id = crypto.randomUUID();
            return { id: s.id, type: s.type, name: mod.name, icon: mod.icon, settings: s.settings };
        });
        window.sendAppUpdate();
    }
}

window.updateHubLayersFromConfig = function(layers) {
    window.isUpdatingHubFromPython = true;
    for(let i=0; i<9; i++) {
        if (layers[i]) {
            hubSlots[i] = { id: layers[i].id, type: layers[i].type, settings: layers[i].settings || {} };
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

function renderHubGridOld() {
    const container = document.getElementById('hub-grid-container');
    if (!container) return;
    container.innerHTML = '';

    hubSlots.forEach((slot, i) => {
        const slotEl = document.createElement('div');
        const isSelected = i === selectedHubSlotIndex;
        
        if (slot) {
            const mod = HUB_MODULES[slot.type];
            slotEl.className = `hub-slot filled${isSelected ? ' selected' : ''}`;
            slotEl.style.setProperty('--slot-glow-color', mod.color + '30'); // Premium soft glow
            slotEl.style.borderColor = isSelected ? mod.color : 'rgba(255,255,255,0.03)';
            
            slotEl.innerHTML = `
                <span class="mod-icon" style="font-size:24px; margin-bottom:8px; display:block;">${mod.icon}</span>
                <span class="mod-name" style="color:${mod.color};">${mod.name}</span>
                <span class="slot-n">Slot ${i + 1}</span>
                <button class="del-btn" title="Remove Module">×</button>
            `;
            
            // Delete button listener
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

        slotEl.addEventListener('click', () => {
            selectHubSlot(i);
        });

        container.appendChild(slotEl);
    });
}

function saveHubConfig() {
    if (window.getAppConfig && window.sendAppUpdate) {
        const cfg = window.getAppConfig();
        if (!cfg.hub_config) cfg.hub_config = {};
        cfg.hub_config.layers = hubSlots;
        window.sendAppUpdate('hub_config', cfg.hub_config);
    }
}

function deleteHubSlot(index) {
    hubSlots[index] = null;
    if (selectedHubSlotIndex === index) {
        selectedHubSlotIndex = -1;
        document.getElementById('widget-settings-panel').style.display = 'none';
    }
    saveHubConfig();
    renderHubGrid();
}

function selectHubSlot(index) {
    selectedHubSlotIndex = index;
    renderHubGrid();
    openWidgetSettings(index);
}

function assignHubModule(index, type) {
    const defaultSettings = {
        pandora: {},
        media: { art_style: 'Gaussian Blur', effect_strength: 25, visualizer: 'None', mosaic_shape: 'Square', show_timeline: true, show_title: true, show_controls: true },
        clock: { clock_mode: 'digital', active_clock_tz: '', active_clock_label: 'LOCAL TIME', format_24h: false, show_date: true, show_seconds: true },
        stopwatch: {},
        timer: { default_duration: 300, auto_repeat: false },
        weather: { provider: 'free', location: '', use_metric: true, api_key: '' },
        launcher: { show_labels: true, icon_size: 24 }
    };

    hubSlots[index] = {
        type: type,
        settings: { ...defaultSettings[type] }
    };
    
    selectedHubSlotIndex = index;
    saveHubConfig();
    renderHubGrid();
    openWidgetSettings(index);
}

function initWidgetCustomSelects(container, index) {
    const selects = container.querySelectorAll('select');
    selects.forEach(sel => {
        if (sel.parentNode.classList.contains('custom-select')) return;
        
        const wrapper = document.createElement('div');
        wrapper.className = 'custom-select';
        sel.parentNode.insertBefore(wrapper, sel);
        wrapper.appendChild(sel);

        const selectedDiv = document.createElement('div');
        selectedDiv.className = 'select-selected';
        selectedDiv.innerHTML = sel.options[sel.selectedIndex].innerHTML;
        wrapper.appendChild(selectedDiv);

        const optionsDiv = document.createElement('div');
        optionsDiv.className = 'select-items select-hide';
        
        for (let i = 0; i < sel.options.length; i++) {
            const opt = document.createElement('div');
            opt.innerHTML = sel.options[i].innerHTML;
            if (i === sel.selectedIndex) opt.classList.add('same-as-selected');
            if (sel.options[i].hidden || sel.options[i].disabled) opt.style.display = 'none';
            
            opt.addEventListener('click', function(e) {
                if (sel.options[i].disabled || sel.options[i].hidden) return;
                sel.selectedIndex = i;
                sel.dispatchEvent(new Event('change'));
                selectedDiv.innerHTML = this.innerHTML;
                
                const s = this.parentNode.querySelectorAll('.same-as-selected');
                for (let k = 0; k < s.length; k++) {
                    s[k].classList.remove('same-as-selected');
                }
                this.classList.add('same-as-selected');
                selectedDiv.click();
            });
            optionsDiv.appendChild(opt);
        }
        wrapper.appendChild(optionsDiv);
        
        selectedDiv.addEventListener('click', function(e) {
            e.stopPropagation();
            closeAllSelect(this);
            this.nextSibling.classList.toggle('select-hide');
            this.classList.toggle('select-arrow-active');
            wrapper.classList.toggle('active');
        });
    });
}

function openWidgetSettings(index) {
    const panel = document.getElementById('widget-settings-panel');
    const title = document.getElementById('widget-settings-title');
    const content = document.getElementById('widget-settings-content');
    if (!panel || !title || !content) return;

    panel.style.display = 'block';
    content.innerHTML = '';
    
    // Smooth transition scroll to settings panel
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    const slot = hubSlots[index];
    if (slot) {
        const mod = HUB_MODULES[slot.type];
        const iconHtml = mod.icon.endsWith('.svg') ? renderSvgIcon(mod.icon, 24, 24, `filter: drop-shadow(0 0 2px ${mod.color});`) : mod.icon;
        title.innerHTML = `<span style="display:inline-flex; align-items:center; gap:8px;">${iconHtml} Module Settings: <span style="color:${mod.color}">${mod.name}</span></span>`;
        
        let html = `<div class="flex-col gap-16" style="width:100%;">`;
        html += `<div style="font-size:12px; color:var(--text-3); margin-bottom:8px; line-height:1.4;">${mod.description}</div>`;

        if (slot.type === 'pandora') {
            html += `
                <div style="font-size:12.5px; color:var(--text-2); padding:8px 0; display:flex; align-items:center; gap:8px;">
                    <span style="color:var(--accent-hub);">●</span> Core Processes active. No additional configuration needed.
                </div>
            `;
        } else if (slot.type === 'media') {
            const isMosaic = slot.settings.art_style === '8-Bit Mosaic';
            const isFerro = slot.settings.art_style === 'Liquid Ferrofluid';
            html += `
                <div class="control-row">
                    <span class="control-label">Art Style</span>
                    <select id="setting-media-artstyle">
                        <option value="Gaussian Blur" ${slot.settings.art_style === 'Gaussian Blur' ? 'selected' : ''}>Gaussian Blur</option>
                        <option value="8-Bit Mosaic" ${slot.settings.art_style === '8-Bit Mosaic' ? 'selected' : ''}>8-Bit Mosaic</option>
                        <option value="Liquid Ferrofluid" ${slot.settings.art_style === 'Liquid Ferrofluid' ? 'selected' : ''}>Liquid Ferrofluid (3D)</option>
                        <option value="None" ${slot.settings.art_style === 'None' ? 'selected' : ''}>None</option>
                    </select>
                </div>
            `;
            
            if (isMosaic) {
                html += `
                    <div class="control-row">
                        <span class="control-label">Mosaic Shape</span>
                        <select id="setting-media-mosaicshape">
                            <option value="Square" ${slot.settings.mosaic_shape === 'Square' ? 'selected' : ''}>Square</option>
                            <option value="Rounded" ${slot.settings.mosaic_shape === 'Rounded' ? 'selected' : ''}>Rounded</option>
                        </select>
                    </div>
                `;
            }

            html += `
                <div class="control-item mt-8">
                    <div class="control-row">
                        <span class="control-label">${isMosaic ? 'Pixel Mosaic Scale' : 'Blur Intensity'}</span>
                        <span class="range-val" id="v-media-strength">${slot.settings.effect_strength}</span>
                    </div>
                    <input type="range" min="0" max="100" value="${slot.settings.effect_strength}" data-val="v-media-strength" id="setting-media-strength">
                </div>
                <div class="control-row">
                    <span class="control-label">Visualizer EQ Type</span>
                    <select id="setting-media-visualizer">
                        <option value="None" ${slot.settings.visualizer === 'None' ? 'selected' : ''}>None</option>
                        <option value="Edge Ring EQ" ${slot.settings.visualizer === 'Edge Ring EQ' ? 'selected' : ''}>Edge Ring EQ</option>
                        ${isMosaic ? `
                        <option value="Reactive Voxels" ${slot.settings.visualizer === 'Reactive Voxels' ? 'selected' : ''}>Reactive Voxels</option>
                        ` : ''}
                    </select>
                </div>
                <div class="control-row" style="flex-direction: column; align-items: flex-start; margin-top: 10px;">
                    <span class="control-label" style="margin-bottom: 8px;">Animation Style</span>
                    <div class="preset-radio-group" id="setting-media-animation">
                        ${['Ambient', 'Relaxed', 'Balanced', 'Reactive', 'Lively'].map(style => `
                            <label class="preset-radio-label">
                                <input type="radio" name="anim_style" value="${style}" ${slot.settings.animation_style === style || (!slot.settings.animation_style && style === 'Balanced') ? 'checked' : ''}>
                                <span>${style}</span>
                            </label>
                        `).join('')}
                    </div>
                </div>
                <div class="control-row">
                    <span class="control-label">Show Music Timeline Arc</span>
                    <label class="switch">
                        <input type="checkbox" id="setting-media-showtimeline" ${slot.settings.show_timeline ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="control-row">
                    <span class="control-label">Show Track Title text</span>
                    <label class="switch">
                        <input type="checkbox" id="setting-media-showtitle" ${slot.settings.show_title ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="control-row">
                    <span class="control-label">Show Media Controls HUD</span>
                    <label class="switch">
                        <input type="checkbox" id="setting-media-showcontrols" ${slot.settings.show_controls ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
            `;
        } else if (slot.type === 'clock') {
            html += `
                <div class="control-row">
                    <span class="control-label">Clock Visual Mode</span>
                    <select id="setting-clock-mode">
                        <option value="digital" ${slot.settings.clock_mode === 'digital' ? 'selected' : ''}>Digital Clock</option>
                        <option value="analog" ${slot.settings.clock_mode === 'analog' ? 'selected' : ''}>Analog Chronograph</option>
                    </select>
                </div>
                <div class="control-row">
                    <span class="control-label">Active Timezone</span>
                    <select id="setting-clock-tz">
                        <option value="" ${slot.settings.active_clock_tz === '' ? 'selected' : ''}>Local System Time</option>
                        <option value="America/New_York" ${slot.settings.active_clock_tz === 'America/New_York' ? 'selected' : ''}>New York (EST)</option>
                        <option value="Europe/London" ${slot.settings.active_clock_tz === 'Europe/London' ? 'selected' : ''}>London (GMT)</option>
                        <option value="Asia/Tokyo" ${slot.settings.active_clock_tz === 'Asia/Tokyo' ? 'selected' : ''}>Tokyo (JST)</option>
                        <option value="Asia/Kolkata" ${slot.settings.active_clock_tz === 'Asia/Kolkata' ? 'selected' : ''}>Kolkata (IST)</option>
                    </select>
                </div>
                <div class="control-row">
                    <span class="control-label">Custom Display Label</span>
                    <input type="text" id="setting-clock-label" value="${slot.settings.active_clock_label}" class="keybind-key" style="text-align:left; padding:8px 12px; width:50%; font-family:inherit; font-size:12px; cursor:text; color:var(--cyan); border-color:rgba(139, 233, 253, 0.3);">
                </div>
                <div class="control-row">
                    <span class="control-label">24-Hour Time Format</span>
                    <label class="switch">
                        <input type="checkbox" id="setting-clock-24h" ${slot.settings.format_24h ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="control-row">
                    <span class="control-label">Show Date string</span>
                    <label class="switch">
                        <input type="checkbox" id="setting-clock-showdate" ${slot.settings.show_date ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="control-row">
                    <span class="control-label">Show Seconds hand/ticks</span>
                    <label class="switch">
                        <input type="checkbox" id="setting-clock-showseconds" ${slot.settings.show_seconds ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
                
                <!-- World Clocks List Manager -->
                <div style="border-top:1px solid rgba(255,255,255,0.05); margin-top:20px; padding-top:16px; width:100%;">
                    <span class="control-label" style="font-size:11px; font-weight:700; letter-spacing:1px; color:var(--accent-hub); text-transform:uppercase;">◆ World Clocks (Max 12)</span>
                    <div id="clock-world-list" class="flex-col gap-8 mt-16" style="width:100%;">
            `;
            
            const clocks = slot.settings.world_clocks || [];
            if (clocks.length === 0) {
                html += `<div style="font-size:11px; color:var(--text-3); font-style:italic;">No world clocks added.</div>`;
            } else {
                clocks.forEach((c, cIdx) => {
                    html += `
                        <div style="display:flex; align-items:center; justify-content:space-between; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.05); padding:8px 12px; border-radius:8px; width:100%;">
                            <div style="display:flex; flex-direction:column; gap:2px;">
                                <span style="font-size:11px; font-weight:700; color:var(--text-1);">${c.label.toUpperCase()}</span>
                                <span style="font-size:9px; color:var(--text-3);">${c.tz}</span>
                            </div>
                            <div>
                                <button class="clock-world-del-btn" data-cidx="${cIdx}" style="background:transparent; border:none; color:var(--text-3); font-size:12px; cursor:pointer; padding:4px;">✕</button>
                            </div>
                        </div>
                    `;
                });
            }
            
            html += `
                    </div>
                    
                    <div style="display:flex; align-items:center; gap:8px; margin-top:16px; width:100%;">
                        <select id="clock-world-tz-select" style="flex:1;">
                            <option value="America/New_York">New York (EST)</option>
                            <option value="Europe/London">London (GMT)</option>
                            <option value="Europe/Paris">Paris (CET)</option>
                            <option value="Asia/Tokyo">Tokyo (JST)</option>
                            <option value="Asia/Kolkata">Kolkata (IST)</option>
                            <option value="Asia/Shanghai">Shanghai (CST)</option>
                            <option value="Australia/Sydney">Sydney (AEDT)</option>
                            <option value="Pacific/Honolulu">Honolulu (HST)</option>
                        </select>
                        <input type="text" id="clock-world-label-input" placeholder="Label (e.g. LONDON)" class="keybind-key" style="text-align:left; padding:8px 12px; width:140px; font-family:inherit; font-size:12px; cursor:text; color:var(--cyan); border-color:rgba(139, 233, 253, 0.3);">
                        <button id="clock-world-add-btn" class="keybind-key" style="padding:8px 16px; background:rgba(255, 184, 108, 0.1); border-color:rgba(255, 184, 108, 0.3); color:var(--accent-hub); font-weight:600; cursor:pointer;">ADD</button>
                    </div>
                </div>
            `;
        } else if (slot.type === 'stopwatch') {
            html += `
                <div style="font-size:12.5px; color:var(--text-2); padding:8px 0; display:flex; align-items:center; gap:8px;">
                    <span style="color:var(--accent-hub);">●</span> Autonomous module. Features keyboard shortcuts for lap logging. No setup required.
                </div>
            `;
        } else if (slot.type === 'timer') {
            const currentMin = Math.round(slot.settings.default_duration / 60);
            html += `
                <div class="control-item">
                    <div class="control-row">
                        <span class="control-label">Default Countdown</span>
                        <span class="range-val" id="v-timer-dur">${currentMin} min</span>
                    </div>
                    <input type="range" min="1" max="120" value="${currentMin}" data-val="v-timer-dur" id="setting-timer-dur">
                </div>
                <div class="control-row">
                    <span class="control-label">Auto Repeat on Complete</span>
                    <label class="switch">
                        <input type="checkbox" id="setting-timer-repeat" ${slot.settings.auto_repeat ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="control-row">
                    <span class="control-label">Sound on Complete</span>
                    <label class="switch">
                        <input type="checkbox" id="setting-timer-sound" ${slot.settings.sound_enabled ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
                
                <!-- Presets (1 to 5) Manager -->
                <div style="border-top:1px solid rgba(255,255,255,0.05); margin-top:20px; padding-top:16px; width:100%;">
                    <span class="control-label" style="font-size:11px; font-weight:700; letter-spacing:1px; color:var(--accent-hub); text-transform:uppercase;">◆ Timer Presets (Minutes)</span>
                    <div style="display:flex; align-items:center; gap:8px; margin-top:12px; overflow-x:auto; padding-bottom:8px;">
            `;
            
            const presets = slot.settings.presets || [60, 180, 300, 600, 1500];
            presets.forEach((p, pIdx) => {
                const mins = Math.round(p / 60);
                html += `
                    <div style="display:flex; align-items:center; gap:6px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); padding:6px 8px; border-radius:8px; min-width:80px; justify-content:center;">
                        <button class="timer-preset-adj" data-pidx="${pIdx}" data-adj="-1" style="background:transparent; border:none; color:var(--text-3); font-weight:bold; cursor:pointer; font-size:14px; padding:0 4px;">−</button>
                        <span style="font-size:11px; font-weight:700; color:var(--text-1); font-family:monospace; min-width:24px; text-align:center;">${mins}m</span>
                        <button class="timer-preset-adj" data-pidx="${pIdx}" data-adj="1" style="background:transparent; border:none; color:var(--text-3); font-weight:bold; cursor:pointer; font-size:14px; padding:0 4px;">+</button>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        } else if (slot.type === 'weather') {
            const hasPremium = slot.settings.provider !== 'free';
            html += `
                <div class="control-row">
                    <span class="control-label">Weather Provider</span>
                    <select id="setting-weather-provider">
                        <option value="free" ${slot.settings.provider === 'free' ? 'selected' : ''}>Free Met Provider (Default)</option>
                        <option value="tomorrow.io" ${slot.settings.provider === 'tomorrow.io' ? 'selected' : ''}>Tomorrow.io Premium</option>
                        <option value="openweathermap" ${slot.settings.provider === 'openweathermap' ? 'selected' : ''}>OpenWeatherMap API</option>
                    </select>
                </div>
                <div class="control-row">
                    <span class="control-label">Provider API Key</span>
                    <input type="password" id="setting-weather-key" value="${slot.settings.api_key}" placeholder="Paste API Key here..." class="keybind-key" ${!hasPremium ? 'disabled style="opacity:0.35; cursor:not-allowed;"' : ''} style="text-align:left; padding:8px 12px; width:50%; font-family:inherit; font-size:12px; cursor:text; color:var(--yellow); border-color:rgba(241, 250, 140, 0.3);">
                </div>
                <div class="control-row">
                    <span class="control-label">Custom Location Query</span>
                    <input type="text" id="setting-weather-location" value="${slot.settings.location}" placeholder="Leave empty for Auto-IP location..." class="keybind-key" style="text-align:left; padding:8px 12px; width:50%; font-family:inherit; font-size:12px; cursor:text; color:var(--yellow); border-color:rgba(241, 250, 140, 0.3);">
                </div>
                <div class="control-row">
                    <span class="control-label">Use Metric Units (°C)</span>
                    <label class="switch">
                        <input type="checkbox" id="setting-weather-metric" ${slot.settings.use_metric ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
            `;
        } else if (slot.type === 'launcher') {
            html += `
                <div class="control-row">
                    <span class="control-label">Show App Labels</span>
                    <label class="switch">
                        <input type="checkbox" id="setting-launcher-labels" ${slot.settings.show_labels ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="control-item mt-8">
                    <div class="control-row">
                        <span class="control-label">Icon Size Overlay</span>
                        <span class="range-val" id="v-launcher-size">${slot.settings.icon_size}px</span>
                    </div>
                    <input type="range" min="16" max="48" value="${slot.settings.icon_size}" data-val="v-launcher-size" id="setting-launcher-size">
                </div>
                
                <!-- Launcher Items List Grid -->
                <div style="border-top:1px solid rgba(255,255,255,0.05); margin-top:20px; padding-top:16px; width:100%;">
                    <span class="control-label" style="font-size:11px; font-weight:700; letter-spacing:1px; color:var(--accent-hub); text-transform:uppercase;">◆ Launcher Items</span>
                    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-top:16px;">
            `;
            
            const launcherItems = slot.settings.items || [];
            launcherItems.forEach((item, lIdx) => {
                const previewChar = showCustomIcon ? '' + renderSvgIcon("assets/file explorer.svg", 20, 20, "filter: drop-shadow(0 0 2px var(--green));") + '' : '' + renderSvgIcon("assets/launcher.svg", 20, 20, "filter: drop-shadow(0 0 2px var(--green));") + '';
                html += `
                    <div style="position:relative; background:rgba(255,255,255,0.015); border:1px solid rgba(255,255,255,0.05); border-radius:12px; padding:12px 8px; display:flex; flex-direction:column; align-items:center; gap:6px; min-height:140px; min-width: 0;">
                        <!-- Top Controls Row -->
                        <div style="position:absolute; top:6px; left:6px; right:6px; display:flex; justify-content:space-between; align-items:center; width:calc(100% - 12px); z-index: 5;">
                            <button class="launcher-item-menu-btn" data-lidx="${lIdx}" style="background:transparent; border:none; color:var(--text-3); font-size:12px; cursor:pointer; padding:2px;">' + renderSvgIcon("assets/Pandora.svg", 12, 12, "pointer-events:none; opacity: 0.7;") + '</button>
                            <button class="launcher-item-del-btn" data-lidx="${lIdx}" style="background:transparent; border:none; color:var(--text-3); font-size:12px; cursor:pointer; padding:2px;">' + renderSvgIcon("assets/delete.svg", 12, 12, "pointer-events:none; opacity: 0.7;") + '</button>
                        </div>
                        
                        <!-- Actions Dropdown Overlay -->
                        <div class="launcher-item-actions-dd" id="la-dd-${lIdx}" style="display:none; position:absolute; top:28px; left:6px; background:#1a1a20; border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:4px; z-index:10; width:130px; box-shadow:0 8px 16px rgba(0,0,0,0.5);">
                            <div class="la-dd-opt" data-lidx="${lIdx}" data-action="installed-apps" style="font-size:9.5px; color:var(--text-2); padding:6px; cursor:pointer; border-radius:4px; text-align:left;">Browse Apps</div>
                            <div class="la-dd-opt" data-lidx="${lIdx}" data-action="browse-file" style="font-size:9.5px; color:var(--text-2); padding:6px; cursor:pointer; border-radius:4px; text-align:left;">Browse File</div>
                            <div class="la-dd-opt" data-lidx="${lIdx}" data-action="browse-folder" style="font-size:9.5px; color:var(--text-2); padding:6px; cursor:pointer; border-radius:4px; text-align:left;">Browse Folder</div>
                            <div class="la-dd-opt" data-lidx="${lIdx}" data-action="default-icon" style="font-size:9.5px; color:var(--text-2); padding:6px; cursor:pointer; border-radius:4px; text-align:left;">Default Icon</div>
                            <div class="la-dd-opt" data-lidx="${lIdx}" data-action="custom-icon" style="font-size:9.5px; color:var(--text-2); padding:6px; cursor:pointer; border-radius:4px; text-align:left;">Custom Icon</div>
                        </div>
                        
                        <!-- Icon Circle Preview -->
                        <div style="width:36px; height:36px; border-radius:50%; background:rgba(80, 250, 123, 0.1); display:flex; align-items:center; justify-content:center; font-size:18px; color:var(--green); margin-top:14px; border:1px solid rgba(80, 250, 123, 0.2); flex-shrink: 0;">
                            ${previewChar}
                        </div>
                        
                        <!-- Inputs -->
                        <input type="text" class="launcher-item-label-inp" data-lidx="${lIdx}" value="${item.label}" placeholder="Label" style="width:100%; text-align:center; font-size:10.5px; background:transparent; border:none; outline:none; color:var(--text-1); font-weight:600; padding:2px 0;">
                        <input type="text" class="launcher-item-path-inp" data-lidx="${lIdx}" value="${item.path}" placeholder="Path" style="width:100%; text-align:center; font-size:9px; background:transparent; border:none; outline:none; color:var(--text-3); font-family:monospace; padding:2px 0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                    </div>
                `;
            });
            
            // Dotted Add Button Card
            html += `
                        <div id="launcher-item-add-btn" style="border:1px dashed rgba(255,255,255,0.1); border-radius:12px; display:flex; flex-direction:column; align-items:center; justify-content:center; cursor:pointer; min-height:140px; color:var(--text-3); font-size:11px; font-weight:600; gap:8px;">
                            <span style="font-size:24px; font-weight:300;">+</span>
                            <span>ADD ITEM</span>
                        </div>
                    </div>
                </div>
            `;
        }

        html += `</div>`;
        content.innerHTML = html;

        // Custom Slider Background updates & State saving
        content.querySelectorAll('input[type=range]').forEach(el => {
            updateSlider(el);
            el.addEventListener('input', () => {
                updateSlider(el);
                if (el.id === 'setting-media-strength') {
                    slot.settings.effect_strength = parseInt(el.value);
                } else if (el.id === 'setting-timer-dur') {
                    slot.settings.default_duration = parseInt(el.value) * 60;
                    document.getElementById('v-timer-dur').textContent = el.value + ' min';
                } else if (el.id === 'setting-launcher-size') {
                    slot.settings.icon_size = parseInt(el.value);
                    document.getElementById('v-launcher-size').textContent = el.value + 'px';
                }
                saveHubConfig();
            });
        });

        // Event listeners for selects
        content.querySelectorAll('select').forEach(sel => {
            sel.addEventListener('change', () => {
                const val = sel.value;
                if (sel.id === 'setting-media-artstyle') {
                    const oldStyle = slot.settings.art_style || 'Gaussian Blur';
                    const currentVis = slot.settings.visualizer || 'None';
                    if (oldStyle === '8-Bit Mosaic') {
                        slot.settings.last_mosaic_vis = currentVis;
                    } else {
                        slot.settings.last_blur_vis = currentVis;
                    }
                    
                    slot.settings.art_style = val;
                    
                    if (val === '8-Bit Mosaic') {
                        slot.settings.visualizer = slot.settings.last_mosaic_vis || 'Reactive Voxels';
                    } else {
                        slot.settings.visualizer = slot.settings.last_blur_vis || 'Edge Ring EQ';
                    }
                    openWidgetSettings(index); // Re-render to show/hide mosaic block style!
                }

                else if (sel.id === 'setting-media-mosaicshape') slot.settings.mosaic_shape = val;
                else if (sel.id === 'setting-media-visualizer') {
                    slot.settings.visualizer = val;
                    if (slot.settings.art_style === '8-Bit Mosaic') {
                        slot.settings.last_mosaic_vis = val;
                    } else {
                        slot.settings.last_blur_vis = val;
                    }
                }
                else if (sel.id === 'setting-clock-mode') slot.settings.clock_mode = val;
                else if (sel.id === 'setting-clock-tz') {
                    slot.settings.active_clock_tz = val;
                    const selectedOpt = sel.options[sel.selectedIndex];
                    const labelInput = document.getElementById('setting-clock-label');
                    if (labelInput) {
                        const newLabel = val === "" ? "LOCAL TIME" : selectedOpt.text.split(" (")[0].toUpperCase();
                        slot.settings.active_clock_label = newLabel;
                        labelInput.value = newLabel;
                    }
                }
                else if (sel.id === 'setting-weather-provider') {
                    slot.settings.provider = val;
                    openWidgetSettings(index); // Re-render to enable/disable API key input!
                }
                saveHubConfig();
                if (window.sendAppUpdate) window.sendAppUpdate();
            });
        });

        // Event listeners for radio buttons
        content.querySelectorAll('input[type=radio][name=anim_style]').forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.checked) {
                    slot.settings.animation_style = radio.value;
                    saveHubConfig();
                    if (window.sendAppUpdate) window.sendAppUpdate();
                }
            });
        });

        // Event listeners for toggles
        content.querySelectorAll('input[type=checkbox]').forEach(chk => {
            chk.addEventListener('change', () => {
                const checked = chk.checked;
                if (chk.id === 'setting-media-showtimeline') slot.settings.show_timeline = checked;
                else if (chk.id === 'setting-media-showtitle') slot.settings.show_title = checked;
                else if (chk.id === 'setting-media-showcontrols') slot.settings.show_controls = checked;
                else if (chk.id === 'setting-clock-24h') slot.settings.format_24h = checked;
                else if (chk.id === 'setting-clock-showdate') slot.settings.show_date = checked;
                else if (chk.id === 'setting-clock-showseconds') slot.settings.show_seconds = checked;
                else if (chk.id === 'setting-timer-repeat') slot.settings.auto_repeat = checked;
                else if (chk.id === 'setting-weather-metric') slot.settings.use_metric = checked;
                else if (chk.id === 'setting-launcher-labels') slot.settings.show_labels = checked;
                saveHubConfig();
            });
        });

        // Event listeners for text/password inputs
        content.querySelectorAll('input[type=text], input[type=password]').forEach(inp => {
            inp.addEventListener('input', () => {
                const val = inp.value;
                if (inp.id === 'setting-clock-label') slot.settings.active_clock_label = val;
                else if (inp.id === 'setting-weather-location') slot.settings.location = val;
                else if (inp.id === 'setting-weather-key') slot.settings.api_key = val;
                saveHubConfig();
            });
        });

        initWidgetCustomSelects(content, index);

        // Clock Widget World Clocks event bindings
        const addClockBtn = document.getElementById('clock-world-add-btn');
        if (addClockBtn) {
            addClockBtn.addEventListener('click', () => {
                const tzSelect = document.getElementById('clock-world-tz-select');
                const labelInput = document.getElementById('clock-world-label-input');
                if (tzSelect && labelInput) {
                    const tz = tzSelect.value;
                    const label = labelInput.value.trim() || tzSelect.options[tzSelect.selectedIndex].text.split(" (")[0];
                    if (!slot.settings.world_clocks) slot.settings.world_clocks = [];
                    if (slot.settings.world_clocks.length >= 12) return;
                    slot.settings.world_clocks.push({ label: label, tz: tz });
                    saveHubConfig();
                    openWidgetSettings(index);
                }
            });
        }
        document.querySelectorAll('.clock-world-del-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const cIdx = parseInt(btn.getAttribute('data-cidx'));
                if (slot.settings.world_clocks) {
                    slot.settings.world_clocks.splice(cIdx, 1);
                    saveHubConfig();
                    openWidgetSettings(index);
                }
            });
        });

        // Timer Widget Sound & Presets event bindings
        const timerSound = document.getElementById('setting-timer-sound');
        if (timerSound) {
            timerSound.addEventListener('change', () => {
                slot.settings.sound_enabled = timerSound.checked;
                saveHubConfig();
            });
        }
        document.querySelectorAll('.timer-preset-adj').forEach(btn => {
            btn.addEventListener('click', () => {
                const pIdx = parseInt(btn.getAttribute('data-pidx'));
                const adj = parseInt(btn.getAttribute('data-adj'));
                if (!slot.settings.presets) slot.settings.presets = [60, 180, 300, 600, 1500];
                
                let mins = Math.round(slot.settings.presets[pIdx] / 60);
                mins = Math.max(1, Math.min(120, mins + adj));
                slot.settings.presets[pIdx] = mins * 60;
                
                saveHubConfig();
                openWidgetSettings(index);
            });
        });

        // Launcher Widget Items list bindings
        const addLauncherBtn = document.getElementById('launcher-item-add-btn');
        if (addLauncherBtn) {
            addLauncherBtn.addEventListener('click', () => {
                if (!slot.settings.items) slot.settings.items = [];
                slot.settings.items.push({ label: 'New', path: '', icon_mode: 'auto', icon: '' });
                saveHubConfig();
                openWidgetSettings(index);
            });
        }
        document.querySelectorAll('.launcher-item-del-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const lIdx = parseInt(btn.getAttribute('data-lidx'));
                if (slot.settings.items) {
                    slot.settings.items.splice(lIdx, 1);
                    saveHubConfig();
                    openWidgetSettings(index);
                }
            });
        });
        document.querySelectorAll('.launcher-item-label-inp').forEach(inp => {
            inp.addEventListener('input', () => {
                const lIdx = parseInt(inp.getAttribute('data-lidx'));
                if (slot.settings.items) {
                    slot.settings.items[lIdx].label = inp.value;
                    saveHubConfig();
                }
            });
        });
        document.querySelectorAll('.launcher-item-path-inp').forEach(inp => {
            inp.addEventListener('input', () => {
                const lIdx = parseInt(inp.getAttribute('data-lidx'));
                if (slot.settings.items) {
                    slot.settings.items[lIdx].path = inp.value;
                    saveHubConfig();
                }
            });
        });
        document.querySelectorAll('.launcher-item-menu-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const lIdx = btn.getAttribute('data-lidx');
                const dd = document.getElementById('la-dd-' + lIdx);
                document.querySelectorAll('.launcher-item-actions-dd').forEach(other => {
                    if (other.id !== 'la-dd-' + lIdx) other.style.display = 'none';
                });
                if (dd) {
                    dd.style.display = dd.style.display === 'none' ? 'flex' : 'none';
                    dd.style.flexDirection = 'column';
                }
            });
        });
        document.querySelectorAll('.la-dd-opt').forEach(opt => {
            opt.addEventListener('click', () => {
                const lIdx = parseInt(opt.getAttribute('data-lidx'));
                const action = opt.getAttribute('data-action');
                if (slot.settings.items) {
                    const item = slot.settings.items[lIdx];
                    if (action === 'installed-apps') {
                        item.path = 'C:\\Program Files\\Example\\App.exe';
                        item.label = 'Example App';
                        item.icon_mode = 'auto';
                    } else if (action === 'browse-file') {
                        item.path = 'C:\\Users\\User\\Documents\\File.txt';
                        item.label = 'File';
                        item.icon_mode = 'auto';
                    } else if (action === 'browse-folder') {
                        item.path = 'C:\\Users\\User\\Pictures';
                        item.label = 'Pictures';
                        item.icon_mode = 'auto';
                    } else if (action === 'default-icon') {
                        item.icon_mode = 'auto';
                    } else if (action === 'custom-icon') {
                        item.icon_mode = 'custom';
                        item.icon = 'assets/custom_icon.png';
                    }
                    saveHubConfig();
                    openWidgetSettings(index);
                }
            });
        });
    } else {
        title.innerHTML = `Assign Module to Slot ${index + 1}`;
        let html = `
            <div style="font-size:12px; color:var(--text-3); margin-bottom:16px;">This slot is currently empty. Select a widget module below to assign it:</div>
            <div class="add-widget-grid">
        `;
        
        Object.entries(HUB_MODULES).forEach(([typeKey, mod]) => {
            const isAssigned = hubSlots.some(s => s && s.type === typeKey);
            const isDisabled = typeKey !== 'launcher' && isAssigned;
            
            html += `
                <button class="add-widget-btn" data-type="${typeKey}" ${isDisabled ? 'disabled style="opacity:0.35; cursor:not-allowed;"' : ''} style="--widget-hover-color:${mod.color}">
                    <span class="add-widget-icon">${mod.icon}</span>
                    <span>${mod.name}</span>
                    ${isDisabled ? '<span style="font-size:9px; color:var(--text-3); font-weight:normal; display:block; margin-top:2px;">(Assigned)</span>' : ''}
                </button>
            `;
        });
        
        html += `</div>`;
        content.innerHTML = html;

        content.querySelectorAll('.add-widget-btn').forEach(btn => {
            if (btn.hasAttribute('disabled')) return;
            btn.addEventListener('click', () => {
                const type = btn.getAttribute('data-type');
                assignHubModule(index, type);
            });
        });
    }
}

// Initialize Hub (render without sending, config hasn't loaded yet)
window.isUpdatingHubFromPython = true;
renderHubGrid();
window.isUpdatingHubFromPython = false;

// Toggle sizing container dynamically when size preset is "Custom" (Templates)
const tplPreset = document.getElementById('mock-tpl-size-preset');
if (tplPreset) {
    tplPreset.addEventListener('change', () => {
        const container = document.getElementById('tpl-custom-sizing-container');
        if (container) {
            container.style.display = tplPreset.value === 'Custom' ? 'flex' : 'none';
            container.style.flexDirection = 'column';
        }
    });
}

// Toggle sizing container dynamically when size preset is "Custom" (Folders)
const fldPreset = document.getElementById('mock-fld-size-preset');
if (fldPreset) {
    fldPreset.addEventListener('change', () => {
        const container = document.getElementById('fld-custom-sizing-container');
        if (container) {
            container.style.display = fldPreset.value === 'Custom' ? 'flex' : 'none';
            container.style.flexDirection = 'column';
        }
    });
}

// Bind Color Pickers in Template Editor and Folder Editor to display hex labels
['glowcolor', 'bgcolor', 'textcolor', 'highlightcolor'].forEach(colorId => {
    // Templates
    const tplInput = document.getElementById('i-tpl-' + colorId);
    if (tplInput) {
        tplInput.addEventListener('input', () => {
            const span = document.getElementById('v-tpl-' + colorId);
            if (span) span.textContent = tplInput.value;
        });
    }
    // Folders
    const fldInput = document.getElementById('i-fld-' + colorId);
    if (fldInput) {
        fldInput.addEventListener('input', () => {
            const span = document.getElementById('v-fld-' + colorId);
            if (span) span.textContent = fldInput.value;
        });
    }
});
}

// Initialize Custom Selects (File Scope)
function syncCustomSelect(sel) {
    if (typeof sel === 'string') sel = document.getElementById(sel);
    if (!sel) return;
    
    let wrapper = sel.parentNode;
    let isNew = false;
    if (!wrapper || !wrapper.classList.contains('custom-select')) {
        wrapper = document.createElement('div');
        wrapper.className = 'custom-select';
        sel.parentNode.insertBefore(wrapper, sel);
        wrapper.appendChild(sel);
        isNew = true;
    }
    
    const selectedDiv = wrapper.querySelector('.select-selected');
    const optionsDiv = wrapper.querySelector('.select-items');
    
    let rebuild = isNew || !selectedDiv || !optionsDiv;
    if (!rebuild) {
        const optionDivs = optionsDiv.querySelectorAll('div');
        if (optionDivs.length !== sel.options.length) {
            rebuild = true;
        } else {
            for (let i = 0; i < sel.options.length; i++) {
                if (optionDivs[i].innerHTML !== sel.options[i].innerHTML) {
                    rebuild = true;
                    break;
                }
            }
        }
    }
    
    if (rebuild) {
        if (selectedDiv) selectedDiv.remove();
        if (optionsDiv) optionsDiv.remove();
        
        if (sel.options.length === 0) return;
        
        const newSelectedDiv = document.createElement('div');
        newSelectedDiv.className = 'select-selected';
        if (sel.options[sel.selectedIndex]) {
            newSelectedDiv.innerHTML = sel.options[sel.selectedIndex].innerHTML;
        }
        wrapper.appendChild(newSelectedDiv);

        const newOptionsDiv = document.createElement('div');
        newOptionsDiv.className = 'select-items select-hide';
        
        for (let i = 0; i < sel.options.length; i++) {
            const opt = document.createElement('div');
            opt.innerHTML = sel.options[i].innerHTML;
            if (i === sel.selectedIndex) opt.classList.add('same-as-selected');
            if (sel.options[i].hidden || sel.options[i].disabled) opt.style.display = 'none';
            
            opt.addEventListener('click', function(e) {
                e.stopPropagation();
                if (sel.options[i].disabled || sel.options[i].hidden) return;
                sel.selectedIndex = i;
                sel.dispatchEvent(new Event('change'));
                
                newSelectedDiv.innerHTML = this.innerHTML;
                
                const s = this.parentNode.querySelectorAll('.same-as-selected');
                for (let k = 0; k < s.length; k++) {
                    s[k].classList.remove('same-as-selected');
                }
                this.classList.add('same-as-selected');
                
                closeAllSelect();
            });
            newOptionsDiv.appendChild(opt);
        }
        wrapper.appendChild(newOptionsDiv);
        
        newSelectedDiv.onclick = function(e) {
            e.stopPropagation();
            closeAllSelect(this);
            newOptionsDiv.classList.toggle('select-hide');
            newSelectedDiv.classList.toggle('select-arrow-active');
            wrapper.classList.toggle('active');
        };
    } else {
        if (sel.options[sel.selectedIndex]) {
            selectedDiv.innerHTML = sel.options[sel.selectedIndex].innerHTML;
        }
        const optionDivs = optionsDiv.querySelectorAll('div');
        for (let i = 0; i < optionDivs.length; i++) {
            if (i === sel.selectedIndex) {
                optionDivs[i].classList.add('same-as-selected');
            } else {
                optionDivs[i].classList.remove('same-as-selected');
            }
            if (sel.options[i].hidden || sel.options[i].disabled) {
                optionDivs[i].style.display = 'none';
            } else {
                optionDivs[i].style.display = '';
            }
        }
    }
}

function closeAllSelect(elmnt) {
    const items = document.getElementsByClassName('select-items');
    const selected = document.getElementsByClassName('select-selected');
    for (let i = 0; i < selected.length; i++) {
        if (elmnt !== selected[i]) {
            selected[i].classList.remove('select-arrow-active');
            const wrap = selected[i].parentNode;
            if (wrap && wrap.classList.contains('custom-select')) {
                wrap.classList.remove('active');
            }
            if (items[i]) {
                items[i].classList.add('select-hide');
            }
        }
    }
}
document.addEventListener('click', closeAllSelect);

function initResetButtons() {
    document.querySelectorAll('.section-header').forEach(header => {
        const textEl = header.querySelector('.sh-text');
        if (!textEl) return;
        const sectionName = textEl.textContent.trim();
        
        const validSections = ["Appearance", "Grid Behavior", "Display Effects", "Media Widget Settings", "Time Widget Settings", "Activation & Behavior", "Dimensions & Feel"];
        if (!validSections.includes(sectionName)) return;
        
        const resetBtn = document.createElement('button');
        resetBtn.className = 'link-btn';
        resetBtn.style.fontSize = '11px';
        resetBtn.style.marginLeft = 'auto';
        resetBtn.style.opacity = '0.6';
        resetBtn.innerHTML = 'Reset to Default';
        
        resetBtn.onmouseenter = () => resetBtn.style.opacity = '1';
        resetBtn.onmouseleave = () => resetBtn.style.opacity = '0.6';
        
        resetBtn.onclick = (e) => {
            e.stopPropagation();
            if (window.sendCustomCommand) {
                window.sendCustomCommand({ type: 'reset_config', section: sectionName });
                
                const origText = resetBtn.innerHTML;
                resetBtn.innerHTML = 'Resetting...';
                setTimeout(() => resetBtn.innerHTML = origText, 1000);
            }
        };
        
        header.style.display = 'flex';
        header.style.alignItems = 'center';
        header.appendChild(resetBtn);
    });
}
// Run on next tick to ensure DOM is ready and renderer has attached functions
setTimeout(initResetButtons, 100);

module.exports = { vkMap, getVkName, bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue, initGlobalUI, syncCustomSelect };
