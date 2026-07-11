const { ipcRenderer } = require('electron');

const screenWelcome = document.getElementById('screen-welcome');
const screenEula = document.getElementById('screen-eula');
const screenInstalling = document.getElementById('screen-installing');
const screenComplete = document.getElementById('screen-complete');

const btnNext = document.getElementById('btn-next');
const btnBack = document.getElementById('btn-back');
const btnInstall = document.getElementById('btn-install');
const btnFinish = document.getElementById('btn-finish');
const closeBtn = document.getElementById('close-btn');

const optStartup = document.getElementById('opt-startup');
const optDesktop = document.getElementById('opt-desktop');
const optLaunchNow = document.getElementById('opt-launchnow');
const optAccept = document.getElementById('opt-accept');

const progressFill = document.getElementById('progress-fill');
const statusText = document.getElementById('status-text');

closeBtn.addEventListener('click', () => {
  ipcRenderer.send('close-installer');
});

function showScreen(screen) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  screen.classList.add('active');
}

btnNext.addEventListener('click', () => {
  showScreen(screenEula);
});

btnBack.addEventListener('click', () => {
  showScreen(screenWelcome);
});

optAccept.addEventListener('change', (e) => {
  if (e.target.checked) {
    btnInstall.disabled = false;
    btnInstall.style.opacity = '1';
    btnInstall.style.cursor = 'pointer';
  } else {
    btnInstall.disabled = true;
    btnInstall.style.opacity = '0.5';
    btnInstall.style.cursor = 'not-allowed';
  }
});

btnInstall.addEventListener('click', () => {
  showScreen(screenInstalling);
  
  // Start fake progress
  let progress = 0;
  const interval = setInterval(() => {
    progress += Math.random() * 15;
    if (progress > 95) progress = 95; // Wait for complete signal
    progressFill.style.width = `${progress}%`;
    
    if (progress > 20) statusText.innerText = "Copying files...";
    if (progress > 50) statusText.innerText = "Creating shortcuts...";
    if (progress > 80) statusText.innerText = "Finalizing...";
  }, 400);

  ipcRenderer.send('start-install', {
    startup: optStartup.checked,
    desktop: optDesktop.checked
  });

  ipcRenderer.once('install-complete', () => {
    clearInterval(interval);
    progressFill.style.width = '100%';
    statusText.innerText = "Done.";
    
    setTimeout(() => {
      showScreen(screenComplete);
    }, 600);
  });
});

btnFinish.addEventListener('click', () => {
  ipcRenderer.send('close-installer', {
    launchNow: optLaunchNow.checked
  });
});
