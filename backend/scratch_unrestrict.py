import os

# 1. Modify consumers.py
consumers_path = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\backend\core\consumers.py'
with open(consumers_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """        # Re-verify status
        self.service_request = await self.get_service_request(self.request_id)
        if self.service_request.status == 'Completed':
            # Send error back to sender
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Cannot send messages on a completed request.'
            }))
            return
            
        if self.service_request.status == 'Pending':
            return"""

content = content.replace(target, """        # Re-verify status
        self.service_request = await self.get_service_request(self.request_id)
        # Allow chatting even on completed requests for testing purposes""")

with open(consumers_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)


# 2. Modify customer/chat.html and technician/chat.html
for html_path in [
    r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\customer\chat.html',
    r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\technician\chat.html'
]:
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    html = html.replace("{% if service_request.status != 'Completed' %}", "")
    html = html.replace("""    {% else %}
    <div class="chat-closed-notice">
        🔒 Chat is closed. This service request has been completed.
    </div>
    {% endif %}""", "")
    
    html = html.replace("if (status !== 'Completed') {", "if (true) {")
    
    with open(html_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)

print("Removed 'Completed' restriction from chat functionality.")
