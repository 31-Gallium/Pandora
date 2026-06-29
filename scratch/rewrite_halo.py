import re

with open('halo.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Fullscreen geometry in __init__
code = re.sub(
    r'self\.setFixedSize\(self\.outer_radius \* 2 \+ 100, self\.outer_radius \* 2 \+ 100\)',
    r'self.setGeometry(QApplication.primaryScreen().geometry())',
    code, count=1
)

# 2. reload_tools Geometry
code = re.sub(
    r'self\.setFixedSize\(self\.outer_radius \* 2 \+ 100, self\.outer_radius \* 2 \+ 100\)',
    r'self.setGeometry(QApplication.primaryScreen().geometry())',
    code, count=1
)

# 3. show_center
code = re.sub(
    r'self\.move\(pos\.x\(\) - self\.width\(\) // 2, pos\.y\(\) - self\.height\(\) // 2\)',
    r'self.setGeometry(screen)',
    code
)

# 4. _anim_loop - add fade_progress
code = re.sub(
    r'layer_anim = getattr\(self, \'layer_anim_progress\', 0\.0\)',
    r'layer_anim = getattr(self, "layer_anim_progress", 0.0)\n        if getattr(self, "closing", False):\n            self.fade_progress = max(0.0, getattr(self, "fade_progress", 1.0) - 0.15)\n            if self.fade_progress <= 0.01:\n                self.hide()\n                self.closing = False\n                return\n            changed = True\n        else:\n            if getattr(self, "fade_progress", 0.0) < 1.0:\n                self.fade_progress = min(1.0, getattr(self, "fade_progress", 0.0) + 0.15)\n                changed = True',
    code
)

# 5. execute_current - change hide to closing
code = re.sub(
    r'        if self\.original_cursor_pos:\n            QCursor\.setPos\(self\.original_cursor_pos\)\n        self\.hide\(\)',
    r'        if self.original_cursor_pos:\n            QCursor.setPos(self.original_cursor_pos)\n        self.closing = True\n        self.anim_timer.start(16)',
    code
)
code = re.sub(
    r'self\.hide\(\)\n                return',
    r'self.closing = True\n                self.anim_timer.start(16)\n                return',
    code
)

# 6. paintEvent - translucent background using fade_progress
code = re.sub(
    r'# 0\. Invisible shield to prevent Windows click-through on alpha=0 pixels\n        p\.setBrush\(QColor\(0, 0, 0, 1\)\)\n        p\.setPen\(Qt\.PenStyle\.NoPen\)\n        p\.drawEllipse\(self\.center_pt, self\.outer_radius, self\.outer_radius\)',
    r'# 0. Translucent full-screen background\n        fade = getattr(self, "fade_progress", 0.0)\n        if fade > 0.01:\n            p.fillRect(self.rect(), QColor(0, 0, 0, int(180 * fade)))\n        # Invisible shield for center\n        p.setBrush(QColor(0, 0, 0, 1))\n        p.setPen(Qt.PenStyle.NoPen)\n        p.drawEllipse(self.center_pt, self.outer_radius, self.outer_radius)',
    code
)

# 7. Add self.fade_progress to show_center
code = re.sub(
    r'self\.active_index = -1\n        self\.show\(\)',
    r'self.active_index = -1\n        self.closing = False\n        self.fade_progress = 0.0\n        self.show()',
    code
)

# 8. Mouse press outside to close
code = re.sub(
    r'        if e\.button\(\) == Qt\.MouseButton\.XButton1:',
    r'        if math.hypot(dx, dy) > self.outer_radius + 20:\n            self.execute_current()\n            return\n        if e.button() == Qt.MouseButton.XButton1:',
    code
)

with open('halo.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Updated halo.py")
