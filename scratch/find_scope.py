import re

with open(r'c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\ui_dashboard_common.js', encoding='utf-8') as f:
    lines = f.read().split('\n')

start = 98  # line 99 is initGlobalUI (0-indexed: 98)
depth = 0
found_end = None

for i in range(start, len(lines)):
    line = lines[i]
    # Simple brace counting (skip strings/comments roughly)
    stripped = re.sub(r'//.*$', '', line)
    stripped = re.sub(r'/\*.*?\*/', '', stripped)
    stripped = re.sub(r'"[^"]*"', '', stripped)
    stripped = re.sub(r"'[^']*'", '', stripped)
    stripped = re.sub(r'`[^`]*`', '', stripped)
    
    opens = stripped.count('{')
    closes = stripped.count('}')
    depth += opens - closes
    
    if depth == 0 and found_end is None and i > start:
        found_end = i + 1
        print(f'initGlobalUI ends at line {found_end}')
        break

print(f'Total lines: {len(lines)}')

# Show what's after initGlobalUI
if found_end:
    print(f'\nLines after initGlobalUI ({found_end} to {min(found_end+20, len(lines))}):')
    for i in range(found_end - 1, min(found_end + 20, len(lines))):
        print(f'{i+1}: {lines[i][:100]}')
