import re

with open('electron_dashboard/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

tabs = re.findall(r'<div class="tab-content"[^>]*id="(.*?)"', text)
print("TABS:", tabs)

for tab in tabs:
    print(f"\n--- {tab} ---")
    start = text.find(f'id="{tab}"')
    end = text.find('<div class="tab-content"', start + 1)
    if end == -1: end = len(text)
    
    pane = text[start:end]
    rows = re.findall(r'<div class="control-row"[^>]*>(.*?)</div>\s*(?:</div>)?', pane, re.DOTALL)
    for r in rows:
        label = re.search(r'<span class="control-label">(.*?)</span>', r)
        if label:
            print("- " + label.group(1).strip())
