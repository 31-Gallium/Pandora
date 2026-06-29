import re

with open('electron_dashboard/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

panes = re.findall(r'<div id="(pane-[^"]+)" class="pane', text)
print('PANES:', panes)

for pane in panes:
    print(f'\n--- {pane} ---')
    start = text.find(f'id="{pane}"')
    end = text.find('<div id="pane-', start + 1)
    if end == -1: end = len(text)
    
    p = text[start:end]
    rows = re.findall(r'<div class="control-row"[^>]*>(.*?)</div>\s*(?:</div>)?', p, re.DOTALL)
    for r in rows:
        label = re.search(r'<span class="control-label">(.*?)</span>', r)
        if label:
            print('- ' + label.group(1).strip())
