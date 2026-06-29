from PyQt6.QtWidgets import QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QMenu, QApplication
from PyQt6.QtCore import Qt, QMimeData, QPoint, pyqtSignal
from PyQt6.QtGui import QDrag, QPainter, QColor, QPixmap
from utils import VectorIcon
from ui_dashboard_common import get_current_theme, get_theme_colors

def map_icon_color(original_color, theme):
    if theme == 'Light':
        # Map Dracula/glassmorphic pastels to solid/deep readable colors
        mapping = {
            "#FFF": "#1c1d22",
            "#FFFFFF": "#1c1d22",
            "#8BE9FD": "#2563eb",  # Blue instead of Cyan
            "#00F0FF": "#2563eb",  # Blue instead of Cyan
            "#F1FA8C": "#b45309",  # Deep amber/yellow instead of pale yellow
            "#50FA7B": "#16a34a",  # Deep green instead of pale green
            "#FFB86C": "#ea580c",  # Deep orange instead of pale orange
            "#BD93F9": "#7c3aed",  # Rich purple instead of pale purple
            "#FF79C6": "#db2777"   # Rich pink instead of pale pink
        }
        return mapping.get(original_color.upper(), original_color)
    elif theme == 'Dark':
        # Map to more vibrant or suitable dark-mode colors without cyan
        mapping = {
            "#FFF": "#ffffff",
            "#FFFFFF": "#ffffff",
            "#8BE9FD": "#a78bfa",  # Lavender (accent) instead of Cyan
            "#00F0FF": "#a78bfa",  # Lavender (accent) instead of Cyan
            "#F1FA8C": "#fbbf24",  # Yellow
            "#50FA7B": "#34d399",  # Green
            "#FFB86C": "#fb923c",  # Orange
            "#BD93F9": "#c084fc",  # Purple
            "#FF79C6": "#f472b6"   # Pink
        }
        return mapping.get(original_color.upper(), original_color)
    else:
        # Default Glassmorphic
        return original_color

