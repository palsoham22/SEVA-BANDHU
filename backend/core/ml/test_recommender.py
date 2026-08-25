import os
import sys
import django
from datetime import timedelta
import random

# Setup django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seva_bandhu.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User
from core.models import Service, ServiceRequest, ServiceDetail, ServiceAddress, customer_signup
from core.ml.recommender import get_recommendations
import core.ml.train_recommender as trainer

def setup_dummy_data():
    print("--- Setting up Dummy Data for ML Testing ---")
    
    # Ensure Services exist
    services = ['AC Repair', 'Plumbing', 'Electrical', 'Cleaning']
    for s in services:
        Service.objects.get_or_create(name=s, defaults={'price': 500, 'is_enabled': True})

    # Dummy Customers
    customers = [
        {'user': 'test_cust_A', 'email': 'a@test.com'},
        {'user': 'test_cust_B', 'email': 'b@test.com'},
        {'user': 'test_cust_C', 'email': 'c@test.com'} # No history
    ]
    
    for c in customers:
        user, _ = User.objects.get_or_create(username=c['user'], email=c['email'])
        customer_signup.objects.get_or_create(user=user, username=c['user'], email=c['email'])
        # Clear existing history for these dummies
        ServiceRequest.objects.filter(customer_username=c['user']).delete()

    now = timezone.now()
    
    # Helper to create requests
    def create_history(username, category, count, days_ago_start):
        for i in range(count):
            sd = ServiceDetail.objects.create(service_category=category, problem_description="Test", preferred_service_date=now.date(), preferred_time_slot="10 AM - 12 PM")
            sa = ServiceAddress.objects.create(city="Test City")
            sr = ServiceRequest.objects.create(
                customer_username=username,
                service_detail=sd,
                service_address=sa,
                status='Completed',
                payment_status='paid'
            )
            # Override created_at for recency testing
            sr.created_at = now - timedelta(days=days_ago_start - (i * 2))
            sr.save()

    # Customer A: AC Heavy (Recent)
    create_history('test_cust_A', 'Electrical', 6, 15)
    create_history('test_cust_A', 'AC Repair', 2, 5)
    create_history('test_cust_A', 'Plumbing', 1, 30)

    # Customer B: Plumbing/Electrical Heavy (Older)
    create_history('test_cust_B', 'Plumbing', 5, 60)
    create_history('test_cust_B', 'Electrical', 3, 20)
    create_history('test_cust_B', 'AC Repair', 1, 90)

    print("Dummy data seeded.")

def run_tests():
    print("\n--- Training Model ---")
    trainer.train_model()
    
    print("\n--- Testing Recommendations ---")
    
    for user in ['test_cust_A', 'test_cust_B', 'test_cust_C']:
        recs = get_recommendations(user, max_results=3)
        print(f"\nRecommendations for {user}:")
        for i, r in enumerate(recs, 1):
            print(f" {i}. {r['service'].name} (Score: {r['recommendation_score']}) - {r['reason']}")

if __name__ == '__main__':
    setup_dummy_data()
    run_tests()
