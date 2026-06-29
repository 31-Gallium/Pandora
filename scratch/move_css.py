import re

with open('dashboard.py', 'r', encoding='utf-8') as f:
    dashboard_py = f.read()

m = re.search(r'SCROLLBAR_CSS = \"\"\"(.*?)\"\"\"', dashboard_py, re.DOTALL)
if m:
    with open('main.py', 'r', encoding='utf-8') as f:
        main_py = f.read()
    
    css = 'SCROLLBAR_CSS = \"\"\"' + m.group(1) + '\"\"\"\n'
    
    # insert SCROLLBAR_CSS
    if 'SCROLLBAR_CSS =' not in main_py:
        main_py = main_py.replace('import sys\nimport os', 'import sys\nimport os\n\n' + css)
    
    # remove DashboardUI import
    main_py = re.sub(r'from dashboard import DashboardUI\s*\n', '', main_py)
    
    # modify initialization
    # DashboardUI is initialized inside launch_gui() or somewhere.
    # Actually let's just see where DashboardUI is used.
    
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(main_py)
    print('main.py updated')
