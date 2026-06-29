import re

with open('electron_dashboard/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# We need to find every <div class="control-row"> or <div class="setting-item"> 
# and look at its label, then add an ID to the <input>, <select>, or <div class="slider-track">.

# It's safer to just do manual mapping for the tabs that are broken.
# Let's list the settings in GeneralTab.
# wait, ui_dashboard_general.js uses specific IDs.
# I'll just print out all the labels and their surrounding HTML so I can see.

def print_pane(pane_id):
    print(f"--- {pane_id} ---")
    start = html.find(f'id="{pane_id}"')
    if start == -1: return
    end = html.find('id="pane-', start + 1)
    if end == -1: end = len(html)
    pane = html[start:end]
    
    rows = re.findall(r'<div class="control-row".*?>(.*?)</div>\s*(?:</div>)?', pane, re.DOTALL)
    for r in rows:
        label_match = re.search(r'<span class="control-label">(.*?)</span>', r)
        if label_match:
            print("- " + label_match.group(1).strip())

print_pane('pane-general')
print_pane('pane-halo')
print_pane('pane-hub')
print_pane('pane-folders')
print_pane('pane-templates')
