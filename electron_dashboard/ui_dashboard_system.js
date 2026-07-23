const { bindInput, setCheckboxValue, setInputValue } = require('./ui_dashboard_common.js');

class SystemTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
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
    }
}
module.exports = { SystemTab };
