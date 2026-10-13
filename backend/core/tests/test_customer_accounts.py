from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import customer_signup


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class CustomerAccountFlowTests(TestCase):
    def signup(self):
        return self.client.post(reverse('customer_signup'), {
            'username': 'newcustomer', 'email': 'customer@example.com',
            'contact': '9876543210', 'password': 'StrongPass123!',
        })

    def verify_email_code(self):
        session = self.client.session
        session['verification_code_email'] = 'customer@example.com'
        session['verification_code_created_at'] = 2_000_000_000
        import hashlib
        session['verification_code_hash'] = hashlib.sha256(b'123456').hexdigest()
        session.save()
        return self.client.post(reverse('verify_email_code'), data='{"email":"customer@example.com","code":"123456"}',
                                content_type='application/json')

    def test_signup_requires_a_verified_email_code_before_creating_account(self):
        response = self.signup()
        self.assertContains(response, 'Please verify this email before signing up')
        self.assertFalse(User.objects.filter(username='newcustomer').exists())

    def test_code_verification_allows_signup_without_reentering_data(self):
        response = self.verify_email_code()
        self.assertJSONEqual(response.content, {'status': 'success', 'message': 'Email verified.'})
        response = self.signup()
        self.assertRedirects(response, reverse('customer_login'))
        user = User.objects.get(username='newcustomer')
        profile = customer_signup.objects.get(user=user)
        self.assertTrue(user.is_active)
        self.assertTrue(profile.email_verified)
        self.assertEqual(profile.password, '')

    def test_duplicate_email_is_explained_and_does_not_create_another_account(self):
        self.verify_email_code()
        self.signup()
        self.verify_email_code()
        response = self.client.post(reverse('customer_signup'), {
            'username': 'othercustomer', 'email': 'customer@example.com',
            'contact': '9876543210', 'password': 'StrongPass123!',
        })
        self.assertContains(response, 'already exists for this email')
        self.assertEqual(User.objects.filter(email='customer@example.com').count(), 1)
