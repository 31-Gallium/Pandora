with open(r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\prototype.html", "r", encoding="utf-8") as f:
    html = f.read()

lines = html.splitlines()
print("--- Clock settings HTML in prototype.html ---")
for idx, line in enumerate(lines):
    if "setting-clock-" in line or "clock-world" in line:
        # Print the line and the next few lines
        print(f"Line {idx+1}: {line.strip()}")
