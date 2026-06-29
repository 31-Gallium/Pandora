const { getVkName, bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue, syncCustomSelect } = require('./ui_dashboard_common.js');

class FoldersTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
        this.editingFolderId = null;
    }

    init() {
        // Add new Folder button
        const addBtn = document.getElementById('btn-add-folder');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                const name = prompt("Enter new folder name:");
                if (!name) return;
                
                const cfg = this.getConfig();
                if (!cfg.folders) cfg.folders = [];
                
                const newFolder = {
                    id: crypto.randomUUID(),
                    name: name,
                    show_title: true,
                    grid_snap: true,
                    show_app_names: false,
                    pill_mode: 'Name',
                    pill_icon_path: '',
                    apps: []
                };
                
                cfg.folders.push(newFolder);
                this.sendUpdate();
                this.updateUI(cfg);
            });
        }
    }

    updateUI(cfg) {
        if (!cfg || !cfg.folders) return;
        const container = document.getElementById('fld-list-content');
        if (!container) return;
        
        container.innerHTML = '';
        
        cfg.folders.forEach(fld => {
            const item = document.createElement('div');
            item.className = 'list-item';
            item.onclick = () => window.showEditor('fld', null, fld.id);
            
            const numItems = (fld.apps || []).length;
            
            item.innerHTML = `
                <div><span class="item-name" style="color:var(--accent-folders);">${fld.name}</span><span style="color:var(--text-3);font-size:11px;margin-left:8px;">(${numItems} items)</span></div>
            `;
            container.appendChild(item);
        });

        if (this.editingFolderId) {
            const folder = cfg.folders.find(f => f.id === this.editingFolderId);
            if (folder) this.renderEditor(folder);
            else this.hideEditor();
        }
    }

    showEditor(id) {
        this.editingFolderId = id;
        const cfg = this.getConfig();
        const folder = cfg.folders.find(f => f.id === id);
        if (folder) {
            document.getElementById('fld-list').style.display = 'none';
            document.getElementById('fld-editor').style.display = 'block';
            this.renderEditor(folder);
        }
    }

    hideEditor() {
        this.editingFolderId = null;
        document.getElementById('fld-editor').style.display = 'none';
        document.getElementById('fld-list').style.display = 'block';
    }

    renderEditor(folder) {
        document.getElementById('fld-title').textContent = `Editing: ${folder.name}`;
        
        const nameInput = document.querySelector('#i-fld-name');
        const showTitleInput = document.querySelector('#i-fld-showtitle');
        const showAppNamesInput = document.querySelector('#i-fld-showappnames');
        const gridSnapInput = document.querySelector('#i-fld-gridsnap');
        const pillIconInput = document.querySelector('#i-fld-pillicon');
        const btnModeText = document.getElementById('btn-mode-text');
        const btnModeIcon = document.getElementById('btn-mode-icon');
        const btnPickIcon = document.getElementById('btn-pick-icon');
        
        nameInput.value = folder.name || '';
        showTitleInput.checked = folder.show_title !== false;
        showAppNamesInput.checked = folder.show_app_names === true;
        gridSnapInput.checked = folder.grid_snap !== false;
        pillIconInput.value = folder.pill_icon_path || '';
        
        const updatePillVisibility = () => {
            const isName = folder.pill_mode !== 'Icon';
            document.getElementById('row-pill-icon').style.display = isName ? 'none' : 'flex';
            
            btnModeText.style.background = isName ? 'var(--accent-folders)' : 'transparent';
            btnModeText.querySelector('img').style.opacity = isName ? '1' : '0.5';
            
            btnModeIcon.style.background = !isName ? 'var(--accent-folders)' : 'transparent';
            btnModeIcon.querySelector('img').style.opacity = !isName ? '1' : '0.5';
        };
        updatePillVisibility();
        
        nameInput.onchange = (e) => {
            folder.name = e.target.value;
            document.getElementById('fld-title').textContent = `Editing: ${folder.name}`;
            this.sendUpdate();
            this.updateUI(this.getConfig());
        };
        
        showTitleInput.onchange = (e) => {
            folder.show_title = e.target.checked;
            this.sendUpdate();
        };
        

        
        showAppNamesInput.onchange = (e) => {
            folder.show_app_names = e.target.checked;
            this.sendUpdate();
        };
        
        gridSnapInput.onchange = (e) => {
            folder.grid_snap = e.target.checked;
            this.sendUpdate();
        };
        
        btnModeText.onclick = () => {
            folder.pill_mode = 'Name';
            updatePillVisibility();
            this.sendUpdate();
        };
        
        btnModeIcon.onclick = () => {
            folder.pill_mode = 'Icon';
            updatePillVisibility();
            this.sendUpdate();
        };
        
        btnPickIcon.onclick = async () => {
            const { ipcRenderer } = require('electron');
            const path = await ipcRenderer.invoke('dialog:openFile');
            if (path) {
                pillIconInput.value = path;
                folder.pill_icon_path = path;
                this.sendUpdate();
            }
        };
        
        pillIconInput.onchange = (e) => {
            folder.pill_icon_path = e.target.value;
            this.sendUpdate();
        };
    }
}
module.exports = { FoldersTab };
