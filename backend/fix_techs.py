import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seva_bandhu.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Technician_signup, Service

# Make sure all Services are enabled
Service.objects.update(is_enabled=True)

# Update existing tech_elec
tech_e = Technician_signup.objects.filter(username='tech_elec').first()
if tech_e:
    tech_e.service_category = 'Electrical'
    tech_e.save()
    print("Updated tech_elec to Electrical")

# Update tech_wash to Cleaning
tech_w = Technician_signup.objects.filter(username='tech_wash').first()
if tech_w:
    tech_w.service_category = 'Cleaning'
    tech_w.save()
    print("Updated tech_wash to Cleaning")

# tech_plumb is already 'Plumbing', just make sure it's available
tech_p = Technician_signup.objects.filter(username='tech_plumb').first()
if tech_p:
    tech_p.is_available = True
    tech_p.save()
    print("tech_plumb is available")

# Ensure AC Repair tech exists
user, created = User.objects.get_or_create(username='tech_ac', email='ac@tech.com')
if created:
    user.set_password('Password@123')
    user.save()
    
    Technician_signup.objects.create(
        user=user,
        username='tech_ac',
        email='ac@tech.com',
        contact='9876543213',
        password='Password@123',
        service_category='AC Repair',
        years_of_experience=3,
        working_locations='City Center',
        profile_completed=True,
        is_available=True
    )
    print("Created tech_ac for AC Repair")
else:
    t = Technician_signup.objects.filter(username='tech_ac').first()
    if t:
        t.service_category = 'AC Repair'
        t.is_available = True
        t.save()
        print("Updated tech_ac for AC Repair")

print("All technicians are ready and available.")
