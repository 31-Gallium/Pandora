class BaseHubModule:
    """Base class for all Hub HUD modules."""
    def __init__(self, manager):
        self.manager = manager
        self.settings = {}

    def load_settings(self, settings):
        self.settings = settings or {}

    def draw(self, p, cx, cy, inner_radius):
        """Override to render module content inside the radial center."""
        pass

    def on_mouse_press(self, pos, button):
        pass

    def on_mouse_release(self, pos, button):
        pass

    def on_wheel(self, delta):
        return False

    def cleanup(self):
        """Called when the module is unloaded."""
        pass
