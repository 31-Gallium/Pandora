css = """
SCROLLBAR_CSS = '''
QScrollArea, QScrollArea > QWidget > QWidget, QListWidget, QListView, QTextEdit, QPlainTextEdit {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    width: 6px;
    background: transparent;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 40);
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 80);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    border: none;
    height: 0px;
    width: 0px;
}

QScrollBar:horizontal {
    height: 6px;
    background: transparent;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 40);
    border-radius: 3px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(255, 255, 255, 80);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
    border: none;
    height: 0px;
    width: 0px;
}
'''
"""
with open('main.py', 'r', encoding='utf-8') as f:
    main_py = f.read()

if 'SCROLLBAR_CSS =' not in main_py:
    main_py = main_py.replace('import sys', 'import sys\n' + css + '\n')
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(main_py)
    print('Inserted SCROLLBAR_CSS')
