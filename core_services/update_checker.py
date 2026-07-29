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

    def __init__(self, current_version, update_channel="stable", parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self.update_channel = update_channel

    def run(self):
        try:
            if self.update_channel == "prerelease":
                api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
            else:
                api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

            req = Request(api_url, headers={
                'User-Agent': 'Pandora-Update-Checker',
                'Accept': 'application/vnd.github.v3+json'
            })
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                
            if isinstance(data, list):
                if not data:
                    self.result.emit({'available': False, 'error': 'No releases found.'})
                    return
                data = data[0]

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


class ReleaseHistoryFetcher(QThread):
    """Fetches the last N releases for version rollback."""
    result = pyqtSignal(list)

    def run(self):
        try:
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
            req = Request(api_url, headers={
                'User-Agent': 'Pandora-Update-Checker',
                'Accept': 'application/vnd.github.v3+json'
            })
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            
            releases = []
            for r in data[:15]:
                dl_url = None
                for asset in r.get('assets', []):
                    if asset.get('name', '').lower().endswith('.zip'):
                        dl_url = asset.get('browser_download_url')
                        break
                
                releases.append({
                    'version': r.get('tag_name', '').lstrip('v'),
                    'name': r.get('name', ''),
                    'prerelease': r.get('prerelease', False),
                    'date': r.get('published_at', ''),
                    'download_url': dl_url
                })
            self.result.emit(releases)
        except Exception as e:
            self.result.emit([])


class HTTPRangeFile:
    def __init__(self, url):
        self.url = url
        req = Request(self.url, method='HEAD')
        req.add_header('User-Agent', 'Pandora-Updater')
        # GitHub releases redirect to AWS S3 which supports range requests
        import urllib.request
        # We need a custom opener to catch the redirect URL to make range requests, 
        # or we can just use the url directly and let urlopen handle redirect on every range request.
        # Handling redirect on every request adds ~100ms latency per read.
        # Let's resolve the final URL once to optimize speed.
        try:
            with urlopen(req) as resp:
                self.final_url = resp.url
                self.size = int(resp.headers.get('Content-Length', 0))
        except Exception:
            self.final_url = self.url
            self.size = 0
            
        self.pos = 0

    def seek(self, offset, whence=0):
        if whence == 0: self.pos = offset
        elif whence == 1: self.pos += offset
        elif whence == 2: self.pos = self.size + offset
        return self.pos

    def tell(self): return self.pos

    def seekable(self): return True

    def read(self, size=-1):
        if size == -1: size = self.size - self.pos
        if size == 0: return b""
        end = self.pos + size - 1
        import time
        last_err = None
        for attempt in range(3):
            try:
                req = Request(self.final_url, headers={
                    'Range': f'bytes={self.pos}-{end}',
                    'User-Agent': 'Pandora-Updater'
                })
                with urlopen(req, timeout=30) as resp:
                    data = resp.read()
                self.pos += len(data)
                return data
            except Exception as e:
                last_err = e
                time.sleep(1 * (2 ** attempt))  # 1s, 2s, 4s
        raise last_err


class DifferentialUpdater(QThread):
    """Downloads and applies an update incrementally using HTTP Range requests."""
    progress = pyqtSignal(int, str)    # (percent, status_message)
    finished = pyqtSignal(bool, str)   # (success, message)

    def __init__(self, target_version, payload_url, parent=None):
        super().__init__(parent)
        self.target_version = target_version
        self.payload_url = payload_url
        self.localappdata_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), "Programs", "Pandora")

    def run(self):
        try:
            import hashlib
            import sys
            
            if getattr(sys, 'frozen', False):
                current_app_dir = os.path.dirname(sys.executable)
            else:
                current_app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
            new_app_dir = os.path.join(self.localappdata_dir, f"app-{self.target_version}")
            
            # Guard: never delete the directory we are currently running from
            current_norm = os.path.normcase(os.path.abspath(current_app_dir))
            new_norm = os.path.normcase(os.path.abspath(new_app_dir))
            if current_norm == new_norm:
                self.finished.emit(False, "You are already running this version.")
                return
            
            if os.path.exists(new_app_dir):
                shutil.rmtree(new_app_dir, ignore_errors=True)
            os.makedirs(new_app_dir, exist_ok=True)
            
            self.progress.emit(10, "Connecting to payload server...")
            hf = HTTPRangeFile(self.payload_url)
            
            self.progress.emit(15, "Parsing remote payload...")
            with zipfile.ZipFile(hf) as zip_ref:
                # 1. Read manifest from remote zip
                if 'manifest.json' in zip_ref.namelist():
                    manifest_data = zip_ref.read('manifest.json')
                    remote_manifest = json.loads(manifest_data.decode('utf-8'))
                else:
                    remote_manifest = None
                    
                total_files = len(zip_ref.namelist())
                completed_files = 0
                
                # 2. Diff and Download
                for file_info in zip_ref.infolist():
                    file_name = file_info.filename
                    target_path = os.path.join(new_app_dir, file_name)
                    
                    if file_info.is_dir():
                        os.makedirs(target_path, exist_ok=True)
                        continue
                        
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    reused = False
                    if remote_manifest and file_name in remote_manifest:
                        local_file = os.path.join(current_app_dir, file_name)
                        if os.path.exists(local_file):
                            hasher = hashlib.sha256()
                            with open(local_file, 'rb') as f:
                                while chunk := f.read(8192):
                                    hasher.update(chunk)
                            if hasher.hexdigest() == remote_manifest[file_name]:
                                try:
                                    os.link(local_file, target_path)
                                    reused = True
                                except Exception:
                                    shutil.copy2(local_file, target_path)
                                    reused = True
                    
                    if not reused:
                        pct = 15 + int(80 * (completed_files / max(1, total_files)))
                        self.progress.emit(pct, f"Downloading {file_name}...")
                        data = zip_ref.read(file_name)
                        with open(target_path, 'wb') as f:
                            f.write(data)
                            
                    completed_files += 1

            self.progress.emit(98, "Preparing restart...")
            
            # Copy the launcher out to root, just in case
            root_launcher = os.path.join(self.localappdata_dir, 'Pandora.exe')
            extracted_launcher = os.path.join(new_app_dir, 'Pandora.exe')
            if os.path.exists(extracted_launcher):
                try:
                    shutil.copy2(extracted_launcher, root_launcher)
                except Exception:
                    pass

            # Clean up old app-* version folders to prevent disk bloat
            try:
                current_app_name = os.path.basename(new_app_dir)
                for entry in os.listdir(self.localappdata_dir):
                    if entry.startswith('app-') and entry != current_app_name:
                        old_dir = os.path.join(self.localappdata_dir, entry)
                        if os.path.isdir(old_dir):
                            shutil.rmtree(old_dir, ignore_errors=True)
            except Exception:
                pass

            self.finished.emit(True, "Update ready for restart.")

        except Exception as e:
            logger.error(f"Differential update failed: {e}")
            self.finished.emit(False, str(e))
