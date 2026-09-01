import os

filepath = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\customer\my_requests.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                    {% if request.status == 'In Progress' or request.status == 'Accepted' or request.status == 'Assigned' %}
                    <a href="{% url 'customer_tracking' request.id %}" class="btn-card-action btn-action-blue">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 12 8 12s8-6.75 8-12a8 8 0 0 0-8-8z"/><circle cx="12" cy="10" r="3"/></svg>
                        Track Technician
                    </a>
                    {% endif %}"""

replacement = """                    {% if request.status == 'In Progress' or request.status == 'Accepted' or request.status == 'Assigned' %}
                    <a href="{% url 'customer_tracking' request.id %}" class="btn-card-action btn-action-blue">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 12 8 12s8-6.75 8-12a8 8 0 0 0-8-8z"/><circle cx="12" cy="10" r="3"/></svg>
                        Track Technician
                    </a>
                    {% endif %}
                    
                    {% if request.status != 'Pending' %}
                    <a href="{% url 'customer_chat' request.id %}" class="btn-card-action btn-action-blue">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                        Chat with Technician
                    </a>
                    {% endif %}"""

# Normalize line endings
content = content.replace('\r\n', '\n')
target = target.replace('\r\n', '\n')
replacement = replacement.replace('\r\n', '\n')

content = content.replace(target, replacement)

with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("Updated my_requests.html successfully")
