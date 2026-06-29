with open(r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\prototype.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
script = scripts[0]

lines = script.splitlines()
print("--- Script lines 1200 to 1500 ---")
for idx in range(1200, min(len(lines), 1500)):
    safe_line = lines[idx].encode('ascii', 'ignore').decode('ascii')
    print(f"{idx+1:3d}: {safe_line}")
