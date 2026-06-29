from html.parser import HTMLParser

void_elements = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr', 'polyline', 'line', 'circle', 'path', 'polygon', 'rect', 'feGaussianBlur', 'feMergeNode'}

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.tabs = {}

    def handle_starttag(self, tag, attrs):
        if tag in void_elements:
            return
            
        attr_dict = dict(attrs)
        tag_id = attr_dict.get('id', '')
        classes = attr_dict.get('class', '')
        
        self.stack.append((tag, tag_id, classes, self.getpos()[0]))
        
        if 'tab-page' in classes:
            print(f"[{self.getpos()[0]}] Started tab: {tag_id} (Depth: {len(self.stack)})")
            self.tabs[tag_id] = len(self.stack)

    def handle_endtag(self, tag):
        if tag in void_elements:
            return
            
        if not self.stack:
            print(f"[{self.getpos()[0]}] Unmatched end tag: </{tag}>")
            return
            
        start_tag, start_id, start_classes, start_line = self.stack.pop()
        
        if tag != start_tag:
            print(f"[{self.getpos()[0]}] Mismatched tag! Expected </{start_tag}> (from line {start_line}), got </{tag}>")
            
        if 'tab-page' in start_classes:
            print(f"[{self.getpos()[0]}] Ended tab: {start_id} (Depth: {len(self.stack)+1})")

parser = MyHTMLParser()
with open(r'c:\Users\Base\Desktop\Seb\Pandora\electron_dashboard\index.html', encoding='utf-8') as f:
    parser.feed(f.read())

if parser.stack:
    print(f"Unclosed tags at EOF: {len(parser.stack)}")
    for tag, tid, cls, line in parser.stack:
        if 'tab-page' in cls:
            print(f"  - <{tag} id='{tid}' class='{cls}'> from line {line}")
        elif len(parser.stack) <= 10 or line > 450:
            print(f"  - <{tag} id='{tid}' class='{cls}'> from line {line}")
