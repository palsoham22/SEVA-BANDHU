import os

filepath = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\SevaBandhu-Frontend\templates\technician\my_job.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """                <a href="{% url 'technician_navigation' job.id %}" class="btn-action btn-action-success">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
                    Open Live Navigation Map
                </a>
            </div>
            {% endif %}"""

replacement = """                <a href="{% url 'technician_navigation' job.id %}" class="btn-action btn-action-success">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>
                    Open Live Navigation Map
                </a>
                
                <a href="{% url 'technician_chat' job.id %}" class="btn-action btn-action-primary" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    Chat with Customer
                </a>
            </div>
            {% else %}
            <div class="job-actions-cluster">
                <a href="{% url 'technician_chat' job.id %}" class="btn-action btn-action-outline">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    View Chat History
                </a>
            </div>
            {% endif %}"""

content = content.replace('\r\n', '\n')
target = target.replace('\r\n', '\n')
replacement = replacement.replace('\r\n', '\n')

content = content.replace(target, replacement)

with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("Updated my_job.html successfully")
