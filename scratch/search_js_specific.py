import re

with open(r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\prototype.html", "r", encoding="utf-8") as f:
    html = f.read()

keys_to_check = [
    # General & Appearance
    "v-gs", "v-ep", "v-gv", "set-show-grid-drag", "set-anim-grid-color", 
    "set-wave-ent", "set-wave-color", "set-filter-preset", "v-wi",
    
    # Keybinds
    "set-kb-launch", "set-kb-folder", "set-kb-menu",
    
    # Halo activation & behavior
    "set-halo-act-key", "set-halo-act-mode", "set-halo-theme", "set-halo-arc",
    "v-md", "v-hr", "v-bo", "v-ss", "v-ms",
    
    # Templates Editor Sizing
    "i-tpl-foldersize", "v-tpl-foldersize",
    "i-tpl-miniiconsize", "v-tpl-miniiconsize",
    "i-tpl-fontsize", "v-tpl-fontsize",
    "i-tpl-appiconsize", "v-tpl-appiconsize",
    
    # Templates Editor Styling
    "i-mock-opacity", "v-mock-opacity",
    "i-mock-radius", "v-mock-radius",
    "i-mock-glow", "v-mock-glow",
    "i-mock-coverblur", "v-mock-coverblur",
    "i-mock-coveropacity", "v-mock-coveropacity",
    "i-mock-coverpath",
    
    # Templates Colors
    "i-tpl-glowcolor", "v-tpl-glowcolor",
    "i-tpl-bgcolor", "v-tpl-bgcolor",
    "i-tpl-textcolor", "v-tpl-textcolor",
    "i-tpl-highlightcolor", "v-tpl-highlightcolor",

    # Folders Editor Sizing
    "i-fld-foldersize", "v-fld-foldersize",
    "i-fld-miniiconsize", "v-fld-miniiconsize",
    "i-fld-fontsize", "v-fld-fontsize",
    "i-fld-appiconsize", "v-fld-appiconsize",
    
    # Folders Editor Styling
    "i-fld-opacity", "v-fld-opacity",
    "i-fld-radius", "v-fld-radius",
    "i-fld-glow", "v-fld-glow",
    "i-fld-coverblur", "v-fld-coverblur",
    "i-fld-coveropacity", "v-fld-coveropacity",
    "i-fld-coverpath",
    
    # Folders Colors
    "i-fld-glowcolor", "v-fld-glowcolor",
    "i-fld-bgcolor", "v-fld-bgcolor",
    "i-fld-textcolor", "v-fld-textcolor",
    "i-fld-highlightcolor", "v-fld-highlightcolor",
    
    # Weather Widget
    "setting-weather-provider", "setting-weather-loc", "setting-weather-key", "setting-weather-metric",
    
    # Clock Widget
    "setting-clock-mode", "setting-clock-label", "setting-clock-date", 
    "setting-clock-24h", "setting-clock-seconds", "clock-world-tz-select",
    "clock-world-label-input", "clock-world-add-btn",
    
    # Timer Widget
    "setting-timer-dur", "setting-timer-repeat", "setting-timer-sound", "timer-preset-adj",
    
    # Launcher Widget
    "setting-launcher-labels", "setting-launcher-size", "launcher-item-add-btn"
]

print("--- Checking exact prototype.html element parity ---")
missing = []
for k in keys_to_check:
    count = html.count(k)
    if count > 0:
        print(f"[OK]   {k:28s} : FOUND ({count} times)")
    else:
        print(f"[FAIL] {k:28s} : NOT FOUND")
        missing.append(k)

print("\nTotal checked:", len(keys_to_check))
print("Total missing:", len(missing))
