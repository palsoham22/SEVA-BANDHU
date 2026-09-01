import os

consumers_path = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\backend\core\consumers.py'
with open(consumers_path, 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Remove all lines containing ws_debug.log
lines = content.split('\n')
new_lines = [line for line in lines if 'ws_debug.log' not in line]
content = '\n'.join(new_lines)

with open(consumers_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print("Removed ws_debug.log writes from consumers.py")
