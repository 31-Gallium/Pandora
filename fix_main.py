with open('c:\\\\Users\\\\Base\\\\Desktop\\\\Seb\\\\Pandora\\\\main.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('elif cmd == "explorer":', 'elif cmd in ["explorer", "files"]:')
text = text.replace('elif cmd == "grid":', 'elif cmd in ["grid", "toggle grid"]:')
text = text.replace('elif cmd == "screenshot":', 'elif cmd in ["screenshot", "snip"]:')
text = text.replace('elif cmd == "taskmgr":', 'elif cmd in ["taskmgr", "tasks"]:')
text = text.replace('elif cmd == "settings":', 'elif cmd in ["settings", "pandora"]:')
text = text.replace('elif cmd == "trash":', 'elif cmd in ["trash", "empty trash"]:')
text = text.replace('elif cmd == "notes":', 'elif cmd in ["notes", "sticky notes"]:')

with open('c:\\\\Users\\\\Base\\\\Desktop\\\\Seb\\\\Pandora\\\\main.py', 'w', encoding='utf-8') as f:
    f.write(text)
