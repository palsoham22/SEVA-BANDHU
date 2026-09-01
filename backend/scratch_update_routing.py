import os

routing_path = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\backend\core\routing.py'
with open(routing_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    re_path(
        r'ws/chat/(?P<request_id>\d+)/$',
        consumers.ChatConsumer.as_asgi()
    ),"""

replacement = """    path('ws/chat/<int:request_id>/', consumers.ChatConsumer.as_asgi()),"""

if "from django.urls import path" not in content:
    content = content.replace("from django.urls import re_path", "from django.urls import re_path, path")

if target in content:
    content = content.replace(target, replacement)
else:
    # Try normalized
    content = content.replace('\r\n', '\n').replace(target.replace('\r\n', '\n'), replacement)

with open(routing_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print("Updated routing.py to use path")
