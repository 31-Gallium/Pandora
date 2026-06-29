with open(r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\prototype.html", "r", encoding="utf-8") as f:
    html = f.read()

import re
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
script = scripts[0]

# Search for cover/blur/opacity/font elements inside the script
print("--- Searching for key terms inside script block ---")
for word in ["blur", "opacity", "cover", "image", "sound", "preset", "fontsize", "coverblur", "coveropacity", "coverpath"]:
    matches = []
    for idx, line in enumerate(script.splitlines()):
        if word in line.lower():
            matches.append((idx+1, line.strip()))
    print(f"\nWord '{word}': {len(matches)} matches")
    # Show first 15 matches
    for m in matches[:15]:
        safe_m = m[1].encode('ascii', 'ignore').decode('ascii')
        print(f"  Line {m[0]}: {safe_m}")
