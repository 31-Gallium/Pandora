import re

with open('electron_dashboard/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Add set-filter-preset
text = text.replace('<div class="control-row"><span class="control-label">Dashboard Theme</span><select>', '<div class="control-row" id="set-filter-preset"><span class="control-label">Dashboard Theme</span><select>')
text = text.replace('<div class="control-row"><span class="control-label">Filter Preset</span><select>', '<div class="control-row" id="set-filter-preset"><span class="control-label">Filter Preset</span><select>')

# Add set-kb-launch
text = text.replace('<div class="control-row"><span class="control-label">Launch App</span><button class="keybind-key">Left Click</button></div>', '<div class="control-row" id="set-kb-launch"><span class="control-label">Launch App</span><button class="keybind-key">Left Click</button></div>')

# Add set-kb-folder
text = text.replace('<div class="control-row"><span class="control-label">Open Folder</span><button class="keybind-key">Middle Click</button></div>', '<div class="control-row" id="set-kb-folder"><span class="control-label">Open Folder</span><button class="keybind-key">Middle Click</button></div>')

# Add set-kb-menu
text = text.replace('<div class="control-row"><span class="control-label">Show Menu</span><button class="keybind-key">Right Click</button></div>', '<div class="control-row" id="set-kb-menu"><span class="control-label">Show Menu</span><button class="keybind-key">Right Click</button></div>')

# Wait, the prototype HTML for toggles is:
# <div class="toggle-row"><span class="control-label">Show Grid when Dragging</span><label class="toggle"><input type="checkbox" checked><span class="track"></span></label></div>
text = text.replace('<div class="toggle-row"><span class="control-label">Show Grid when Dragging</span><label class="toggle">', '<div class="toggle-row" id="set-show-grid-drag"><span class="control-label">Show Grid when Dragging</span><label class="toggle">')
text = text.replace('<div class="toggle-row"><span class="control-label">Grid Animated Color</span><label class="toggle">', '<div class="toggle-row" id="set-anim-grid-color"><span class="control-label">Grid Animated Color</span><label class="toggle">')
text = text.replace('<div class="toggle-row"><span class="control-label">Grid Wave Entrance</span><label class="toggle">', '<div class="toggle-row" id="set-wave-ent"><span class="control-label">Grid Wave Entrance</span><label class="toggle">')
text = text.replace('<div class="toggle-row"><span class="control-label">Grid Wave Fade</span><label class="toggle">', '<div class="toggle-row" id="set-wave-color"><span class="control-label">Grid Wave Fade</span><label class="toggle">')

with open('electron_dashboard/index.html', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated index.html")
