import re
with open('core/views.py', 'r', encoding='utf-8') as f:
    text = f.read()

pattern = r"(except Exception as e:\s+)(return JsonResponse\(\{'status': 'error', 'message': str\(e\)\}, status=500\))"
replacement = r"\1print('API ERROR:', e)\n            import traceback\n            traceback.print_exc()\n            \2"
new_text = re.sub(pattern, replacement, text)

if new_text != text:
    with open('core/views.py', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print('Patched views.py!')
else:
    print('Pattern not found!')
