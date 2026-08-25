from core.models import ServiceRequest, customer_signup, Service
from django.db.models import Sum

def get_customer_context(customer_username):
    """
    Retrieves the necessary context for the AI Chatbot 
    belonging to the currently authenticated customer.
    """
    try:
        customer = customer_signup.objects.get(username=customer_username)
    except customer_signup.DoesNotExist:
        return None

    # Fetch all service requests for this customer
    service_requests = ServiceRequest.objects.filter(customer_username=customer_username).order_by('-created_at')
    
    # Categorize requests
    active_requests = service_requests.exclude(status='Completed')
    completed_requests = service_requests.filter(status='Completed')

    # Available services
    services = Service.objects.filter(is_enabled=True).values('name', 'price')

    context_data = {
        "customer_name": customer.username,
        "contact": customer.contact,
        "email": customer.email,
        "active_requests": [
            {
                "id": req.id,
                "service": req.service_detail.service_category,
                "status": req.status,
                "technician": req.technician_username or "Not Assigned",
                "payment_status": req.payment_status,
                "amount": float(req.amount),
                "scheduled_date": str(req.service_detail.preferred_service_date),
                "scheduled_time": req.service_detail.preferred_time_slot,
            }
            for req in active_requests
        ],
        "completed_requests": [
            {
                "id": req.id,
                "service": req.service_detail.service_category,
                "technician": req.technician_username,
                "amount": float(req.amount),
            }
            for req in completed_requests[:5] # Limit to recent 5
        ],
        "available_services": list(services),
    }

    return context_data
