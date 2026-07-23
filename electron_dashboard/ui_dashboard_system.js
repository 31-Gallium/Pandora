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
    }

    handleUpdateCheckResult(data) {
        const btn = document.getElementById('btn-check-update');
        const status = document.getElementById('update-status');
        if (!btn || !status) return;

        btn.disabled = false;

        if (data.error) {
            status.textContent = data.error;
            status.style.color = '#ff5555';
            btn.innerHTML = 'Retry';
            btn.dataset.action = 'check';
        } else if (data.available) {
            status.textContent = `v${data.latest_version} is available!`;
            status.style.color = '#50fa7b';
            btn.innerHTML = 'Update Now';
            btn.dataset.action = 'apply';
            this._pendingDownloadUrl = data.download_url;
        } else {
            status.textContent = 'You\'re up to date! ✓';
            status.style.color = '#50fa7b';
            btn.innerHTML = 'Check for Updates';
            btn.dataset.action = 'check';
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

    updateUI(cfg) {
        const gen = cfg.general_settings || {};
        setCheckboxValue('#set-launch-startup input', gen.launch_at_startup === true);
        setCheckboxValue('#set-open-dash-startup input', gen.open_dashboard_startup === true);
        
        setInputValue('#set-system-gpu-pref select', gen.gpu_preference !== undefined ? gen.gpu_preference.toString() : '0');
        
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
