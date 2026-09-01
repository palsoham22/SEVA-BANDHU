import os

cust_chat_path = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\customer\chat.html'
tech_chat_path = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\technician\chat.html'

chat_template = """{% extends "base.html" %}
{% block title %}Chat | Seva Bandhu{% endblock %}

{% block content %}
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.chat-container {
    max-width: 800px;
    margin: 40px auto;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(15, 23, 42, 0.05);
    display: flex;
    flex-direction: column;
    height: 70vh;
    font-family: 'Inter', sans-serif;
}

.chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    border-bottom: 1px solid #f1f5f9;
}

.chat-header-info {
    display: flex;
    flex-direction: column;
}

.chat-back-link {
    font-size: 14px;
    color: #64748b;
    text-decoration: none;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    margin-bottom: 4px;
}
.chat-back-link:hover { color: #0f172a; }

.chat-title {
    font-size: 18px;
    font-weight: 700;
    color: #0f172a;
    display: flex;
    align-items: center;
    gap: 8px;
}

.chat-status-active {
    font-size: 12px;
    font-weight: 700;
    color: #16a34a;
    background: #dcfce7;
    padding: 4px 10px;
    border-radius: 99px;
}

.chat-status-closed {
    font-size: 12px;
    font-weight: 700;
    color: #475569;
    background: #f1f5f9;
    padding: 4px 10px;
    border-radius: 99px;
}

.chat-messages {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    background: #f8fafc;
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.msg-bubble {
    max-width: 70%;
    padding: 12px 16px;
    border-radius: 12px;
    font-size: 14px;
    line-height: 1.5;
    position: relative;
}

.msg-sent {
    align-self: flex-end;
    background: #2563eb;
    color: #ffffff;
    border-bottom-right-radius: 4px;
}

.msg-received {
    align-self: flex-start;
    background: #e2e8f0;
    color: #0f172a;
    border-bottom-left-radius: 4px;
}

.msg-meta {
    display: block;
    font-size: 11px;
    margin-top: 6px;
    opacity: 0.8;
}

.chat-input-area {
    padding: 16px 24px;
    background: #ffffff;
    border-top: 1px solid #f1f5f9;
    border-radius: 0 0 12px 12px;
    display: flex;
    gap: 12px;
}

.chat-input {
    flex: 1;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 12px 16px;
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
    font-family: inherit;
}

.chat-input:focus {
    border-color: #2563eb;
}

.chat-send-btn {
    background: #2563eb;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 0 20px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
}

.chat-send-btn:hover { background: #1d4ed8; }
.chat-send-btn:disabled { background: #94a3b8; cursor: not-allowed; }

.chat-closed-notice {
    text-align: center;
    color: #64748b;
    font-size: 14px;
    padding: 16px;
    background: #f1f5f9;
    border-top: 1px solid #e2e8f0;
    border-radius: 0 0 12px 12px;
}
</style>

<div class="chat-container">
    <div class="chat-header">
        <div class="chat-header-info">
            <a href="{% if user_type == 'customer' %}{% url 'customer_my_requests' %}{% else %}{% url 'technician_my_jobs' %}{% endif %}" class="chat-back-link">← Back</a>
            <div class="chat-title">
                REQ-{{ service_request.id }}
            </div>
            <div style="font-size:13px; color:#64748b;">{{ service_request.service_detail.service_category }}</div>
        </div>
        <div>
            {% if service_request.status == 'Completed' %}
                <span class="chat-status-closed">CLOSED</span>
            {% else %}
                <span class="chat-status-active">ACTIVE</span>
            {% endif %}
        </div>
    </div>

    <div class="chat-messages" id="chat-messages">
        {% for msg in chat_messages %}
            {% if msg.sender.username == current_user_username %}
                <div class="msg-bubble msg-sent">
                    {{ msg.message }}
                    <span class="msg-meta">{{ msg.created_at|date:"M d, h:i A" }}</span>
                </div>
            {% else %}
                <div class="msg-bubble msg-received">
                    {{ msg.message }}
                    <span class="msg-meta">{{ msg.created_at|date:"M d, h:i A" }}</span>
                </div>
            {% endif %}
        {% endfor %}
    </div>

    {% if service_request.status != 'Completed' %}
    <div class="chat-input-area">
        <input type="text" id="chat-input" class="chat-input" placeholder="Type a message..." autocomplete="off">
        <button id="chat-send-btn" class="chat-send-btn">Send</button>
    </div>
    {% else %}
    <div class="chat-closed-notice">
        🔒 Chat is closed. This service request has been completed.
    </div>
    {% endif %}
</div>

<script>
    const reqId = "{{ service_request.id }}";
    const currentUsername = "{{ current_user_username }}";
    const status = "{{ service_request.status }}";
    
    const messagesContainer = document.getElementById('chat-messages');
    
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    scrollToBottom();

    if (status !== 'Completed') {
        const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
        const chatSocket = new WebSocket(wsProtocol + window.location.host + `/ws/chat/${reqId}/`);

        chatSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            
            if (data.type === 'error') {
                alert(data.message);
                return;
            }

            const isSent = (data.sender === currentUsername);
            const msgDiv = document.createElement('div');
            msgDiv.className = 'msg-bubble ' + (isSent ? 'msg-sent' : 'msg-received');
            
            const txtNode = document.createTextNode(data.message);
            msgDiv.appendChild(txtNode);
            
            const metaSpan = document.createElement('span');
            metaSpan.className = 'msg-meta';
            metaSpan.innerText = data.created_at;
            msgDiv.appendChild(metaSpan);
            
            messagesContainer.appendChild(msgDiv);
            scrollToBottom();
        };

        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send-btn');

        function sendMessage() {
            const message = chatInput.value.trim();
            if (message && chatSocket.readyState === WebSocket.OPEN) {
                chatSocket.send(JSON.stringify({
                    'message': message
                }));
                chatInput.value = '';
            }
        }

        sendBtn.onclick = sendMessage;
        chatInput.onkeyup = function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        };
    }
</script>
{% endblock %}
"""

cust_content = chat_template.replace("{{ user_type }}", "customer").replace("{{ current_user_username }}", "{{ customer.username }}")
tech_content = chat_template.replace("{{ user_type }}", "technician").replace("{{ current_user_username }}", "{{ technician.username }}")

with open(cust_chat_path, 'w', encoding='utf-8') as f:
    f.write(cust_content)

with open(tech_chat_path, 'w', encoding='utf-8') as f:
    f.write(tech_content)

print("Created chat templates successfully")
