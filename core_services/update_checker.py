import os
import json
import shutil
import zipfile
import tempfile
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from PyQt6.QtCore import QThread, pyqtSignal
from config import APPDATA_DIR, CONFIG_PATH, logger

GITHUB_REPO = "31-Gallium/Pandora"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(version_str):
    """Parse a version string like 'v0.9.1' or '0.9.1' into a tuple of ints."""
    v = version_str.strip().lstrip('v')
    parts = []
    for p in v.split('.'):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


class UpdateChecker(QThread):
    """Checks GitHub Releases for a newer version."""
    result = pyqtSignal(dict)  # {available, latest_version, download_url, notes, error}

    def __init__(self, current_version, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        try:
            req = Request(GITHUB_API_URL, headers={
                'User-Agent': 'Pandora-Update-Checker',
                'Accept': 'application/vnd.github.v3+json'
            })
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            latest_tag = data.get('tag_name', '')
            release_notes = data.get('body', '')
            
            # Find the payload.zip asset
            download_url = None
            for asset in data.get('assets', []):
                if asset.get('name', '').lower().endswith('.zip'):
                    download_url = asset.get('browser_download_url')
                    break

            current = _parse_version(self.current_version)
            latest = _parse_version(latest_tag)
            is_newer = latest > current

            self.result.emit({
                'available': is_newer,
                'latest_version': latest_tag.lstrip('v'),
                'download_url': download_url or '',
                'notes': release_notes,
                'error': None
            })

        except HTTPError as e:
            if e.code == 403:
                self.result.emit({'available': False, 'error': 'GitHub API rate limit reached. Try again later.'})
            elif e.code == 404:
                self.result.emit({'available': False, 'error': 'No releases found.'})
            else:
                self.result.emit({'available': False, 'error': f'HTTP error: {e.code}'})
        except URLError as e:
            self.result.emit({'available': False, 'error': f'Network error: {e.reason}'})
        except Exception as e:
            self.result.emit({'available': False, 'error': str(e)})


class UpdateWorker(QThread):
    """Downloads and applies an update from a GitHub release asset."""
    progress = pyqtSignal(int, str)    # (percent, status_message)
    finished = pyqtSignal(bool, str)   # (success, message)

    def __init__(self, download_url, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.install_dir = os.path.join(
            os.environ.get('LOCALAPPDATA', os.path.expanduser('~')),
            "Programs", "Pandora"
        )

    def run(self):
        tmp_zip = None
        try:
            # Step 1: Backup config
            self.progress.emit(5, "Backing up settings...")
            config_bak = CONFIG_PATH + '.bak'
            if os.path.exists(CONFIG_PATH):
                shutil.copy2(CONFIG_PATH, config_bak)
                logger.info(f"Config backed up to {config_bak}")

            # Step 2: Download the update zip
            self.progress.emit(10, "Downloading update...")
            req = Request(self.download_url, headers={
                'User-Agent': 'Pandora-Updater'
            })
            
            with urlopen(req, timeout=120) as resp:
                total = int(resp.headers.get('Content-Length', 0))
                tmp_fd, tmp_zip = tempfile.mkstemp(suffix='.zip')
                
                downloaded = 0
                with os.fdopen(tmp_fd, 'wb') as f:
                    while True:
                        chunk = resp.read(65536)  # 64KB chunks
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = 10 + int((downloaded / total) * 60)  # 10-70%
                            self.progress.emit(pct, f"Downloading... {downloaded // 1024}KB / {total // 1024}KB")
                        else:
                            self.progress.emit(40, f"Downloading... {downloaded // 1024}KB")

            # Step 3: Validate the zip
            self.progress.emit(72, "Verifying download...")
            if not zipfile.is_zipfile(tmp_zip):
                self.finished.emit(False, "Downloaded file is not a valid zip archive.")
                return

            # Step 4: Extract to install directory
            self.progress.emit(75, "Installing update...")
            if not os.path.exists(self.install_dir):
                os.makedirs(self.install_dir)

            with zipfile.ZipFile(tmp_zip, 'r') as zf:
                file_list = zf.namelist()
                total_files = len(file_list)
                for i, file in enumerate(file_list):
                    zf.extract(file, self.install_dir)
                    if i % 20 == 0:
                        pct = 75 + int((i / max(total_files, 1)) * 20)  # 75-95%
                        self.progress.emit(pct, f"Extracting files... ({i}/{total_files})")

            # Step 5: Verify config was not touched
            self.progress.emit(96, "Verifying settings...")
            if os.path.exists(CONFIG_PATH):
                logger.info("Config file intact after update")
            elif os.path.exists(config_bak):
                # Restore from backup if somehow lost
                shutil.copy2(config_bak, CONFIG_PATH)
                logger.warning("Config restored from backup")

            self.progress.emit(100, "Update complete!")
            self.finished.emit(True, "Update installed successfully. Restart to apply.")
            logger.info("Update applied successfully")

        except Exception as e:
            logger.error(f"Update failed: {e}")
            self.finished.emit(False, f"Update failed: {e}")
        finally:
            # Cleanup temp file
            if tmp_zip and os.path.exists(tmp_zip):
                try:
                    os.remove(tmp_zip)
                except Exception:
                    pass
