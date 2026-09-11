import datetime
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone

from core.models import (
    customer_signup,
    Technician_signup,
    Service,
    ServiceDetail,
    ServiceAddress,
    ServiceRequest,
    SupportTicket,
    TechnicianRating,
    TechnicianWalletTransaction,
    TechnicianWithdrawal,
    TechnicianIncentive,
    WalletTransaction,
    ReferralLog,
    Offer,
    CustomerOffer,
)
from core.services.admin_income_analytics_service import (
    resolve_date_range,
    get_comparison_range,
    compute_delta,
    get_kpi_summary,
    get_financial_ledger_breakdown,
    get_full_income_analytics_context,
)


class IncomeAnalyticsServiceTestCase(TestCase):
    def setUp(self):
        # Create Super Admin
        self.admin_user = User.objects.create_superuser(
            username='analytics_admin',
            email='admin@sevabandhu.com',
            password='Password123!'
        )

        # Create Regular User & Customer
        self.cust_user = User.objects.create_user(
            username='cust_test',
            email='cust@test.com',
            password='Password123!'
        )
        self.customer = customer_signup.objects.create(
            user=self.cust_user,
            username='cust_test',
            email='cust@test.com',
            contact='9876543210',
            password='Password123!',
            wallet_balance=Decimal('150.00')
        )

        # Create Technician
        self.tech_user = User.objects.create_user(
            username='tech_pro',
            email='tech@test.com',
            password='Password123!'
        )
        self.technician = Technician_signup.objects.create(
            user=self.tech_user,
            username='tech_pro',
            email='tech@test.com',
            contact='9876543211',
            password='Password123!',
            service_category='Plumbing',
            is_available=True,
            wallet_balance=Decimal('800.00')
        )

        # Create Service Catalog Item
        self.service = Service.objects.create(
            name='Plumbing',
            price=500,
            is_enabled=True
        )

        # Address & Detail
        self.address = ServiceAddress.objects.create(
            house_flat_no='101',
            street_area='Main Street',
            city='Mumbai',
            pincode='400001'
        )
        self.detail = ServiceDetail.objects.create(
            service_category='Plumbing',
            problem_description='Pipe leaking',
            priority='Medium',
            preferred_service_date=timezone.now().date(),
            preferred_time_slot='Morning',
            contact_number='9876543210'
        )

        # Test Client
        self.client = Client(SERVER_NAME='127.0.0.1')

    def test_resolve_date_range_presets(self):
        presets = ['today', 'yesterday', 'last_7_days', 'last_30_days', 'this_month', 'previous_month', 'this_year', 'all_time']
        for p in presets:
            s, e, key, label = resolve_date_range(p)
            self.assertEqual(key, p)
            self.assertIsNotNone(label)
            if s and e:
                self.assertLessEqual(s, e)

    def test_resolve_custom_date_range(self):
        # Valid custom
        s, e, key, label = resolve_date_range('custom', '2026-09-01', '2026-09-10')
        self.assertEqual(key, 'custom')
        self.assertEqual(s.date(), datetime.date(2026, 9, 1))
        self.assertEqual(e.date(), datetime.date(2026, 9, 10))

        # Inverted custom dates (end < start) should auto-swap safely
        s_rev, e_rev, key_rev, label_rev = resolve_date_range('custom', '2026-09-10', '2026-09-01')
        self.assertEqual(s_rev.date(), datetime.date(2026, 9, 1))
        self.assertEqual(e_rev.date(), datetime.date(2026, 9, 10))

    def test_compute_delta(self):
        # Normal positive
        d = compute_delta(150, 100)
        self.assertEqual(d['direction'], 'up')
        self.assertEqual(d['value'], 50.0)

        # Normal negative
        d_neg = compute_delta(50, 100)
        self.assertEqual(d_neg['direction'], 'down')
        self.assertEqual(d_neg['value'], 50.0)

        # Zero previous
        d_zero = compute_delta(100, 0)
        self.assertEqual(d_zero['direction'], 'up')
        self.assertEqual(d_zero['value'], 100.0)

        # Both zero
        d_neutral = compute_delta(0, 0)
        self.assertEqual(d_neutral['direction'], 'neutral')

    def test_kpi_summary_with_bookings(self):
        # Booking 1: Completed ₹500
        req1 = ServiceRequest.objects.create(
            customer_username=self.customer.username,
            technician_username=self.technician.username,
            service_detail=self.detail,
            service_address=self.address,
            status='Completed',
            payment_status='paid',
            amount=Decimal('500.00')
        )
        # Technician payout for req1: ₹400
        TechnicianWalletTransaction.objects.create(
            technician=self.technician,
            service_request=req1,
            amount=Decimal('400.00'),
            transaction_type='CREDIT',
            description='Job Payment'
        )

        # Booking 2: Pending ₹600
        req2 = ServiceRequest.objects.create(
            customer_username=self.customer.username,
            technician_username=None,
            service_detail=self.detail,
            service_address=self.address,
            status='Pending',
            payment_status='pending',
            amount=Decimal('600.00')
        )

        s, e, _, _ = resolve_date_range('all_time')
        kpi = get_kpi_summary(s, e)

        # Gross Sales = 500 + 600 = 1100
        self.assertEqual(kpi['gross_sales'], Decimal('1100.00'))
        # Realized Sales = 500 (completed only)
        self.assertEqual(kpi['realized_sales'], Decimal('500.00'))
        # Technician Payouts = 400
        self.assertEqual(kpi['technician_payouts'], Decimal('400.00'))
        # Platform Income = 500 - 400 = 100
        self.assertEqual(kpi['platform_income'], Decimal('100.00'))
        # Bookings count
        self.assertEqual(kpi['total_bookings'], 2)
        self.assertEqual(kpi['completed_bookings'], 1)
        self.assertEqual(kpi['active_bookings'], 1)
        self.assertEqual(kpi['completion_rate'], 50.0)

    def test_zero_division_safety_on_empty_db(self):
        # Clear requests
        ServiceRequest.objects.all().delete()
        s, e, _, _ = resolve_date_range('all_time')
        kpi = get_kpi_summary(s, e)

        self.assertEqual(kpi['total_bookings'], 0)
        self.assertEqual(kpi['completed_bookings'], 0)
        self.assertEqual(kpi['completion_rate'], 0.0)
        self.assertEqual(kpi['gross_sales'], Decimal('0.00'))
        self.assertEqual(kpi['platform_income'], Decimal('0.00'))

    def test_superuser_security_access(self):
        # Anonymous user must be redirected
        resp_anon = self.client.get('/super-admin/income-analytics/', HTTP_HOST='127.0.0.1')
        self.assertEqual(resp_anon.status_code, 302)
        self.assertIn('/admin-login/', resp_anon.url)

        # Non-superuser must be redirected
        self.client.force_login(self.cust_user)
        resp_cust = self.client.get('/super-admin/income-analytics/', HTTP_HOST='127.0.0.1')
        self.assertEqual(resp_cust.status_code, 302)
        self.assertIn('/admin-login/', resp_cust.url)

        # Superuser must get 200 OK
        self.client.force_login(self.admin_user)
        resp_admin = self.client.get('/super-admin/income-analytics/', HTTP_HOST='127.0.0.1')
        self.assertEqual(resp_admin.status_code, 200)
        self.assertContains(resp_admin, 'Income &amp; Business Analytics')
        self.assertContains(resp_admin, 'Total Gross Sales (GMV)')

