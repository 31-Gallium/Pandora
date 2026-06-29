import os
import re

folder = r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard"
files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith((".html", ".js"))]

combined_content = ""
for fpath in files:
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            combined_content += f"\n=== {os.path.basename(fpath)} ===\n" + f.read()
    except Exception as e:
        print("Error reading", fpath, e)

print("Total combined characters:", len(combined_content))

elements_to_check = {
    # 1. General tab settings elements
    "Grid Size Slider": "grid_size",
    "Edge Padding Slider": "edge_padding",
    "Show Grid on Drag Toggle": "show_grid_on_drag",
    "Animated Grid Color Toggle": "grid_animated_color",
    "Wave Entrance Toggle": "grid_wave_entrance",
    "Wave Color Fade Toggle": "grid_wave_fade",
    "Grid Visibility Slider": "grid_opacity",
    "Dashboard Theme Selector": "dashboard_theme",
    "Keybind Launch App Button/Input": "launch_app",
    "Keybind Open Folder Button/Input": "open_folder",
    "Keybind Show Menu Button/Input": "show_menu",
    "Halo Activation Key Button/Input": "activation_key",
    "Halo Activation Mode Selector": "hold_mode",
    "Halo Visual Theme Selector": "theme",
    "Halo HUD Arc Gap Selector": "gap_size",
    "Halo Diameter Slider": "max_bound",
    "Halo Hub Ratio Slider": "hub_ratio",
    "Halo BG Opacity Slider": "opacity",
    "Halo Scroll Sensitivity Slider": "scroll_sens",
    "Halo Mouse Sensitivity Slider": "mouse_sens",
    "Display Filter Preset Selector": "active_preset",
    "Display Warmth Intensity Slider": "warmth_intensity",

    # 2. Templates Editor elements
    "Templates Container/Section": "templates-tab",
    "Templates Sizing Sliders Container": "tpl-custom-sizing",
    "Templates Sizing Size Slider": "folder_size",
    "Templates Sizing Mini Icon Slider": "mini_icon_size",
    "Templates Sizing Font Size Slider": "font_size",
    "Templates Sizing App Icon Slider": "expanded_icon_size",
    "Templates Cover Blur Slider": "cover_blur",
    "Templates Cover Opacity Slider": "cover_opacity",
    "Templates Color Glow Swatch": "glow_color",
    "Templates Color BG Swatch": "bg_color",
    "Templates Color Text Swatch": "title_color",
    "Templates Color Highlight Swatch": "highlight_color",
    "Templates Cover Image Input": "cover_image",

    # 3. Folders Editor elements
    "Folders Container/Section": "folders-tab",
    "Folders Custom Styling Toggle": "use_custom_settings",
    "Folders Sizing Size Slider": "folder_size",
    "Folders Sizing Mini Icon Slider": "mini_icon_size",
    "Folders Sizing Font Size Slider": "font_size",
    "Folders Sizing App Icon Slider": "expanded_icon_size",
    "Folders Cover Blur Slider": "cover_blur",
    "Folders Cover Opacity Slider": "cover_opacity",
    "Folders Color Glow Swatch": "glow_color",
    "Folders Color BG Swatch": "bg_color",
    "Folders Color Text Swatch": "title_color",
    "Folders Color Highlight Swatch": "highlight_color",
    "Folders Cover Image Input": "cover_image",

    # 4. Halo Menu elements
    "Halo Container/Section": "halo-tab",
    "Halo Enabled Switch/Toggle": "halo-enabled",
    "Halo Command Bank Tools": "HALO_TOOLS",
    "Calculator Tool ID": "calc",
    "Terminal Tool ID": "cmd",
    "Notepad Tool ID": "notepad",
    "Prev Media Tool ID": "prev",
    "Next Media Tool ID": "next",

    # 5. Hub HUD elements
    "Hub HUD Container/Section": "hub-tab",
    "Hub HUD DZGrid / Layout Grid": "active-modules",
    "Hub Weather Provider Choice": "provider",
    "Hub Weather API Key": "api_key",
    "Hub Weather Location": "location",
    "Hub Weather Metric (Celsius) Switch": "use_metric",
    "Hub Timer Default Duration": "default_duration",
    "Hub Timer Auto-Repeat Switch": "auto_repeat",
    "Hub Timer Sound on Complete Switch": "sound_enabled",
    "Hub Timer Presets Adjusters": "presets",
    "Hub Launcher Labels Switch": "show_labels",
    "Hub Launcher Icon Size Slider": "icon_size",
    "Hub Launcher Items Cards Flow": "launcher-items",
    "Hub Clock Searchable Timezone": "active_clock_tz",
    "Hub Clock World Clocks": "world_clocks",
}

print("\n--- Structural Audit of electron_dashboard folder ---")
all_found = True
for name, query in elements_to_check.items():
    # Find which file has it
    found_in_files = []
    for fname in os.listdir(folder):
        if not fname.endswith((".html", ".js")): continue
        fpath = os.path.join(folder, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                fcontent = f.read()
            if re.search(re.escape(query), fcontent, re.IGNORECASE):
                found_in_files.append(fname)
        except Exception:
            pass
            
    if found_in_files:
        print(f"[OK]   {name:40s} : FOUND in {', '.join(found_in_files)} (searching '{query}')")
    else:
        print(f"[FAIL] {name:40s} : NOT FOUND (searching '{query}')")
        all_found = False

print("\nAll settings parity verified:", all_found)
