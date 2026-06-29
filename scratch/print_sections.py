import re

with open(r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\prototype.html", "r", encoding="utf-8") as f:
    html = f.read()

lines = html.splitlines()

def print_lines(start_line, end_line):
    print(f"\n=== Lines {start_line} to {end_line} ===")
    for i in range(start_line - 1, min(len(lines), end_line)):
        safe_line = lines[i].encode('ascii', 'ignore').decode('ascii')
        print(f"{i+1:4d}: {safe_line}")

print_lines(1550, 1728)
