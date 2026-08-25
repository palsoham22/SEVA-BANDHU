from django.test import TestCase, Client
from django.contrib.auth.models import User
from core.models import customer_signup, Service, Offer, ServiceRequest, ServiceDetail, ServiceAddress, CustomerOffer
from django.utils import timezone
from datetime import timedelta

class SmartOfferIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.now = timezone.now()
        
        Service.objects.update(is_enabled=True)
        self.svc, _ = Service.objects.get_or_create(name='AC Repair', defaults={'price': 1000})
        self.svc_clean, _ = Service.objects.get_or_create(name='Cleaning', defaults={'price': 500})
        
        self.u1 = User.objects.create_user(username='test_smart1', password='password123')
        self.c1 = customer_signup.objects.create(user=self.u1, username='test_smart1', email_verified=True, contact='9999999991')
        
        self.u2 = User.objects.create_user(username='test_smart2', password='password123')
        self.c2 = customer_signup.objects.create(user=self.u2, username='test_smart2', email_verified=True, contact='9999999992')
        
        self.ac_offer = Offer.objects.create(
            title='AC Test Offer',
            code='TEST_AC_OFFER',
            discount_type='FLAT',
            discount_value=100.00,
            applicable_service=self.svc,
            target_segment='ALL',
            active=True,
            start_date=self.now - timedelta(days=1),
            expiry_date=self.now + timedelta(days=30),
            usage_limit=100,
            per_customer_limit=1
        )
        
        self.client.login(username='test_smart1', password='password123')

    def test_ideal_flow_triggers_smart_offer(self):
        """Test 1: 3 views, no booking, offer eligible -> triggers offer."""
        session = self.client.session
        session['smart_offer_intent'] = {}
        session.save()
        
        self.client.get('/customer/create_request/?service=AC%20Repair')
        self.client.get('/customer/create_request/?service=AC%20Repair')
        response = self.client.get('/customer/create_request/?service=AC%20Repair')
        
        self.assertIn(b'TEST_AC_OFFER', response.content, "Smart offer popup should appear after 3 views.")

    def test_booking_applies_offer(self):
        """Test 2: Customer Books -> Offer applied/redeemed."""
        post_data = {
            'service_category': 'AC Repair',
            'problem_description': 'Test',
            'priority': 'Medium',
            'preferred_service_date': (self.now.date() + timedelta(days=1)).strftime('%Y-%m-%d'),
            'preferred_time_slot': '10 AM - 12 PM',
            'contact_number': '1234567890',
            'payment_method': 'offline',
            'house_flat_no': '123',
            'street_area': 'Main St',
            'city': 'TestCity',
            'pincode': '123456',
            'applied_promo_code': 'TEST_AC_OFFER'
        }
        self.client.post('/customer/create_request/?service=AC%20Repair', data=post_data)
        
        sr = ServiceRequest.objects.filter(customer_username='test_smart1').order_by('-created_at').first()
        self.assertIsNotNone(sr)
        self.assertEqual(sr.applied_offer, self.ac_offer)
        
        co = CustomerOffer.objects.filter(customer=self.c1, offer=self.ac_offer).first()
        self.assertIsNotNone(co)
        self.assertTrue(co.redeemed)

    def test_cooldown_prevents_popup(self):
        """Test 3: View Service Again -> Cooldown Prevents Popup."""
        # Set cooldown
        self.c1.last_offer_popup_at = self.now
        self.c1.save()
        
        self.client.get('/customer/create_request/?service=AC%20Repair')
        self.client.get('/customer/create_request/?service=AC%20Repair')
        response = self.client.get('/customer/create_request/?service=AC%20Repair')
        
        self.assertNotIn(b'TEST_AC_OFFER', response.content, "Popup appeared despite cooldown.")

    def test_recent_booking_prevents_popup(self):
        """Test 4: Give customer completed booking within 7 days -> No Trigger."""
        self.c1.last_offer_popup_at = self.now - timedelta(days=5) 
        self.c1.save()
        
        sd = ServiceDetail.objects.create(service_category='Cleaning', problem_description='Test', preferred_service_date=self.now.date(), preferred_time_slot='10 AM')
        sa = ServiceAddress.objects.create(city='TestCity', house_flat_no='12', street_area='St', pincode='123456')
        recent_sr = ServiceRequest.objects.create(
            customer_username='test_smart1', 
            status='Completed', 
            service_detail=sd,
            service_address=sa,
        )
        ServiceRequest.objects.filter(id=recent_sr.id).update(created_at=self.now - timedelta(days=2))
        
        session = self.client.session
        session['smart_offer_intent'] = {}
        session.save()
        
        self.client.get('/customer/create_request/?service=Cleaning')
        self.client.get('/customer/create_request/?service=Cleaning')
        response = self.client.get('/customer/create_request/?service=Cleaning')
        
        self.assertNotIn(b'smartOfferModal', response.content, "Popup appeared despite recent booking.")

    def test_ineligible_customer_no_offer(self):
        """Test 5: Ineligible Customer -> No Offer."""
        Offer.objects.all().delete()
        
        Offer.objects.create(
            title='Freq Test Offer',
            code='FREQ_TEST',
            discount_type='FLAT',
            discount_value=50.00,
            applicable_service=self.svc_clean,
            target_segment='FREQUENT',
            active=True,
            start_date=self.now - timedelta(days=1),
            expiry_date=self.now + timedelta(days=30),
            usage_limit=100,
            per_customer_limit=1
        )
        
        self.client.logout()
        self.client.login(username='test_smart2', password='password123')
        session = self.client.session
        session['smart_offer_intent'] = {}
        session.save()
        
        self.client.get('/customer/create_request/?service=Cleaning')
        self.client.get('/customer/create_request/?service=Cleaning')
        response = self.client.get('/customer/create_request/?service=Cleaning')
        
        self.assertNotIn(b'FREQ_TEST', response.content)
        self.assertNotIn(b'smartOfferModal', response.content)
