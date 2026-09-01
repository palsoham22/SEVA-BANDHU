import os

filepath = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\backend\core\views.py'
with open(filepath, 'a', encoding='utf-8', newline='\n') as f:
    f.write('''
# ==========================================
# REAL-TIME CHAT VIEWS
# ==========================================
def customer_chat(request, request_id):
    if not request.user.is_authenticated:
        return redirect('customer_login')

    try:
        customer = customer_signup.objects.filter(user=request.user).first()
        if not customer:
            return redirect('customer_login')
    except customer_signup.DoesNotExist:
        return redirect('customer_login')

    service_request = get_object_or_404(
        ServiceRequest,
        id=request_id,
        customer_username=customer.username
    )

    from core.models import ChatConversation
    conversation = ChatConversation.objects.filter(service_request=service_request).first()
    messages = conversation.messages.all() if conversation else []

    return render(request, 'customer/chat.html', {
        'service_request': service_request,
        'chat_messages': messages,
        'conversation': conversation,
        'customer': customer
    })

def technician_chat(request, request_id):
    if not request.user.is_authenticated:
        return redirect('technician_login')

    try:
        technician = Technician_signup.objects.get(user=request.user)
    except Technician_signup.DoesNotExist:
        return redirect('technician_login')

    service_request = get_object_or_404(
        ServiceRequest,
        id=request_id,
        technician_username=technician.username
    )

    from core.models import ChatConversation
    conversation = ChatConversation.objects.filter(service_request=service_request).first()
    messages = conversation.messages.all() if conversation else []

    return render(request, 'technician/chat.html', {
        'service_request': service_request,
        'chat_messages': messages,
        'conversation': conversation,
        'technician': technician
    })
''')

print("Appended views successfully")
