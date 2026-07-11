const { bindInput, setCheckboxValue } = require('./ui_dashboard_common.js');

class SystemTab {
    constructor(getConfig, sendUpdate) {
        this.getConfig = getConfig;
        this.sendUpdate = sendUpdate;
    }

    init() {
        bindInput('#set-launch-startup input', 'general_settings.launch_at_startup', false, this.getConfig, this.sendUpdate);
        
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
    }
}
module.exports = { SystemTab };
