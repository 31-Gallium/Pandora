const { getVkName, bindInput, bindSlider, setInputValue, setCheckboxValue, setSliderValue, syncCustomSelect } = require('./ui_dashboard_common.js');

class FoldersTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
        this.editingFolderId = null;
    }

    async showCustomPrompt(message, defaultValue = "") {
        return new Promise(resolve => {
            const overlay = document.createElement('div');
            overlay.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 9999; backdrop-filter: blur(4px);';
            
            const dialog = document.createElement('div');
            dialog.style.cssText = 'background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; width: 300px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); display: flex; flex-direction: column; gap: 15px;';
            
            const msg = document.createElement('div');
            msg.style.cssText = 'font-weight: 600; color: var(--text-primary);';
            msg.textContent = message;
            
            const input = document.createElement('input');
            input.type = 'text';
            input.value = defaultValue;
            input.style.cssText = 'background: var(--bg-tertiary); border: 1px solid var(--border-color); color: var(--text-primary); padding: 8px 12px; border-radius: 6px; outline: none; font-family: inherit;';
            
            const btnRow = document.createElement('div');
            btnRow.style.cssText = 'display: flex; justify-content: flex-end; gap: 10px;';
            
            const cancelBtn = document.createElement('button');
            cancelBtn.textContent = 'Cancel';
            cancelBtn.style.cssText = 'background: transparent; border: 1px solid var(--border-color); color: var(--text-secondary); padding: 6px 16px; border-radius: 6px; cursor: pointer; font-family: inherit;';
            
            const okBtn = document.createElement('button');
            okBtn.textContent = 'OK';
            okBtn.style.cssText = 'background: var(--accent-primary); border: none; color: white; padding: 6px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; font-family: inherit;';
            
            btnRow.appendChild(cancelBtn);
            btnRow.appendChild(okBtn);
            dialog.appendChild(msg);
            dialog.appendChild(input);
            dialog.appendChild(btnRow);
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);
            
            input.focus();
            
            const cleanup = (val) => {
                document.body.removeChild(overlay);
                resolve(val);
            };
            
            okBtn.onclick = () => cleanup(input.value.trim());
            cancelBtn.onclick = () => cleanup(null);
            input.onkeydown = (e) => {
                if (e.key === 'Enter') cleanup(input.value.trim());
                if (e.key === 'Escape') cleanup(null);
            };
        });
    }

    async showCustomConfirm(message, cancelText="Cancel", spillText="Spill out", deleteText="Delete them") {
        return new Promise(resolve => {
            const overlay = document.createElement('div');
            overlay.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 9999; backdrop-filter: blur(4px);';
            
            const dialog = document.createElement('div');
            dialog.style.cssText = 'background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; width: 320px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); display: flex; flex-direction: column; gap: 15px;';
            
            const msg = document.createElement('div');
            msg.style.cssText = 'font-weight: 500; color: var(--text-1); font-size: 14px;';
            msg.textContent = message;
            
            const btnRow = document.createElement('div');
            btnRow.style.cssText = 'display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px; flex-wrap: wrap;';
            
            const cancelBtn = document.createElement('button');
            cancelBtn.textContent = cancelText;
            cancelBtn.className = "action-btn";
            
            const spillBtn = document.createElement('button');
            spillBtn.textContent = spillText;
            spillBtn.className = "action-btn";
            spillBtn.style.cssText = 'color: #26C0D3; border-color: rgba(38,192,211,0.4); background: rgba(38,192,211,0.05);';
            spillBtn.onmouseover = () => spillBtn.style.background = 'rgba(38,192,211,0.15)';
            spillBtn.onmouseout = () => spillBtn.style.background = 'rgba(38,192,211,0.05)';
            
            const deleteBtn = document.createElement('button');
            deleteBtn.textContent = deleteText;
            deleteBtn.className = "action-btn";
            deleteBtn.style.cssText = 'color: #ff5555; border-color: rgba(255,85,85,0.4); background: rgba(255,85,85,0.05);';
            deleteBtn.onmouseover = () => deleteBtn.style.background = 'rgba(255,85,85,0.15)';
            deleteBtn.onmouseout = () => deleteBtn.style.background = 'rgba(255,85,85,0.05)';
            
            btnRow.appendChild(cancelBtn);
            btnRow.appendChild(spillBtn);
            btnRow.appendChild(deleteBtn);
            
            dialog.appendChild(msg);
            dialog.appendChild(btnRow);
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);
            
            const cleanup = (val) => {
                document.body.removeChild(overlay);
                resolve(val);
            };
            
            cancelBtn.onclick = () => cleanup(null);
            spillBtn.onclick = () => cleanup("spill");
            deleteBtn.onclick = () => cleanup("delete");
        });
    }

    init() {
        // Add new Folder button
        const addBtn = document.getElementById('btn-add-folder');
        if (addBtn) {
            addBtn.addEventListener('click', async () => {
                const greekNames = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega"];
                const cfg = this.getConfig();
                if (!cfg.folders) cfg.folders = [];
                const existingNames = new Set(cfg.folders.map(f => f.name));
                const defaultName = greekNames.find(n => !existingNames.has(n)) || "New Folder";
                
                const name = await this.showCustomPrompt("Enter new folder name:", defaultName);
                if (!name) return;
                
                if (window.sendCustomCommand) {
                    window.sendCustomCommand({
                        type: 'create_folder_action',
                        name: name
                    });
                }
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
                <div style="display:flex; justify-content:space-between; align-items:center; width:100%;">
                    <div><span class="item-name" style="color:var(--accent-folders);">${fld.name}</span><span style="color:var(--text-3);font-size:11px;margin-left:8px;">(${numItems} items)</span></div>
                    <button class="delete-fld-btn" title="Delete Folder"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg></button>
                </div>
            `;
            
            item.querySelector('.delete-fld-btn').onclick = async (e) => {
                e.stopPropagation();
                const regularApps = fld.apps ? fld.apps.filter(a => !a.path.startsWith('pandora://folder/')) : [];
                if (regularApps.length === 0) {
                    if (window.sendCustomCommand) {
                        window.sendCustomCommand({
                            type: 'delete_folder_action',
                            id: fld.id,
                            action: 'delete'
                        });
                    }
                    return;
                }
                const choice = await this.showCustomConfirm(`Delete folder "${fld.name}"?`);
                if (choice && window.sendCustomCommand) {
                    window.sendCustomCommand({
                        type: 'delete_folder_action',
                        id: fld.id,
                        action: choice
                    });
                }
            };
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
        const btnDeleteFld = document.getElementById('btn-delete-fld');
        
        if (btnDeleteFld) {
            btnDeleteFld.onclick = async () => {
                const regularApps = folder.apps ? folder.apps.filter(a => !a.path.startsWith('pandora://folder/')) : [];
                if (regularApps.length === 0) {
                    if (window.sendCustomCommand) {
                        window.sendCustomCommand({
                            type: 'delete_folder_action',
                            id: folder.id,
                            action: 'delete'
                        });
                    }
                    this.hideEditor();
                    return;
                }
                const choice = await this.showCustomConfirm(`Delete folder "${folder.name}"?`);
                if (choice && window.sendCustomCommand) {
                    window.sendCustomCommand({
                        type: 'delete_folder_action',
                        id: folder.id,
                        action: choice
                    });
                    this.hideEditor();
                }
            };
        }
        
        nameInput.value = folder.name || '';
        showTitleInput.checked = folder.show_title !== false;
        showAppNamesInput.checked = folder.show_app_names === true;
        gridSnapInput.checked = folder.grid_snap !== false;
        pillIconInput.value = folder.pill_icon_path || '';
        
        const updatePillVisibility = () => {
            const isName = folder.pill_mode !== 'Icon';
            document.getElementById('row-pill-icon').style.display = isName ? 'none' : 'flex';
            
            btnModeText.classList.toggle('active', isName);
            btnModeIcon.classList.toggle('active', !isName);
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
