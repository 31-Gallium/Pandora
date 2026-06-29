import os
import shutil

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Exact files to delete
FILES_TO_DELETE = [
    "proper_diff.patch",
    "dash_diff.txt",
    "dash_diff_lf.txt",
    "dash_diff_utf8.txt",
    "dash_changes.txt",
    "dashboard.py.orig",
    "dashboard.py.rej",
    "dashboard.py.oMLTVxU",
    "dashboard_restored.py",
    "extracted_additions.py",
    "restore_final.py",
    "rollback.txt",
    "all_deleted.txt",
    "all_deleted_code.py",
    "v8_dashboard.py",
    "v8_dashboard_utf8.py",
    "media_debug.log",
    "error.log",
    "output.log",
    "pandora_out.txt",
    "qfont_trace.txt",
    "drag_debug.txt",
    "test_out.txt",
    "update.txt",
    "inject.py",
    "inject2.py",
    "check_thumb_quality.py",
    "trace_qfont.py",
    "update_defaults.py",
    "Debugging Dashboard Layer Reordering.md",
    "implementation_plan.md.resolved",
]

# Directories to delete
DIRS_TO_DELETE = [
    "backup_stable_v8",
    "backup_stable_v9",
]

deleted_files = []
failed_files = []

# 1. Delete exact files
for filename in FILES_TO_DELETE:
    path = os.path.join(ROOT_DIR, filename)
    if os.path.exists(path):
        try:
            os.remove(path)
            deleted_files.append(filename)
        except Exception as e:
            failed_files.append((filename, str(e)))

# 2. Delete exact directories
for dirname in DIRS_TO_DELETE:
    path = os.path.join(ROOT_DIR, dirname)
    if os.path.exists(path):
        try:
            shutil.rmtree(path)
            deleted_files.append(f"{dirname}/ (directory)")
        except Exception as e:
            failed_files.append((dirname, str(e)))

# 3. Dynamic deletion of test_*.py, patch_*.py, test_*.png, etc. in root
for entry in os.listdir(ROOT_DIR):
    path = os.path.join(ROOT_DIR, entry)
    if os.path.isfile(path):
        name_lower = entry.lower()
        should_del = False
        
        # Matches patterns
        if name_lower.startswith("test_") and name_lower.endswith((".py", ".png", ".jpg")):
            should_del = True
        elif name_lower.startswith("patch_") and name_lower.endswith(".py"):
            should_del = True
        elif entry in ["patch.py", "patch3.py"]:
            should_del = True
            
        if should_del:
            try:
                os.remove(path)
                deleted_files.append(entry)
            except Exception as e:
                failed_files.append((entry, str(e)))

print("--- CLEANUP COMPLETED ---")
print(f"Successfully deleted {len(deleted_files)} files/folders:")
for f in sorted(deleted_files):
    print(f"  - {f}")

if failed_files:
    print(f"\nFailed to delete {len(failed_files)} items (possibly locked or lack permissions):")
    for f, err in sorted(failed_files):
        print(f"  - {f}: {err}")
