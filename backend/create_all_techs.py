import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seva_bandhu.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Technician_signup, Service

services = Service.objects.all()
techs_created = []

for i, service in enumerate(services):
    username = f'tech_{service.name.lower().replace(" ", "_")}_{i}'
    email = f'{username}@example.com'
    password = 'Password@123'
    
    user, created = User.objects.get_or_create(username=username, email=email)
    if created:
        user.set_password(password)
        user.save()
        
        Technician_signup.objects.create(
            user=user,
            username=username,
            email=email,
            contact=f'99999999{i:02d}',
            password=password,
            service_category=service.name,
            years_of_experience=5,
            working_locations='All locations',
            profile_completed=True,
            is_available=True
        )
        techs_created.append({'service': service.name, 'username': username, 'password': password})
        print(f"Created technician {username} for {service.name} with password {password}")
    else:
        print(f"Technician {username} already exists")

print("\n--- Summary of Created Technicians ---")
for t in techs_created:
    print(f"Category: {t['service']} | Username: {t['username']} | Password: {t['password']}")
