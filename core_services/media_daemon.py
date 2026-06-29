import asyncio
import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtGui import QImage

@dataclass
class MediaState:
    title: str = ""
    artist: str = ""
    album: str = ""
    status: str = "Stopped"
    position: float = 0.0
    duration: float = 0.0
    sync_time: float = 0.0
    app_id: str = ""
    session_id: str = ""
    can_pause: bool = False
    can_play: bool = False
    can_skip_next: bool = False
    can_skip_prev: bool = False
    has_thumbnail: bool = False
    is_thumbnail_loading: bool = False
    thumb_id: str = ""
    app_volume: float = 1.0
    audio_peak: float = 0.0
    available_sessions: list = field(default_factory=list)

class MediaDaemon(QObject):
    state_changed = pyqtSignal(dict)
    thumbnail_ready = pyqtSignal(QImage)

    def __init__(self):
        super().__init__()
        self.state = MediaState()
        self.thumbnail: Optional[QImage] = None
        self._thumb_cache = {}
        
        self._manager = None
        self._current_session = None
        self._last_synced_session_id = ""
        self._manual_session_id = None
        self._playback_token = None
        self._media_token = None
        self._timeline_token = None
        self._manual_app_id = None

        self._loop = None
        self._thread = None
        self._last_cmd_time = 0.0
        self._last_vol_change_time = 0.0
        
        self.preferred_apps = ["Spotify.exe", "SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify", "AppleMusic.exe", "Music.UI"]
        
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def _run_event_loop(self):
        try:
            import winsdk._winrt
            winsdk._winrt.init_apartment(winsdk._winrt.MTA)
        except Exception as e:
            print(f"[MediaDaemon] Failed to init UWP MTA apartment: {e}")
            
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._init_gsm())
        self._loop.run_forever()

    async def _init_gsm(self):
        try:
            from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as SessionManager
            self._manager = await SessionManager.request_async()
            self._manager.add_sessions_changed(self._on_sessions_changed)
            await self._refresh_sessions()
            # Start polling loops
            self._loop.create_task(self._main_loop())
            # Peak polling runs on its own dedicated thread to avoid
            # cross-apartment COM marshalling deadlocks.
            self._peak_thread = threading.Thread(target=self._peak_polling_thread, daemon=True)
            self._peak_thread.start()
        except Exception as e:
            print(f"[MediaDaemon] Initialization failed: {e}")

    async def _main_loop(self):
        while True:
            await self._refresh_sessions()
            await self._sync_timeline()
            await self._sync_app_volume()
            await asyncio.sleep(1.0)

    def _peak_polling_thread(self):
        """Dedicated thread for all COM audio-peak work.
        
        COM objects are apartment-threaded: they MUST be created and used
        on the same thread.  Running everything here avoids the cross-
        apartment marshalling deadlock that occurs when a meter created
        in run_in_executor is later called from the asyncio loop thread.
        """
        import pythoncom
        from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
        from comtypes import CLSCTX_ALL
        pythoncom.CoInitialize()

        master_meter = None

        while True:
            try:
                if self._current_session and self.state.status == "Playing":
                    if master_meter is None:
                        try:
                            devices = AudioUtilities.GetSpeakers()
                            interface = devices.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
                            master_meter = interface.QueryInterface(IAudioMeterInformation)
                        except Exception:
                            pass
                            
                    if master_meter:
                        try:
                            self.state.audio_peak = master_meter.GetPeakValue()
                        except Exception:
                            master_meter = None
                            self.state.audio_peak = 0.0
                    else:
                        self.state.audio_peak = 0.0
                else:
                    self.state.audio_peak = 0.0
            except Exception:
                self.state.audio_peak = 0.0
                master_meter = None

            time.sleep(0.03)


    def _on_sessions_changed(self, manager, args=None):
        asyncio.run_coroutine_threadsafe(self._refresh_sessions(), self._loop)

    def _get_best_session(self):
        if not self._manager: return None
        try:
            sessions = self._manager.get_sessions()
            if not sessions: return self._manager.get_current_session()
            
            best = None
            best_score = -1
            
            for s in sessions:
                try:
                    app_id = s.source_app_user_model_id or ""
                    info = s.get_playback_info()
                    is_playing = info and hasattr(info, 'playback_status') and info.playback_status and info.playback_status.value == 4
                    
                    score = 0
                    if is_playing: score += 10
                    
                    for i, pref in enumerate(self.preferred_apps):
                        if pref.lower() in app_id.lower():
                            score += (100 - i)
                            break
                            
                    if score > best_score:
                        best_score = score
                        best = s
                except Exception:
                    pass
            
            return best or self._manager.get_current_session()
        except Exception:
            return None

    async def _refresh_sessions(self):
        try:
            if not self._manager:
                from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
                self._manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
                self._manager.add_sessions_changed(self._on_sessions_changed)
            
            manager = self._manager
            all_sessions = manager.get_sessions()
            import uuid
            available = []
            old_unmatched = self.state.available_sessions.copy()
            
            for s in all_sessions:
                try:
                    app_id = s.source_app_user_model_id or ""
                    # Grab titles for identification with a timeout to prevent hanging on suspended apps
                    info = await asyncio.wait_for(s.try_get_media_properties_async(), timeout=1.0)
                    title = info.title if info else app_id
                except:
                    app_id = s.source_app_user_model_id or ""
                    title = "Unknown"
                    
                best_match_idx = -1
                for i, old_s in enumerate(old_unmatched):
                    if old_s['app_id'] == app_id and old_s['title'] == title:
                        best_match_idx = i
                        break
                        
                if best_match_idx != -1:
                    session_id = old_unmatched[best_match_idx]['session_id']
                    old_unmatched.pop(best_match_idx)
                else:
                    session_id = str(uuid.uuid4())
                    
                available.append({"app_id": app_id, "session_id": session_id, "title": title, "_session": s})
            
            self.state.available_sessions = available
            
            new_session_dict = None
            if self._manual_session_id:
                for s in available:
                    if s['session_id'] == self._manual_session_id:
                        new_session_dict = s
                        break
                if not new_session_dict:
                    self._manual_session_id = None # Fallback if manual session died
                else:
                    # Chrome sometimes creates a new SMTC session for the next track and leaves the old one paused.
                    # If our locked session is not playing, but another session from the same app is playing, migrate to it!
                    info = new_session_dict['_session'].get_playback_info()
                    if not info or info.playback_status != 4: # 4 = Playing
                        for s in available:
                            s_info = s['_session'].get_playback_info()
                            if s['app_id'] == new_session_dict['app_id'] and s_info and s_info.playback_status == 4:
                                new_session_dict = s
                                self._manual_session_id = s['session_id']
                                break
                    
            if not new_session_dict:
                best_s = self._get_best_session()
                if best_s:
                    best_app_id = best_s.source_app_user_model_id or ""
                    for s in available:
                        if s['app_id'] == best_app_id:
                            new_session_dict = s
                            break
                            
            if new_session_dict:
                new_session = new_session_dict['_session']
                new_session_id = new_session_dict['session_id']
            else:
                new_session = None
                new_session_id = ""
            
            if new_session_id != self.state.session_id:
                if self._current_session:
                    try:
                        if self._playback_token: self._current_session.remove_playback_info_changed(self._playback_token)
                        if self._media_token: self._current_session.remove_media_properties_changed(self._media_token)
                        if self._timeline_token: self._current_session.remove_timeline_properties_changed(self._timeline_token)
                    except: pass
                
                self._current_session = new_session
                self.state.session_id = new_session_id
                if self._current_session:
                    self._playback_token = self._current_session.add_playback_info_changed(self._on_playback_changed)
                    self._media_token = self._current_session.add_media_properties_changed(self._on_media_changed)
                    self._timeline_token = self._current_session.add_timeline_properties_changed(self._on_timeline_changed)
            
            await self._sync_full_state()
        except: pass

    def switch_session(self, direction=1):
        asyncio.run_coroutine_threadsafe(self._switch_session_async(direction), self._loop)

    async def _switch_session_async(self, direction=1):
        if not self.state.available_sessions: return
        
        idx = -1
        for i, s in enumerate(self.state.available_sessions):
            if s['session_id'] == self.state.session_id:
                idx = i
                break
                
        if idx == -1: idx = 0
        else: idx = (idx + direction) % len(self.state.available_sessions)
        
        new_s = self.state.available_sessions[idx]['_session']
        if new_s:
            self._manual_session_id = self.state.available_sessions[idx]['session_id']
            await self._refresh_sessions()

    def set_session_by_id(self, app_id):
        asyncio.run_coroutine_threadsafe(self._set_session_by_id_async(app_id), self._loop)

    async def _set_session_by_id_async(self, app_id):
        for s in self.state.available_sessions:
            if s['app_id'] == app_id:
                new_s = s['_session']
                if new_s:
                    self._manual_app_id = app_id
                    if self._current_session:
                        try:
                            if self._playback_token: self._current_session.remove_playback_info_changed(self._playback_token)
                            if self._media_token: self._current_session.remove_media_properties_changed(self._media_token)
                            if self._timeline_token: self._current_session.remove_timeline_properties_changed(self._timeline_token)
                        except: pass
                    self._current_session = new_s
                    try:
                        self._playback_token = self._current_session.add_playback_info_changed(self._on_playback_changed)
                        self._media_token = self._current_session.add_media_properties_changed(self._on_media_changed)
                        self._timeline_token = self._current_session.add_timeline_properties_changed(self._on_timeline_changed)
                    except: pass
                    await self._sync_full_state()
                break

    def _on_playback_changed(self, session, args=None):
        if session != self._current_session: return
        asyncio.run_coroutine_threadsafe(self._sync_playback_state(), self._loop)

    def _on_media_changed(self, session, args=None):
        if session != self._current_session: return
        asyncio.run_coroutine_threadsafe(self._sync_media_properties(), self._loop)

    def _on_timeline_changed(self, session, args=None):
        if session != self._current_session: return
        asyncio.run_coroutine_threadsafe(self._sync_timeline(), self._loop)

    async def _sync_full_state(self):
        if not self._current_session:
            self.state = MediaState(title="No Media")
            self.thumbnail = None
            self._emit_update()
            return
            
        await self._sync_media_properties()
        await self._sync_playback_state()
        await self._sync_timeline()

    async def _sync_playback_state(self):
        if not self._current_session: return
        
        # Suppress polling if user manually changed play state recently to prevent bounce
        if time.time() - self._last_cmd_time < 0.6:
            return
            
        try:
            info = self._current_session.get_playback_info()
        except Exception:
            self._current_session = None
            return
            
        try:
            new_status = "Playing" if info.playback_status.value == 4 else "Paused"
            can_pause = False
            can_play = False
            can_skip_next = False
            can_skip_prev = False
            
            if hasattr(info, 'controls') and info.controls:
                can_pause = info.controls.is_pause_enabled
                can_play = info.controls.is_play_enabled
                can_skip_next = info.controls.is_next_enabled
                can_skip_prev = info.controls.is_previous_enabled
            
            # Fetch exact timeline right before pausing/playing/skipping
            try:
                timeline = self._current_session.get_timeline_properties()
                new_pos = timeline.position.total_seconds()
                new_dur = timeline.end_time.total_seconds()
            except:
                new_pos = self.state.position
                new_dur = self.state.duration
            
            # Always update timeline if it changed significantly, or if status changed
            status_changed = self.state.status != new_status
            pos_changed = abs(new_pos - self.state.position) > 1.0
            
            if status_changed or pos_changed or self.state.can_pause != can_pause:
                self.state.status = new_status
                self.state.can_pause = can_pause
                self.state.can_play = can_play
                self.state.can_skip_next = can_skip_next
                self.state.can_skip_prev = can_skip_prev
                self.state.position = new_pos
                self.state.duration = new_dur
                self.state.sync_time = time.time()
                self._emit_update()
        except: pass

    async def _sync_media_properties(self):
        if not self._current_session: return
        try:
            # Wrap properties retrieval with a timeout to prevent blocking on suspended apps
            props = await asyncio.wait_for(self._current_session.try_get_media_properties_async(), timeout=1.0)
            new_title = props.title if props.title else ""
            new_artist = props.artist if props.artist else ""
            new_album = props.album_title if props.album_title else ""
            
            just_switched_session = self.state.session_id != self._last_synced_session_id
            
            track_changed = (not just_switched_session) and (self.state.title != new_title or 
                           self.state.artist != new_artist or 
                           self.state.album != new_album)
                           
            self.state.app_id = self._current_session.source_app_user_model_id or ""
            
            if track_changed:
                import uuid
                new_session_id = str(uuid.uuid4())
                
                for s in self.state.available_sessions:
                    if s.get('session_id') == self._last_synced_session_id:
                        s['session_id'] = new_session_id
                        s['title'] = new_title
                        break
                        
                if self._manual_session_id == self._last_synced_session_id:
                    self._manual_session_id = new_session_id
            else:
                new_session_id = self.state.session_id
            
            session_changed = new_session_id != self._last_synced_session_id
            thumbnail_arrived = (not self.state.has_thumbnail) and (props.thumbnail is not None)
            
            # Update state if track changed, session changed, or we finally received a thumbnail
            if track_changed or session_changed or thumbnail_arrived:
                self._last_synced_session_id = new_session_id
                self.state.session_id = new_session_id
                
                self.state.title = new_title
                self.state.artist = new_artist
                self.state.album = new_album
                self.state.app_id = self._current_session.source_app_user_model_id or ""
                self.state.sync_time = time.time()
                
                # Scope thumb_id to the unique session UUID to prevent cross-contamination between identical titles/apps
                thumb_id = f"{new_session_id}_{new_title}_{new_artist}_{new_album}"
                self.state.thumb_id = thumb_id
                
                self.state.position = 0.0
                if thumb_id in self._thumb_cache:
                    self.thumbnail = self._thumb_cache[thumb_id]
                    self.state.has_thumbnail = True
                    self.state.is_thumbnail_loading = False
                    self._emit_update()
                    self.thumbnail_ready.emit(self.thumbnail)
                else:
                    self.thumbnail = None
                    self.state.has_thumbnail = False
                    self.state.is_thumbnail_loading = True
                    self._emit_update()
                    asyncio.create_task(self._safe_extract_thumbnail(props, thumb_id))
        except: pass

    async def _sync_timeline(self):
        if not self._current_session: return
        try:
            timeline = self._current_session.get_timeline_properties()
            if not timeline: return
            
            def get_sec(ts):
                if hasattr(ts, 'total_seconds'): return ts.total_seconds()
                return float(ts) / 10000000.0 # Ticks to seconds
            
            pos = get_sec(timeline.position)
            dur = get_sec(timeline.end_time)
            
            # winsdk position is a STATIC SNAPSHOT. 
            # We must interpolate using last_updated_time to get the 'true' current position.
            if self.state.status == "Playing" and hasattr(timeline, 'last_updated_time'):
                from datetime import datetime, timezone
                last_upd = timeline.last_updated_time
                now = datetime.now(timezone.utc) if last_upd.tzinfo else datetime.utcnow()
                elapsed = (now - last_upd).total_seconds()
                if elapsed > 0:
                    pos = min(dur, pos + elapsed)

            # Sync Position
            self.state.position = pos
            self.state.duration = dur
            self.state.sync_time = time.time()
            self._emit_update()
        except: pass

    async def _sync_app_volume(self):
        if not self.state.app_id: return
        
        # Suppress polling if user manually changed volume recently (within 2.5s)
        if time.time() - self._last_vol_change_time < 2.5:
            return
        
        def _get_vol():
            try:
                import pythoncom
                from pycaw.pycaw import AudioUtilities
                pythoncom.CoInitialize()
                sessions = AudioUtilities.GetAllSessions()
                target = self.state.app_id.lower()
                for session in sessions:
                    if session.Process:
                        name = session.Process.name().lower()
                        if name.replace(".exe","") in target or target in name:
                            return session.SimpleAudioVolume.GetMasterVolume()
            except: pass
            return None

        vol = await self._loop.run_in_executor(None, _get_vol)
        if vol is not None:
            if abs(self.state.app_volume - vol) > 0.01:
                self.state.app_volume = vol
                self._emit_update()

    async def _safe_extract_thumbnail(self, props, thumb_id):
        try:
            thumb_ref = props.thumbnail
            if not thumb_ref:
                # Some apps (like Spotify) send the track metadata first, then the thumbnail 100-300ms later.
                # Hold `is_thumbnail_loading` True for 0.5s to prevent flashing the app icon during this gap.
                await asyncio.sleep(0.5)
                if self._current_session:
                    try:
                        props = await asyncio.wait_for(self._current_session.try_get_media_properties_async(), timeout=0.5)
                        thumb_ref = props.thumbnail
                    except: pass
                    
                if not thumb_ref:
                    if thumb_id == self.state.thumb_id:
                        self.thumbnail = None
                        self.state.has_thumbnail = False
                        self.state.is_thumbnail_loading = False
                        self._emit_update()
                    return

            await asyncio.wait_for(self._extract_thumbnail_internal(thumb_ref, thumb_id), timeout=1.5)
        except:
            if thumb_id == self.state.thumb_id:
                self.thumbnail = None
                self.state.has_thumbnail = False
                self.state.is_thumbnail_loading = False
                self._emit_update()

    async def _extract_thumbnail_internal(self, thumb_ref, thumb_id):
        try:
            stream = await thumb_ref.open_read_async()
            size = stream.size
            if size <= 0: return

            from winsdk.windows.storage.streams import DataReader
            reader = DataReader(stream)
            await reader.load_async(size)
            
            buf = bytearray(size)
            reader.read_bytes(buf)

            img = QImage()
            if img.loadFromData(bytes(buf)):
                self._thumb_cache[thumb_id] = img
                if len(self._thumb_cache) > 20:
                    self._thumb_cache.pop(next(iter(self._thumb_cache)))
                    
                if thumb_id == self.state.thumb_id:
                    self.thumbnail = img
                    self.state.has_thumbnail = True
                    self.state.is_thumbnail_loading = False
                    self._emit_update()
                    self.thumbnail_ready.emit(self.thumbnail)
        except: 
            if thumb_id == self.state.thumb_id:
                self.state.is_thumbnail_loading = False

    def _emit_update(self):
        self.state_changed.emit(self._emit_update_as_dict())

    def _emit_update_as_dict(self):
        return {
            "title": self.state.title,
            "artist": self.state.artist,
            "album": self.state.album,
            "status": self.state.status,
            "position": self.state.position,
            "duration": self.state.duration,
            "sync_time": self.state.sync_time,
            "app_id": self.state.app_id,
            "session_id": self.state.session_id,
            "controls": {
                "pause": self.state.can_pause,
                "play": self.state.can_play,
                "next": self.state.can_skip_next,
                "prev": self.state.can_skip_prev
            },
            "has_thumbnail": self.state.has_thumbnail,
            "is_thumbnail_loading": self.state.is_thumbnail_loading,
            "thumb_id": self.state.thumb_id,
            "app_volume": self.state.app_volume,
            "available_sessions": self.state.available_sessions
        }

    def notify_vol_change(self, new_vol):
        self._last_vol_change_time = time.time()
        self.state.app_volume = new_vol

    def play_pause(self):
        now = time.time()
        if now - self._last_cmd_time < 0.6: return
        self._last_cmd_time = now
        
        if self._current_session:
            # Eagerly update status to stop interpolation immediately in UI
            if self.state.status == "Playing":
                # Estimate current position to prevent "snap back" to last sync
                if self.state.sync_time > 0:
                    elapsed = time.time() - self.state.sync_time
                    self.state.position = min(self.state.duration, self.state.position + elapsed)
                self.state.status = "Paused"
                self.state.sync_time = time.time()
            else:
                self.state.status = "Playing"
                self.state.sync_time = time.time() # Reset sync time for fresh interpolation
            self._emit_update()
            
            async def _do():
                try: 
                    await self._current_session.try_toggle_play_pause_async()
                    # Follow up with real sync to confirm state
                    await asyncio.sleep(0.2)
                    await self._sync_playback_state()
                except: pass
            asyncio.run_coroutine_threadsafe(_do(), self._loop)

    def next_track(self):
        if self._current_session:
            async def _do():
                try: await self._current_session.try_skip_next_async()
                except: pass
            asyncio.run_coroutine_threadsafe(_do(), self._loop)

    def prev_track(self):
        if self._current_session:
            async def _do():
                try: await self._current_session.try_skip_previous_async()
                except: pass
            asyncio.run_coroutine_threadsafe(_do(), self._loop)
