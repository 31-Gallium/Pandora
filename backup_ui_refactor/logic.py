import os
import json
import shutil
import logging

logger = logging.getLogger("Pandora")

def handle_app_drop(cfg, target_folder_data, mime_data, e_source, is_target_pinned, target_idx, dashboard=None):
    """
    Centralized logic for dropping Pandora apps into a folder.
    Handles physical file relocation, cross-folder metadata updates, and UI refreshes.
    """
    from config import STORAGE_PATH, ConfigManager
    
    if not mime_data.hasFormat("application/x-pandora-app"):
        return False, []

    sid = mime_data.data("application/x-pandora-app").data().decode().strip()
    try:
        # Load the dropped apps data
        dropped_apps = json.loads(mime_data.text())
        if isinstance(dropped_apps, dict):
            dropped_apps = [dropped_apps]
    except Exception as e:
        logger.error(f"Failed to parse dropped apps: {e}")
        return False, []

    from app_icon import AppIcon
    dropped_paths = []
    
    for ad in dropped_apps:
        old_path = ad['path']
        
        # 1. Handle physical move if moving between different folders
        if sid and sid != target_folder_data['id']:
            bn = os.path.basename(old_path)
            target_storage = os.path.join(STORAGE_PATH, target_folder_data['id'])
            if not os.path.exists(target_storage): os.makedirs(target_storage)
            new_path = os.path.join(target_storage, bn)
            
            # Collision handling: add suffix if target exists
            if os.path.exists(new_path) and new_path != old_path:
                base, ext = os.path.splitext(bn)
                new_path = os.path.join(target_storage, f"{base}_moved{ext}")
            
            try:
                shutil.move(old_path, new_path)
                ad['path'] = new_path
                
                # Signal the SOURCE folder UI to update
                if dashboard:
                    for icon in dashboard.folder_icons:
                        if icon.data['id'] == sid:
                            icon.update()
                            if hasattr(icon, 'view') and icon.view:
                                icon.view.refresh()
                            break
            except Exception as ex:
                logger.error(f"Physical relocation error: {ex}")
        
        # 2. Flag the source icon as 'internal' to prevent desktop move
        if isinstance(e_source, AppIcon):
            e_source.is_internal = True
        
        # 3. Remove from source folder metadata in the shared config
        for f in cfg['folders']:
            if f['id'] == sid:
                # Use old_path if moved between folders, or current path if internal reorder
                match_path = old_path if sid != target_folder_data['id'] else ad['path']
                f['apps'] = [a for a in f['apps'] if a['path'] != match_path]
                break
        
        # 4. Insert into destination apps list
        is_custom = target_folder_data.get('sort_type', 'name') == 'custom'
        
        # Recalculate target_idx if dropping into the same folder to account for removal
        final_idx = target_idx
        
        if is_custom:
            # In custom sort, we just insert it at the requested position
            ad['pinned'] = is_target_pinned
            target_folder_data['apps'].insert(max(0, min(final_idx, len(target_folder_data['apps']))), ad)
        else:
            # Otherwise, maintain the pinned/unpinned split
            current_pinned = [a for a in target_folder_data['apps'] if a.get('pinned')]
            current_unpinned = [a for a in target_folder_data['apps'] if not a.get('pinned')]

            ad['pinned'] = is_target_pinned
            if ad['pinned']:
                insert_idx = min(final_idx, len(current_pinned))
                current_pinned.insert(insert_idx, ad)
            else:
                insert_idx = max(0, final_idx - len(current_pinned))
                insert_idx = min(insert_idx, len(current_unpinned))
                current_unpinned.insert(insert_idx, ad)

            target_folder_data['apps'] = current_pinned + current_unpinned
            
        target_idx += 1
        dropped_paths.append(ad['path'])

    return True, dropped_paths
