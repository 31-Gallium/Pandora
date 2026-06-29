with open(r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\prototype.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
script = scripts[0]

lines = script.splitlines()
print("--- Slider code in prototype.html script ---")
for i in range(235, 260):
    safe_line = lines[i].encode('ascii', 'ignore').decode('ascii')
    print(f"{i+1}: {safe_line}")
