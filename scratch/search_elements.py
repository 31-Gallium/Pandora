import re

with open(r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\prototype.html", "r", encoding="utf-8") as f:
    html = f.read()

# Let's find all section tags or IDs or classes that might represent tabs
print("--- IDs in prototype.html ---")
ids = re.findall(r'id=["\']([^"\']+)["\']', html)
for id_val in sorted(list(set(ids))):
    if "tab" in id_val.lower() or "section" in id_val.lower() or "pane" in id_val.lower() or "editor" in id_val.lower() or "template" in id_val.lower() or "folder" in id_val.lower() or "halo" in id_val.lower() or "hub" in id_val.lower() or "active" in id_val.lower() or "launcher" in id_val.lower():
        print("ID:", id_val)

print("\n--- Classes in prototype.html ---")
classes = re.findall(r'class=["\']([^"\']+)["\']', html)
all_classes = []
for c in classes:
    all_classes.extend(c.split())
for c_val in sorted(list(set(all_classes))):
    if "tab" in c_val.lower() or "section" in c_val.lower() or "pane" in c_val.lower() or "editor" in c_val.lower():
        print("Class:", c_val)

print("\n--- Let's look for cover blur / cover opacity / cover image in the file ---")
for word in ["blur", "opacity", "cover", "image", "sound", "preset"]:
    matches = len(re.findall(word, html, re.IGNORECASE))
    print(f"Word '{word}': {matches} matches")
