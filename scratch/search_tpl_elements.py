with open(r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\prototype.html", "r", encoding="utf-8") as f:
    html = f.read()

lines = html.splitlines()
# Let's find where 'tpl-custom-sizing-container' is
idx = -1
for i, line in enumerate(lines):
    if "tpl-custom-sizing-container" in line:
        idx = i
        break

if idx != -1:
    print("--- Templates custom sizing elements in prototype.html ---")
    for i in range(idx - 2, idx + 50):
        safe_line = lines[i].encode('ascii', 'ignore').decode('ascii')
        print(f"{i+1:4d}: {safe_line}")