class DZCard(QFrame):
    edit_req = pyqtSignal(str)
    dup_req = pyqtSignal(str)
    del_req = pyqtSignal(str)
    drag_completed = pyqtSignal()
    
    def __init__(self, layer, icon_path, color):
        super().__init__()
        self.lid = layer['id']
        self.layer_data = layer
        self.icon_path = icon_path
        self.original_color = color
        self.setFixedSize(90, 90)
        self.is_active = False
        self.setObjectName("DZCard")
        
        l = QVBoxLayout(self)
        l.setContentsMargins(10, 10, 10, 10)
        
        self.ic = QLabel()
        self.ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(self.ic)
        
        self.nl = QLabel(layer.get("name", "Layer"))
        self.nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nl.setWordWrap(True)
        l.addWidget(self.nl)
        
        self._update_style()
        
    def _update_style(self):
        colors = get_theme_colors()
        theme = colors['theme']
        accent = colors['accent_color']
        text_primary = colors['text_primary']
        
        # Update name label stylesheet
        self.nl.setStyleSheet(f"color: {text_primary}; font-size: 10px; font-weight: bold; border: none; background: transparent;")
        
        # Update icon pixmap dynamically based on theme
        mapped_color = map_icon_color(self.original_color, theme)
        self.ic.setPixmap(VectorIcon.pixmap(self.icon_path, mapped_color, 32))
        
        if theme == 'Light':
            if self.is_active:
                self.setStyleSheet(f"""
                    QFrame#DZCard {{ background: rgba(79, 70, 229, 0.15); border: 2px solid {accent}; border-radius: 8px; }}
                    QFrame#DZCard:hover {{ background: rgba(79, 70, 229, 0.25); }}
                """)
            else:
                self.setStyleSheet(f"""
                    QFrame#DZCard {{ background: #f3f4f6; border: 1px solid #ccd0d9; border-radius: 8px; }}
                    QFrame#DZCard:hover {{ background: #e5e7eb; border: 1px solid {accent}; }}
                """)
        elif theme == 'Dark':
            if self.is_active:
                self.setStyleSheet(f"""
                    QFrame#DZCard {{ background: rgba(167, 139, 250, 0.15); border: 2px solid {accent}; border-radius: 8px; }}
                    QFrame#DZCard:hover {{ background: rgba(167, 139, 250, 0.25); }}
                """)
            else:
                self.setStyleSheet(f"""
                    QFrame#DZCard {{ background: #181822; border: 1px solid #282835; border-radius: 8px; }}
                    QFrame#DZCard:hover {{ background: #22222d; border: 1px solid {accent}; }}
                """)
        else: # Default Glassmorphism
            if self.is_active:
                self.setStyleSheet(f"""
                    QFrame#DZCard {{ background: rgba(0, 240, 255, 10); border: 2px solid {accent}; border-radius: 8px; }}
                    QFrame#DZCard:hover {{ background: rgba(0, 240, 255, 20); }}
                """)
            else:
                self.setStyleSheet("""
                    QFrame#DZCard { background: rgba(255,255,255,5); border: 1px solid transparent; border-radius: 8px; }
                    QFrame#DZCard:hover { background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,30); }
                """)
            
    def set_active(self, active):
        self.is_active = active
        self._update_style()
        
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = e.pos()
        elif e.button() == Qt.MouseButton.RightButton:
            colors = get_theme_colors()
            accent = colors['accent_color']
            m = QMenu(self)
            if colors['theme'] == 'Light':
                m.setStyleSheet(f"QMenu {{ background: #ffffff; color: #1c1d22; border: 1px solid #ccd0d9; }} QMenu::item:selected {{ background: rgba(79, 70, 229, 0.15); color: #4F46E5; }}")
            elif colors['theme'] == 'Dark':
                m.setStyleSheet(f"QMenu {{ background: #181822; color: #ffffff; border: 1px solid #282835; }} QMenu::item:selected {{ background: rgba(167, 139, 250, 0.15); color: #a78bfa; }}")
            else:
                m.setStyleSheet("QMenu { background: #1a1a1a; color: white; border: 1px solid #333; } QMenu::item:selected { background: rgba(0,240,255,40); }")
            m.addAction("Edit", lambda: self.edit_req.emit(self.lid))
            # Only launcher can be duplicated (other modules are unique)
            if self.layer_data.get('type') == 'launcher':
                m.addAction("Duplicate", lambda: self.dup_req.emit(self.lid))
            m.addAction("Delete", lambda: self.del_req.emit(self.lid))
            m.exec(e.globalPosition().toPoint())
            
    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.MouseButton.LeftButton): return
        if getattr(self, 'drag_start_pos', None) is not None:
            if (e.pos() - self.drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                del self.drag_start_pos # Clear it so release doesn't trigger edit and future moves don't crash
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(self.lid)
                drag.setMimeData(mime)
                pixmap = self.grab()
                drag.setPixmap(pixmap)
                drag.setHotSpot(e.pos())
                
                self.hide()
                res = drag.exec(Qt.DropAction.MoveAction)
                try:
                    self.show()
                except RuntimeError:
                    pass # Widget was deleted during the drop by _render_cards
                
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(0, self.drag_completed.emit)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if getattr(self, 'drag_start_pos', None) is not None:
                self.edit_req.emit(self.lid)


class DZGridSlot(QFrame):
    add_req = pyqtSignal(int)
    drop_req = pyqtSignal(str, int) # lid, target_idx
    
    def __init__(self, idx):
        super().__init__()
        self.idx = idx
        self.setFixedSize(90, 90)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.l = QVBoxLayout(self)
        self.l.setContentsMargins(0, 0, 0, 0)
        
        self.add_lbl = QLabel("+")
        self.add_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.l.addWidget(self.add_lbl)
        
        self.card = None
        self._update_style()

    def _update_style(self):
        colors = get_theme_colors()
        theme = colors['theme']
        accent = colors['accent_color']
        
        self.add_lbl.setStyleSheet(f"color: {accent}; font-size: 24px; font-weight: bold; background: transparent; border: none;")
        
        if self.card:
            self.setStyleSheet("QFrame { background: transparent; border: none; }")
        else:
            if theme == 'Light':
                self.setStyleSheet(f"QFrame {{ background: #e5e7eb; border: 1px dashed #ccd0d9; border-radius: 8px; }} QFrame:hover {{ background: #d1d5db; border: 1px dashed {accent}; }}")
            elif theme == 'Dark':
                self.setStyleSheet(f"QFrame {{ background: #22222d; border: 1px dashed #282835; border-radius: 8px; }} QFrame:hover {{ background: #1a1a24; border: 1px dashed {accent}; }}")
            else: # Default Glassmorphism
                self.setStyleSheet(f"QFrame {{ background: rgba(255,255,255,2); border: 1px dashed rgba(255,255,255,10); border-radius: 8px; }} QFrame:hover {{ background: rgba(255,255,255,5); border: 1px dashed {accent}; }}")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and not self.card:
            self.add_req.emit(self.idx)

    def take_card(self):
        c = self.card
        if c:
            self.l.removeWidget(c)
            c.setParent(None)
            self.card = None
        self.add_lbl.show()
        self._update_style()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        return c

    def set_card(self, card):
        if self.card and self.card is not card:
            self.card.deleteLater()
        self.card = card
        if card:
            self.add_lbl.hide()
            self.l.addWidget(card)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.add_lbl.show()
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style()

    def dragEnterEvent(self, e):
        if e.mimeData().hasText(): e.acceptProposedAction()
    def dragMoveEvent(self, e):
        if e.mimeData().hasText(): e.acceptProposedAction()
    def dropEvent(self, e):
        if e.mimeData().hasText():
            lid = e.mimeData().text()
            self.drop_req.emit(lid, self.idx)
            e.acceptProposedAction()


class DZGrid(QWidget):
    order_changed = pyqtSignal()
    add_req = pyqtSignal(int)
    edit_req = pyqtSignal(str)
    dup_req = pyqtSignal(str)
    del_req = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.l = QHBoxLayout(self)
        self.l.setSpacing(15)
        self.l.setContentsMargins(0, 0, 0, 0)
        self.l.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.slots = []
        for i in range(9):
            slot = DZGridSlot(i)
            slot.add_req.connect(self.add_req.emit)
            slot.drop_req.connect(self._handle_drop)
            self.l.addWidget(slot)
            self.slots.append(slot)
            
        self.cards_data = []
        self.active_lid = None

    def set_active_card(self, lid):
        self.active_lid = lid
        for slot in self.slots:
            if slot.card:
                slot.card.set_active(slot.card.lid == lid)

    def _handle_drop(self, lid, target_idx):
        source_idx = next((i for i, l in enumerate(self.cards_data) if l and l['id'] == lid), -1)
        if source_idx == -1 or source_idx == target_idx: return
        
        # Swap
        self.cards_data[source_idx], self.cards_data[target_idx] = self.cards_data[target_idx], self.cards_data[source_idx]
        self._pending_render = True

    def _on_drag_completed(self):
        if getattr(self, '_pending_render', False):
            self._pending_render = False
            self._render_cards()
            self.order_changed.emit()

    def set_cards(self, cards_data, icon_map, color_map):
        # cards_data is a list of length 9, potentially with Nones
        self.cards_data = cards_data
        self.icon_map = icon_map
        self.color_map = color_map
        self._render_cards()
        
    def _render_cards(self):
        # 1. Gather all existing DZCards to reuse them, detaching them from slots
        existing_cards = {}
        for slot in self.slots:
            c = slot.take_card()
            if c:
                existing_cards[c.lid] = c
                
        # 2. Populate slots with either existing reused cards or new ones
        for i, layer in enumerate(self.cards_data):
            if layer:
                lid = layer['id']
                if lid in existing_cards:
                    c = existing_cards.pop(lid)
                    c.layer_data = layer
                    if hasattr(c, 'nl'):
                        c.nl.setText(layer.get("name", "Layer"))
                else:
                    t = layer.get("type", "default")
                    c = DZCard(layer, self.icon_map.get(t, "circle"), self.color_map.get(t, "#fff"))
                    c.edit_req.connect(self.edit_req.emit)
                    c.dup_req.connect(self.dup_req.emit)
                    c.del_req.connect(self.del_req.emit)
                    c.drag_completed.connect(self._on_drag_completed)
                
                if self.active_lid and c.lid == self.active_lid:
                    c.set_active(True)
                else:
                    c.set_active(False)
                    
                self.slots[i].set_card(c)
            else:
                self.slots[i].set_card(None)
                
        # 3. Safely delete any cards that are no longer needed
        for c in existing_cards.values():
            c.deleteLater()

    def get_order(self):
        return self.cards_data
