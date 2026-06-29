with open(r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\prototype.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
script = scripts[0]

print("--- Searching for element bindings in prototype.html script ---")
lines = script.splitlines()
for idx, line in enumerate(lines):
    if "document.getelementbyid" in line.lower() or "addeventlistener" in line.lower() or ".value =" in line.lower():
        safe_line = line.strip().encode('ascii', 'ignore').decode('ascii')
        print(f"Line {idx+1}: {safe_line}")
