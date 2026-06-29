import re

with open('electron_dashboard/prototype.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Extract CSS
style_match = re.search(r'<style>(.*?)</style>', content, re.DOTALL)
if style_match:
    with open('electron_dashboard/style.css', 'w', encoding='utf-8') as f:
        f.write(style_match.group(1).strip())
    content = content[:style_match.start()] + '<link rel="stylesheet" href="style.css">\n' + content[style_match.end():]

# Extract JS
script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if script_match:
    with open('electron_dashboard/temp_inline.js', 'w', encoding='utf-8') as f:
        f.write(script_match.group(1).strip())
    content = content[:script_match.start()] + '<script src="renderer.js"></script>\n' + content[script_match.end():]

with open('electron_dashboard/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Extracted successfully')
