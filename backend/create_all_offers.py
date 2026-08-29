import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seva_bandhu.settings')
django.setup()

from core.models import Offer, Service

now = timezone.now()
services = Service.objects.all()

print(f"Found {services.count()} services. Creating frequent offers for them...")

for i, service in enumerate(services):
    code = f'SMART_{service.name.upper().replace(" ", "_")[:10]}_{i}'
    title = f'{service.name.title()} Smart Offer'
    
    # Try to create or update an offer for this service
    offer, created = Offer.objects.update_or_create(
        applicable_service=service,
        target_segment='FREQUENT',
        defaults={
            'title': title,
            'description': f"A special 20% discount on {service.name} for our frequent customers.",
            'code': code,
            'discount_type': 'PERCENTAGE',
            'discount_value': 20.00,
            'maximum_discount': 250.00,
            'minimum_order_value': 0,
            'start_date': now - timedelta(days=1),
            'expiry_date': now + timedelta(days=90),
            'usage_limit': 1000,
            'per_customer_limit': 5,
            'active': True
        }
    )
    if created:
        print(f"Created new smart offer: {code} for {service.name}")
    else:
        print(f"Updated existing smart offer: {code} for {service.name}")

print("Successfully created/updated smart offers for all categories!")
