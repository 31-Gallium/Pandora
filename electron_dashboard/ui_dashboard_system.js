const { bindInput, setCheckboxValue, setInputValue } = require('./ui_dashboard_common.js');

class SystemTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
        this._pendingDownloadUrl = null;
    }

    init() {
        bindInput('#set-launch-startup input', 'general_settings.launch_at_startup', false, this.getConfig, this.sendUpdate);
        bindInput('#set-open-dash-startup input', 'general_settings.open_dashboard_startup', false, this.getConfig, this.sendUpdate);
        bindInput('#set-system-gpu-pref select', 'general_settings.gpu_preference', true, this.getConfig, this.sendUpdate);
        
        const channelSelect = document.getElementById('update-channel-select');
        if (channelSelect) {
            bindInput('#update-channel-select', 'general_settings.update_channel', false, this.getConfig, this.sendUpdate);
            channelSelect.addEventListener('change', () => {
                if (window.sendCustomCommand) {
                    const btn = document.getElementById('btn-check-update');
                    if (btn) {
                        btn.innerHTML = 'Checking...';
                        btn.disabled = true;
                    }
                    window.sendCustomCommand({ type: 'check_for_updates' });
                }
            });
        }
        
        const resetBtn = document.getElementById('btn-reset-all');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                if (window.sendCustomCommand) {
                    const orig = resetBtn.innerHTML;
                    resetBtn.innerHTML = 'Resetting...';
                    window.sendCustomCommand({ type: 'reset_config', section: 'all' });
                    setTimeout(() => resetBtn.innerHTML = orig, 1000);
                }
            });
        }

        // Update button
        const updateBtn = document.getElementById('btn-check-update');
        if (updateBtn) {
            updateBtn.addEventListener('click', () => {
                if (!window.sendCustomCommand) return;
                
                const action = updateBtn.dataset.action;
                if (action === 'apply') {
                    updateBtn.innerHTML = 'Updating...';
                    updateBtn.disabled = true;
                    window.sendCustomCommand({ type: 'apply_update' });
                } else if (action === 'restart') {
                    window.sendCustomCommand({ type: 'restart_app' });
                } else {
                    updateBtn.innerHTML = 'Checking...';
                    updateBtn.disabled = true;
                    window.sendCustomCommand({ type: 'check_for_updates' });
                }
            });
        }
        
        // Auto-check for updates when dashboard is opened
        if (window.sendCustomCommand) {
            setTimeout(() => {
                window.sendCustomCommand({ type: 'check_for_updates' });
            }, 500); // Small delay to ensure WS is fully ready
        }

        // Rollbacks button
        const viewRollbacksBtn = document.getElementById('btn-view-rollbacks');
        if (viewRollbacksBtn) {
            viewRollbacksBtn.addEventListener('click', () => {
                const list = document.getElementById('rollbacks-list');
                if (list) {
                    if (list.style.display === 'none' || list.style.display === '') {
                        list.style.display = 'block';
                        viewRollbacksBtn.innerHTML = 'Hide Version History';
                        list.innerHTML = '<div style="text-align: center; color: var(--text-dim); font-size: 11px; padding: 12px;">Loading past releases...</div>';
                        if (window.sendCustomCommand) {
                            window.sendCustomCommand({ type: 'fetch_releases' });
                        }
                    } else {
                        list.style.display = 'none';
                        viewRollbacksBtn.innerHTML = 'View Version History';
                    }
                }
            });
        }
    }

    handleUpdateCheckResult(data) {
        const btn = document.getElementById('btn-check-update');
        const status = document.getElementById('update-status');
        const versionPill = document.getElementById('version-pill');
        
        if (!btn || !status) return;

        btn.disabled = false;
        
        if (versionPill) {
            versionPill.classList.remove('status-error', 'status-available', 'status-uptodate');
        }

        if (data.error) {
            status.textContent = data.error;
            status.style.color = '#ff5555';
            btn.innerHTML = 'Retry';
            btn.dataset.action = 'check';
            if (versionPill) versionPill.classList.add('status-error');
        } else if (data.available) {
            status.textContent = `v${data.latest_version} is available!`;
            status.style.color = '#50fa7b';
            btn.innerHTML = 'Update Now';
            btn.dataset.action = 'apply';
            this._pendingDownloadUrl = data.download_url;
            if (versionPill) versionPill.classList.add('status-available');
        } else {
            status.textContent = 'You\'re up to date! ✓';
            status.style.color = '#50fa7b';
            btn.innerHTML = 'Check for Updates';
            btn.dataset.action = 'check';
            if (versionPill) versionPill.classList.add('status-uptodate');
        }
    }

    handleUpdateProgress(data) {
        const wrap = document.getElementById('update-progress-wrap');
        const bar = document.getElementById('update-progress-bar');
        const text = document.getElementById('update-progress-text');
        const btn = document.getElementById('btn-check-update');
        
        if (wrap) wrap.style.display = 'block';
        if (bar) bar.style.width = `${data.percent}%`;
        if (text) text.textContent = data.status;
        if (btn) {
            btn.innerHTML = `${data.percent}%`;
            btn.disabled = true;
        }
    }

    handleUpdateComplete(data) {
        const btn = document.getElementById('btn-check-update');
        const status = document.getElementById('update-status');
        const bar = document.getElementById('update-progress-bar');

        if (bar) bar.style.width = '100%';

        if (data.success) {
            if (status) {
                status.textContent = 'Update installed! Restart to apply.';
                status.style.color = '#50fa7b';
            }
            if (btn) {
                btn.innerHTML = 'Restart Now';
                btn.dataset.action = 'restart';
                btn.disabled = false;
            }
        } else {
            if (status) {
                status.textContent = data.message || 'Update failed.';
                status.style.color = '#ff5555';
            }
            if (btn) {
                btn.innerHTML = 'Retry';
                btn.dataset.action = 'check';
                btn.disabled = false;
            }
            const wrap = document.getElementById('update-progress-wrap');
            if (wrap) wrap.style.display = 'none';
        }
    }

    handleReleaseHistoryResult(releases) {
        const list = document.getElementById('rollbacks-list');
        if (!list) return;

        if (!releases || releases.length === 0) {
            list.innerHTML = '<div style="text-align: center; color: #ff5555; font-size: 11px; padding: 12px;">Failed to fetch releases.</div>';
            return;
        }

        list.innerHTML = '';
        releases.forEach(r => {
            const item = document.createElement('div');
            item.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.05);';
            
            const info = document.createElement('div');
            const dt = r.date ? new Date(r.date).toLocaleDateString() : 'Unknown date';
            const badge = r.prerelease ? '<span style="background: rgba(255,184,108,0.2); color: #ffb86c; padding: 2px 6px; border-radius: 4px; font-size: 9px; margin-left: 6px;">Pre-release</span>' : '';
            
            info.innerHTML = `
                <div style="font-size: 12px; font-weight: 500; color: var(--text);">v${r.version} ${badge}</div>
                <div style="font-size: 10px; color: var(--text-dim); margin-top: 2px;">${dt}</div>
            `;
            item.appendChild(info);

            const dlBtn = document.createElement('button');
            dlBtn.className = 'themed-btn';
            dlBtn.style.cssText = 'padding: 4px 12px; font-size: 11px; height: auto; min-height: 24px;';
            dlBtn.textContent = 'Install';
            
            const currentVersion = this.getConfig() && this.getConfig().app_version ? this.getConfig().app_version : '';
            
            if (r.version === currentVersion) {
                dlBtn.disabled = true;
                dlBtn.textContent = 'Current';
            } else if (!r.download_url) {
                dlBtn.disabled = true;
                dlBtn.textContent = 'No Asset';
            } else {
                dlBtn.onclick = () => {
                    const status = document.getElementById('update-status');
                    if (status) status.textContent = `Downgrading to v${r.version}...`;
                    dlBtn.disabled = true;
                    dlBtn.textContent = 'Installing...';
                    if (window.sendCustomCommand) {
                        window.sendCustomCommand({ type: 'apply_rollback', download_url: r.download_url });
                    }
                };
            }
            item.appendChild(dlBtn);
            list.appendChild(item);
        });
    }

    updateUI(cfg) {
        const gen = cfg.general_settings || {};
        setCheckboxValue('#set-launch-startup input', gen.launch_at_startup === true);
        setCheckboxValue('#set-open-dash-startup input', gen.open_dashboard_startup === true);
        
        setInputValue('#set-system-gpu-pref select', gen.gpu_preference !== undefined ? gen.gpu_preference.toString() : '0');
        setInputValue('#update-channel-select', gen.update_channel || 'stable');
        
        const gpuLabel = document.getElementById('system-gpu-name');
        if (gpuLabel) {
            gpuLabel.textContent = cfg.system_gpu_name || 'Default Hardware GPU';
        }

        // Update version display
        const verLabel = document.getElementById('update-current-ver');
        if (verLabel && cfg.app_version) {
            verLabel.textContent = 'v' + cfg.app_version;
        }
    }
}
module.exports = { SystemTab };
