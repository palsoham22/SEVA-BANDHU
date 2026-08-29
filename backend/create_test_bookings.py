import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seva_bandhu.settings')
django.setup()

from django.utils import timezone
from core.models import ServiceRequest, customer_signup, ServiceDetail, ServiceAddress

c = customer_signup.objects.first()
dt = timezone.now() - timedelta(days=8)

for i in range(3):
    sd = ServiceDetail.objects.create(
        service_category='AC Repair', 
        problem_description='Test', 
        priority='Low', 
        preferred_service_date=dt.date(),
        preferred_time_slot='Morning', 
        contact_number='0000000000'
    )
    
    sa = ServiceAddress.objects.create(
        house_flat_no='1', 
        street_area='Test', 
        city='Test', 
        pincode='123456'
    )
    
    sr = ServiceRequest.objects.create(
        customer_username=c.username, 
        service_detail=sd, 
        service_address=sa, 
        status='Completed', 
        payment_method='offline', 
        amount=500
    )
    # Manually backdate created_at and updated_at
    ServiceRequest.objects.filter(id=sr.id).update(created_at=dt, updated_at=dt)

print('Successfully created 3 backdated, completed test bookings for', c.username)
