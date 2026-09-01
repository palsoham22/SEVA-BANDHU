import os

for html_path in [
    r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\customer\chat.html',
    r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\technician\chat.html'
]:
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    target_badge = """        <div>
            {% if service_request.status == 'Completed' %}
                <span class="chat-status-closed">CLOSED</span>
            {% else %}
                <span class="chat-status-active">ACTIVE</span>
            {% endif %}
        </div>"""
        
    replacement_badge = """        <div>
            <span class="chat-status-active">ACTIVE</span>
        </div>"""

    html = html.replace(target_badge.replace('\r\n', '\n'), replacement_badge.replace('\r\n', '\n'))
    with open(html_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)

print("Removed closed badge")
