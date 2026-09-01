import os

routing_path = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\backend\core\routing.py'
with open(routing_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = "]"
replacement = """    re_path(r'^.*$', consumers.ChatConsumer.as_asgi()),\n]"""

if target in content:
    content = content.replace(target, replacement)
else:
    print("Could not find ] in routing.py")

with open(routing_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print("Added catch-all route")
