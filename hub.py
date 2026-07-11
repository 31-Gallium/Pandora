"""
Hub Manager — orchestrates the central hub system.
Intelligently switches between MediaHub and TimeHub based on context.
"""
from PyQt6.QtCore import Qt
from hub_modules import MODULE_MAP, DefaultLogoHub

class HubManager:
    def __init__(self, halo):
        self.halo = halo
        
        # Instantiate the two primary hubs
        # We assume MODULE_MAP has "media" and "time"
        self.media_hub = MODULE_MAP.get("media", DefaultLogoHub)(self)
        self.time_hub = MODULE_MAP.get("time", DefaultLogoHub)(self)
        self.default_hub = DefaultLogoHub(self)
        
    def reload_config(self, cfg):
        self.cfg = cfg
        hub_cfg = cfg.get("hub_config", {})
        layers = hub_cfg.get("layers", [])
        
        media_settings = None
        time_settings = None
        for l in layers:
            if not l: continue
            if l.get('type') == 'media' and media_settings is None: 
                media_settings = l.get('settings', {})
            elif l.get('type') == 'time' and time_settings is None: 
                time_settings = l.get('settings', {})
                
        if media_settings is None: media_settings = {}
        if time_settings is None: time_settings = {}
        
        print("DEBUG RELOAD:", media_settings)        
        if hasattr(self.media_hub, 'load_settings'):
            self.media_hub.load_settings(media_settings)
        if hasattr(self.time_hub, 'load_settings'):
            self.time_hub.load_settings(time_settings)

    def get_active_module(self):
        """Returns MediaHub if track info exists, else TimeHub."""
        if hasattr(self.halo, 'media_mgr'):
            track = self.halo.media_mgr.current_track
            title = track.get("title", "")
            if title and title != "No Media":
                return self.media_hub
        return self.time_hub

    def draw_active(self, p, cx, cy, inner_radius):
        self.get_active_module().draw(p, cx, cy, inner_radius)

    def handle_scroll(self, pos, delta):
        mod = self.get_active_module()
        if hasattr(mod, "on_wheel"):
            if mod.on_wheel(delta):
                self.halo.update()
                return True
        return False

    def handle_mouse_move(self, pos):
        mod = self.get_active_module()
        if hasattr(mod, "on_mouse_move"):
            mod.on_mouse_move(pos)

    def handle_mouse_leave(self):
        mod = self.get_active_module()
        if hasattr(mod, "on_mouse_leave"):
            mod.on_mouse_leave()

    def handle_press(self, pos, button):
        mod = self.get_active_module()
        if hasattr(mod, "on_mouse_press"):
            mod.on_mouse_press(pos, button)
            self.halo.update()

    def handle_release(self, pos, button):
        mod = self.get_active_module()
        if hasattr(mod, "on_mouse_release"):
            mod.on_mouse_release(pos, button)
            self.halo.update()

    def handle_key_press(self, event):
        mod = self.get_active_module()
        if hasattr(mod, "on_key_press"):
            if mod.on_key_press(event):
                self.halo.update()
                return True
        return False

    def handle_key_release(self, event):
        mod = self.get_active_module()
        if hasattr(mod, "on_key_release"):
            if mod.on_key_release(event):
                self.halo.update()
                return True
        return False
