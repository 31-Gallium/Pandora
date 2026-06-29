import re
with open('electron_dashboard/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

sliders = re.findall(r'<input[^>]*type=[\"\']range[\"\'][^>]*>', html)
for slider in sliders:
    id_match = re.search(r'id=[\"\']([^\"\']+)[\"\']', slider)
    val_match = re.search(r'data-val=[\"\']([^\"\']+)[\"\']', slider)
    print(f"ID: {id_match.group(1) if id_match else 'None'} -> VAL: {val_match.group(1) if val_match else 'None'}")
