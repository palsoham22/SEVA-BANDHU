import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seva_bandhu.settings')
django.setup()

from core.models import customer_signup, ServiceRequest
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

customer = customer_signup.objects.first()
now_dt = timezone.now()

cooldown_hours = getattr(settings, 'SMART_OFFER_COOLDOWN_HOURS', 24)
cooldown_clear = True
if customer.last_offer_popup_at:
    hours_since_last = (now_dt - customer.last_offer_popup_at).total_seconds() / 3600
    if hours_since_last < cooldown_hours:
        cooldown_clear = False

no_booking_days = getattr(settings, 'SMART_OFFER_NO_BOOKING_DAYS', 7)

# Are there any recent bookings?
recent_booking = ServiceRequest.objects.filter(
    customer_username=customer.username,
    status__in=['Assigned', 'In Progress', 'Completed'],
    created_at__gte=now_dt - timedelta(days=no_booking_days)
).exists()

print('cooldown_clear:', cooldown_clear)
print('recent_booking:', recent_booking)
if recent_booking:
    bookings = ServiceRequest.objects.filter(
        customer_username=customer.username,
        status__in=['Assigned', 'In Progress', 'Completed'],
        created_at__gte=now_dt - timedelta(days=no_booking_days)
    )
    for b in bookings:
        print('Recent booking found:', b.id, b.status, b.created_at)
