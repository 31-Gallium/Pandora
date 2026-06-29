import sys

def analyze_braces(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    stack = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        # We need to ignore strings and comments for a clean brace match
        # But even a simple brace counter can show us the balance.
        # Let's do a basic character-by-character scan ignoring strings and comments.
        pass

    # A more robust parser to find functions and their braces:
    in_string = None
    in_comment = None
    escaped = False
    
    brace_depth = 0
    scope_starts = []
    
    idx = 0
    while idx < len(content):
        c = content[idx]
        
        if in_comment == 'single':
            if c == '\n':
                in_comment = None
            idx += 1
            continue
        elif in_comment == 'multi':
            if c == '*' and idx + 1 < len(content) and content[idx+1] == '/':
                in_comment = None
                idx += 2
            else:
                idx += 1
            continue
            
        if in_string:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == in_string:
                in_string = None
            idx += 1
            continue
            
        # Check comments
        if c == '/' and idx + 1 < len(content):
            if content[idx+1] == '/':
                in_comment = 'single'
                idx += 2
                continue
            elif content[idx+1] == '*':
                in_comment = 'multi'
                idx += 2
                continue
                
        # Check string literals
        if c in ["'", '"', '`']:
            in_string = c
            escaped = False
            idx += 1
            continue
            
        if c == '{':
            brace_depth += 1
            scope_starts.append(idx)
        elif c == '}':
            if brace_depth > 0:
                start_idx = scope_starts.pop()
                brace_depth -= 1
                # Find line number of start and end
                start_line = content[:start_idx].count('\n') + 1
                end_line = content[:idx].count('\n') + 1
                
                # Print any high-level scopes
                if brace_depth == 0 or (brace_depth == 1 and "function" in lines[start_line - 1]):
                    # Get the line text around the start line
                    start_text = lines[start_line - 1].strip()
                    end_text = lines[end_line - 1].strip()
                    print(f"Depth {brace_depth+1} Scope: Line {start_line} '{start_text}' -> Line {end_line} '{end_text}'")
            else:
                print(f"Unmatched closing brace at line {content[:idx].count('\n') + 1}")
        idx += 1
        
    print("Final brace depth:", brace_depth)
    if brace_depth > 0:
        print("Unclosed scopes started at lines:")
        for s in scope_starts:
            print("  Line", content[:s].count('\n') + 1, ":", lines[content[:s].count('\n')].strip())

if __name__ == '__main__':
    analyze_braces(r"c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\ui_dashboard_common.js")
