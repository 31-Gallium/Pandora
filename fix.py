with open('c:\\\\Users\\\\Base\\\\Desktop\\\\Seb\\\\Pandora\\\\ui\\\\halo.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if '        # 1. Volume override if hovering mute' in line:
        skip = True
        new_lines.append(line)
        new_lines.append("""        if self.active_index != -1 and self.active_index < len(self.current_tools):
            tool = self.current_tools[self.active_index]
            tid = tool.get('id', '').strip().lower()
            if tid == 'mute':
                from utils import change_system_volume, get_system_volume_level
                delta = 0.02 if delta_y > 0 else -0.02
                change_system_volume(delta)
                self.vol_level = get_system_volume_level()
                self.vol_target_opacity = 1.0; self.vol_opacity = 1.0
                self.vol_hud_val = int(self.vol_level * 100)
                self.vol_hud_dir = 'up' if delta > 0 else 'down'
                self.last_adjusted_id = tool['id']
                self.vol_fade_timer.start(1500)
                self.update(); return
            elif tid in ['night', 'night light']:
                try:
                    from utils import DisplayEffectsEngine
                    engine = DisplayEffectsEngine.instance()
                    delta = 0.05 if delta_y > 0 else -0.05
                    
                    if not engine._is_enabled:
                        if delta > 0:
                            engine.set_enabled(True, instant=True)
                            engine.set_intensity(0.0)
                        else:
                            return
                    
                    new_val = max(0.0, min(1.0, engine._target_intensity + delta))
                    
                    if new_val <= 0.001 and delta < 0:
                        engine.set_enabled(False)
                        self.vol_target_opacity = 0.0
                    else:
                        engine.set_intensity(new_val)
                        self.vol_level = new_val
                        self.vol_target_opacity = 1.0; self.vol_opacity = 1.0
                        self.vol_hud_val = int(new_val * 100)
                        self.vol_hud_dir = 'night_up' if delta > 0 else 'night_down'
                        self.last_adjusted_id = tool['id']
                        self.vol_fade_timer.start(1500)
                    
                    self.update(); return
                except Exception as e:
                    import traceback
                    with open('scroll_debug.txt', 'a') as df:
                        df.write('Error in night light: ' + str(e) + '\\n')
                    return

""")
        continue
    
    if skip and "if not hasattr(self, 'menus')" in line:
        skip = False
    
    if not skip:
        new_lines.append(line)

with open('c:\\\\Users\\\\Base\\\\Desktop\\\\Seb\\\\Pandora\\\\ui\\\\halo.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
