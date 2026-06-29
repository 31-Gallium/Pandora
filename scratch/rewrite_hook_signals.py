import re

with open("c:/Users/Base/Desktop/Seb/Pandora/main.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update HookSignals
new_signals = """class HookSignals(QObject):
    press = pyqtSignal()
    release = pyqtSignal()
    mouse_move = pyqtSignal(object)
    mouse_wheel = pyqtSignal(int)
    key_event = pyqtSignal(object)
    cycle_layer = pyqtSignal(int)"""

code = re.sub(r'class HookSignals\(QObject\):\n    press = pyqtSignal\(\)\n    release = pyqtSignal\(\)', new_signals, code)

# 2. Update Custom Buttons (cycle_layer)
custom_btn_match1 = r"QTimer\.singleShot\(0, lambda: app\.halo\.hub_manager\.cycle_layer\(1\)\)"
custom_btn_match2 = r"QTimer\.singleShot\(0, lambda: app\.halo\.hub_manager\.cycle_layer\(-1\)\)"
code = re.sub(custom_btn_match1, "self.signals.cycle_layer.emit(1)", code)
code = re.sub(custom_btn_match2, "self.signals.cycle_layer.emit(-1)", code)

# 3. Update Spacebar route
space_block = r"QTimer\.singleShot\(0, lambda et=etype: QApplication\.postEvent\(app\.halo, QKeyEvent\(et, Qt\.Key\.Key_Space, Qt\.KeyboardModifier\.NoModifier\)\)\)"
new_space_block = """key_event = QKeyEvent(etype, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
                                self.signals.key_event.emit(key_event)"""
code = re.sub(space_block, new_space_block, code)

# 4. Update Mouse Wheel
wheel_block = r"QTimer\.singleShot\(0, lambda d=delta: app\.halo\.handle_wheel\(d\)\)"
code = re.sub(wheel_block, "self.signals.mouse_wheel.emit(delta)", code)

# 5. Connect signals
signal_connections = """    signals.press.connect(halo.show_center)
    signals.release.connect(halo.execute_current)"""
new_signal_connections = """    signals.press.connect(halo.show_center)
    signals.release.connect(halo.execute_current)
    signals.mouse_wheel.connect(halo.handle_wheel)
    signals.cycle_layer.connect(halo.hub_manager.cycle_layer)
    
    def on_key_event_routed(ev):
        QApplication.postEvent(halo, ev)
        
    signals.key_event.connect(on_key_event_routed)"""
code = code.replace(signal_connections, new_signal_connections)

with open("c:/Users/Base/Desktop/Seb/Pandora/main.py", "w", encoding="utf-8") as f:
    f.write(code)

print("Patch applied.")
