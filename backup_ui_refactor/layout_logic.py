import math
from PyQt6.QtCore import QPointF

class LayoutEngine:
    @staticmethod
    def get_collapsed_positions(cx, cy, folder_size, icon_size, count, hp=0.0):
        pass
    
    @staticmethod
    def get_expanded_params(count, cell_w, cell_h, grid_w):
        pass

    @staticmethod
    def get_paging_positions(cx, cy, folder_size, icon_size, count, page, next_page, progress, hp=1.0):
        pass

    @staticmethod
    def get_paging_positions(cx, cy, folder_size, icon_size, count, page, next_page, progress, direction, hp=1.0):
        pass

class GridLayoutEngine(LayoutEngine):
    @staticmethod
    def get_collapsed_positions(cx, cy, folder_size, icon_size, count, hp=0.0):
        gap = 4 + (12 * hp) 
        tl = (icon_size * 3) + (gap * 2)
        gx, gy = cx - tl / 2, cy - tl / 2
        positions = []
        for i in range(min(count, 9)):
            r, c = i // 3, i % 3
            dx = (c - 1) * (6 * hp)
            dy = (r - 1) * (6 * hp)
            positions.append(QPointF(gx + c * (icon_size + gap) + dx, gy + r * (icon_size + gap) + dy))
        return positions

    @staticmethod
    def get_paging_positions(cx, cy, folder_size, icon_size, count, page, next_page, progress, direction, hp=1.0):
        gap = 4 + (12 * hp); tl = (icon_size * 3) + (gap * 2); gx, gy = cx - tl / 2, cy - tl / 2
        def get_base(idx):
            r, c = idx // 3, idx % 3
            dx = (c - 1) * (6 * hp); dy = (r - 1) * (6 * hp)
            return QPointF(gx + c * (icon_size + gap) + dx, gy + r * (icon_size + gap) + dy)
        
        results = []
        # Multiplier based on scroll direction (1 for down/forward, -1 for up/backward)
        move_dist = (icon_size + gap) * direction
        
        # Outgoing
        start_idx = page * 9
        for i in range(9):
            app_idx = start_idx + i
            if app_idx < count:
                base = get_base(i)
                results.append((app_idx, base + QPointF(0, -progress * move_dist), 1.0 - progress))
        
        # Incoming
        next_start = next_page * 9
        for i in range(9):
            app_idx = next_start + i
            if app_idx < count:
                base = get_base(i)
                results.append((app_idx, base + QPointF(0, (1.0 - progress) * move_dist), progress))
        return results

    @staticmethod
    def get_expanded_params(count, cell_w, cell_h, grid_w):
        cols = 3; rows = (count + cols - 1) // cols; content_h = max(cell_h * 3, rows * cell_h)
        positions = []
        for i in range(count):
            r, c = i // cols, i % cols
            positions.append(QPointF(c * cell_w, r * cell_h))
        return positions, content_h

class FlowerLayoutEngine(LayoutEngine):
    @staticmethod
    def get_collapsed_positions(cx, cy, folder_size, icon_size, count, hp=0.0):
        positions = []
        if count > 0: positions.append(QPointF(cx - icon_size/2, cy - icon_size/2))
        if count > 1:
            target_r = folder_size * 0.52; start_r = folder_size * 0.35; radius = start_r + (target_r - start_r) * hp
            for i in range(min(count - 1, 6)):
                angle = math.radians(i * 60 - 90)
                px = cx + math.cos(angle) * radius - icon_size / 2; py = cy + math.sin(angle) * radius - icon_size / 2
                positions.append(QPointF(px, py))
        return positions

    @staticmethod
    def get_paging_positions(cx, cy, folder_size, icon_size, count, page, next_page, progress, direction, hp=1.0):
        PAGE_SIZE = 7; target_r = folder_size * 0.52; start_r = folder_size * 0.35; radius = start_r + (target_r - start_r) * hp
        results = []
        def get_flower_pos(i, rotation=0.0):
            if i == 0: return QPointF(cx - icon_size/2, cy - icon_size/2)
            angle = math.radians((i-1) * 60 - 90 + rotation)
            return QPointF(cx + math.cos(angle) * radius - icon_size / 2, cy + math.sin(angle) * radius - icon_size / 2)

        rot_step = 60 * direction
        # Outgoing
        start_idx = page * PAGE_SIZE
        for i in range(PAGE_SIZE):
            app_idx = start_idx + i
            if app_idx < count:
                rot = progress * rot_step if i > 0 else 0
                results.append((app_idx, get_flower_pos(i, -rot), 1.0 - progress))
        # Incoming
        next_start = next_page * PAGE_SIZE
        for i in range(PAGE_SIZE):
            app_idx = next_start + i
            if app_idx < count:
                rot = (1.0 - progress) * rot_step if i > 0 else 0
                results.append((app_idx, get_flower_pos(i, rot), progress))
        return results

    @staticmethod
    def get_expanded_params(count, cell_w, cell_h, grid_w):
        positions = []; view_h = cell_h * 3; cx, cy = grid_w / 2, view_h / 2
        if count == 0: return [], view_h
        positions.append(QPointF(cx - cell_w/2, cy - cell_h/2))
        apps_placed = 1; ring_idx = 1
        while apps_placed < count:
            num_in_ring = ring_idx * 6; radius = cell_w * 1.2 * ring_idx; items_to_place = min(count - apps_placed, num_in_ring)
            for i in range(items_to_place):
                angle = math.radians(i * (360 / items_to_place) - 90)
                positions.append(QPointF(cx + math.cos(angle) * radius - cell_w/2, cy + math.sin(angle) * radius - cell_h/2))
            apps_placed += items_to_place; ring_idx += 1
        max_r = cell_h * 1.2 * (ring_idx - 1); content_h = max(view_h, cy + max_r + cell_h/2)
        return positions, content_h

def get_engine(t_type):
    if t_type == 'flower': return FlowerLayoutEngine
    return GridLayoutEngine
