with open(r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\prototype.html", "r", encoding="utf-8") as f:
    html = f.read()

# Let's find where the <script> tags are and see how much script there is
import re
scripts = re.findall(r'<script>(.*?)</script>', html, re.DOTALL)
print("Found", len(scripts), "script tags")
for idx, s in enumerate(scripts):
    print(f"Script {idx+1} size: {len(s)} characters")
    
# Let's find functions defined in the first script
functions = re.findall(r'function\s+(\w+)\s*\(', scripts[0])
print("\n--- Functions in first script ---")
for f in sorted(list(set(functions))):
    print("-", f)
