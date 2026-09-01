import os

for html_path in [
    r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\customer\chat.html',
    r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\technician\chat.html'
]:
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    target_js = """        function sendMessage() {
            const message = chatInput.value.trim();
            if (message && chatSocket.readyState === WebSocket.OPEN) {
                chatSocket.send(JSON.stringify({
                    'message': message
                }));
                chatInput.value = '';
            }
        }"""
        
    replacement_js = """        chatSocket.onopen = function(e) {
            console.log("WebSocket connected!");
        };
        
        chatSocket.onclose = function(e) {
            alert("WebSocket connection closed unexpectedly.");
        };
        
        chatSocket.onerror = function(err) {
            alert("WebSocket error occurred.");
        };

        function sendMessage() {
            const message = chatInput.value.trim();
            if (message) {
                if (chatSocket.readyState === WebSocket.OPEN) {
                    chatSocket.send(JSON.stringify({
                        'message': message
                    }));
                    chatInput.value = '';
                } else {
                    alert("Cannot send. WebSocket state is: " + chatSocket.readyState + "\\nURL: " + wsProtocol + window.location.host + `/ws/chat/${reqId}/`);
                }
            }
        }"""

    html = html.replace(target_js.replace('\r\n', '\n'), replacement_js.replace('\r\n', '\n'))
    with open(html_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(html)

print("Added JS debugging")
