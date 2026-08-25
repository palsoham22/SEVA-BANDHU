import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seva_bandhu.settings')
django.setup()

from core.models import Offer, Service
from django.utils import timezone
from datetime import timedelta

# Clear existing test offers
Offer.objects.filter(code__in=['WELCOME50', 'SAVE150', 'AC20OFF', 'FREQUENT10', 'FREQ_AC', 'FREQ_PLUMB', 'FREQ_ELEC', 'FREQ_CLEAN']).delete()

now = timezone.now()

# 1. Welcome Offer (New Customers)
Offer.objects.create(
    title='Welcome Bonus 50% Off',
    description='Get 50% off on your first service booking with Seva Bandhu!',
    code='WELCOME50',
    discount_type='PERCENTAGE',
    discount_value=50.00,
    maximum_discount=200.00,
    minimum_order_value=0,
    target_segment='NEW_CUSTOMER',
    start_date=now - timedelta(days=1),
    expiry_date=now + timedelta(days=30),
    usage_limit=1000,
    per_customer_limit=1,
    active=True
)
print('Created Welcome Offer: WELCOME50')

# 2. Global Flat Discount (All Customers)
Offer.objects.create(
    title='Flat ₹150 Off on Any Service',
    description='Enjoy a flat discount of ₹150 on all services with minimum order value of ₹500.',
    code='SAVE150',
    discount_type='FLAT',
    discount_value=150.00,
    minimum_order_value=500.00,
    target_segment='ALL',
    start_date=now - timedelta(days=1),
    expiry_date=now + timedelta(days=30),
    usage_limit=500,
    per_customer_limit=2,
    active=True
)
print('Created Global Flat Offer: SAVE150')



# 4. Smart/Frequent Customer Category-Specific Offers
frequent_discounts = [
    {'code': 'FREQ_AC', 'title': 'AC Loyalty 15% Off', 'service': 'AC Repair', 'discount': 15.00},
    {'code': 'FREQ_PLUMB', 'title': 'Plumbing Loyalty 10% Off', 'service': 'Plumbing', 'discount': 10.00},
    {'code': 'FREQ_ELEC', 'title': 'Electrical Loyalty 10% Off', 'service': 'Electrical', 'discount': 10.00},
    {'code': 'FREQ_CLEAN', 'title': 'Cleaning Loyalty 20% Off', 'service': 'Cleaning', 'discount': 20.00},
]

for fd in frequent_discounts:
    service_obj = Service.objects.filter(name__iexact=fd['service']).first()
    if service_obj:
        Offer.objects.create(
            title=fd['title'],
            description=f"A special {fd['discount']}% discount on {fd['service']} just for being a frequent Seva Bandhu customer.",
            code=fd['code'],
            discount_type='PERCENTAGE',
            discount_value=fd['discount'],
            maximum_discount=150.00,
            minimum_order_value=0,
            applicable_service=service_obj,
            target_segment='FREQUENT',
            start_date=now - timedelta(days=1),
            expiry_date=now + timedelta(days=90),
            usage_limit=500,
            per_customer_limit=5,
            active=True
        )
        print(f"Created Frequent Customer Offer: {fd['code']} for {fd['service']}")
    else:
        print(f"Service {fd['service']} not found, skipping {fd['code']}")

print('All sample offers created successfully!')
