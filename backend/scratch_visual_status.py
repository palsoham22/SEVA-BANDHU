import os

for html_path in [
    r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\customer\chat.html',
    r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\technician\chat.html'
]:
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Add a status label
    target_html = """        <button id="chat-send-btn" class="chat-send-btn">Send</button>
    </div>"""
    
    replacement_html = """        <button id="chat-send-btn" class="chat-send-btn">Send</button>
        <div id="ws-status" style="font-size: 11px; color: gray; align-self: center;">Connecting...</div>
    </div>"""
    
    if target_html in html:
        html = html.replace(target_html, replacement_html)
    
    # Update JS to change the label
    target_js = """        chatSocket.onopen = function(e) {
            console.log("WebSocket connected!");
        };"""
        
    replacement_js = """        chatSocket.onopen = function(e) {
            document.getElementById('ws-status').innerText = 'Connected';
            document.getElementById('ws-status').style.color = 'green';
        };"""
        
    if target_js in html:
        html = html.replace(target_js, replacement_js)
        
    target_js2 = """        chatSocket.onclose = function(e) {
            alert("WebSocket connection closed unexpectedly.");
        };"""
        
    replacement_js2 = """        chatSocket.onclose = function(e) {
            document.getElementById('ws-status').innerText = 'Disconnected';
            document.getElementById('ws-status').style.color = 'red';
            alert("WebSocket connection closed unexpectedly.");
        };"""
        
    if target_js2 in html:
        html = html.replace(target_js2, replacement_js2)
        
    with open(html_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)

print("Added visual connection status")
