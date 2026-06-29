import os

folder = r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard"
for fname in os.listdir(folder):
    if not fname.endswith((".html", ".js")): continue
    fpath = os.path.join(folder, fname)
    # Try different encodings
    for encoding in ["utf-8", "utf-16", "cp1252"]:
        try:
            with open(fpath, "r", encoding=encoding) as f:
                content = f.readlines()
            for idx, line in enumerate(content):
                if any(w in line.lower() for w in ["cover_blur", "cover_opacity", "cover_image", "cover-blur", "cover-opacity"]):
                    print(f"{fname}:{idx+1}: {line.strip()}")
            break
        except Exception:
            continue
