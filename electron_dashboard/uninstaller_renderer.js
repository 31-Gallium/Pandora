const { ipcRenderer } = require('electron');

const btnCancel = document.getElementById('btn-cancel');
const btnUninstall = document.getElementById('btn-uninstall');
const btnClose = document.getElementById('btn-close-window');
const chkAppData = document.getElementById('chk-appdata');
const radioStorageOptions = document.getElementsByName('storage');
const storageDesc = document.getElementById('storage-desc');
const screenWelcome = document.getElementById('screen-welcome');
const screenUninstalling = document.getElementById('screen-uninstalling');
const progressFill = document.getElementById('progress-fill');

// Update dynamic description for storage options
radioStorageOptions.forEach(radio => {
    radio.addEventListener('change', (e) => {
        if (e.target.value === 'desktop') {
            storageDesc.innerText = "Moves your files to a 'Pandora_Backup' folder on your desktop.";
        } else if (e.target.value === 'delete') {
            storageDesc.innerText = "Permanently delete all internal storage files.";
        }
    });
});

btnCancel.addEventListener('click', () => {
    ipcRenderer.send('close-window');
});

btnClose.addEventListener('click', () => {
    ipcRenderer.send('close-window');
});

btnUninstall.addEventListener('click', () => {
    screenWelcome.style.opacity = '0';
    screenWelcome.style.pointerEvents = 'none';
    
    setTimeout(() => {
        screenUninstalling.classList.add('active');
        
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 95) progress = 95;
            progressFill.style.width = `${progress}%`;
        }, 400);

        let backupStorage = 'keep';
        for (const radio of radioStorageOptions) {
            if (radio.checked) {
                backupStorage = radio.value;
                break;
            }
        }

        const options = {
            deleteAppData: chkAppData.checked,
            backupStorage: backupStorage
        };

        // Delay enough to show animation
        setTimeout(() => {
            clearInterval(interval);
            progressFill.style.width = '100%';
            setTimeout(() => {
                ipcRenderer.send('execute-uninstall', options);
            }, 300);
        }, 1500);

    }, 400); // Wait for fade out
});
