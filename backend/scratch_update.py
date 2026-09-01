import re
import os

filepath = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\backend\core\views.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Normalize line endings for reliable replace
content = content.replace('\r\n', '\n')

old_assign = """        # [FIRE] ASSIGN JOB
        service_request.technician_username = technician.username
        service_request.status = 'Assigned'
        service_request.save()"""

new_assign = """        # [FIRE] ASSIGN JOB
        service_request.technician_username = technician.username
        service_request.status = 'Assigned'
        service_request.save()

        # [FIRE] CREATE CHAT
        from core.models import ChatConversation
        ChatConversation.objects.get_or_create(service_request=service_request)"""

old_complete = """                technician.is_available = True
                technician.save()
                print("[ICON] Technician is now AVAILABLE")"""

new_complete = """                technician.is_available = True
                technician.save()
                
                # [FIRE] CLOSE CHAT
                from core.models import ChatConversation
                from django.utils import timezone
                chat, created = ChatConversation.objects.get_or_create(service_request=job)
                chat.is_active = False
                chat.closed_at = timezone.now()
                chat.save()

                print("[ICON] Technician is now AVAILABLE")"""

content = content.replace(old_assign, new_assign)
content = content.replace(old_complete, new_complete)

with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("Replaced successfully")
