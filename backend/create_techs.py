import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seva_bandhu.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Technician_signup, Service

# Remove AC Service if it exists in DB
ac_service = Service.objects.filter(name='AC Service').first()
if ac_service:
    ac_service.delete()
    print("Deleted AC Service from DB")

techs = [
    {
        'username': 'tech_elec',
        'email': 'elec@tech.com',
        'contact': '9876543210',
        'service_category': 'Electrician'
    },
    {
        'username': 'tech_wash',
        'email': 'wash@tech.com',
        'contact': '9876543211',
        'service_category': 'Washing Machine Service'
    },
    {
        'username': 'tech_plumb',
        'email': 'plumb@tech.com',
        'contact': '9876543212',
        'service_category': 'Plumbing'
    }
]

for t in techs:
    user, created = User.objects.get_or_create(username=t['username'], email=t['email'])
    if created:
        user.set_password('Password@123')
        user.save()
        
        tech = Technician_signup.objects.create(
            user=user,
            username=t['username'],
            email=t['email'],
            contact=t['contact'],
            password='Password@123',
            service_category=t['service_category'],
            years_of_experience=3,
            working_locations='City Center',
            profile_completed=True,
            is_available=True
        )
        print(f"Created technician {t['username']} for {t['service_category']} with password Password@123")
    else:
        print(f"Technician {t['username']} already exists")
