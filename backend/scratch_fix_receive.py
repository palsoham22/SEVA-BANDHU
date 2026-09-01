import os

consumers_path = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\backend\core\consumers.py'
with open(consumers_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = "    async def receive(self, text_data):"
replacement = "    async def receive(self, text_data=None, bytes_data=None):"

content = content.replace(target, replacement)

with open(consumers_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print("Fixed receive signature")
