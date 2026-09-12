import json
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
    TechnicianWarning,
    TechnicianWalletTransaction,
    TechnicianWithdrawal,
    TechnicianIncentive,
    WalletTransaction,
)
from core.services.admin_assistant import process_admin_query
from core.services.admin_assistant.parser import parse_admin_query
from core.services.admin_assistant.entity_resolver import resolve_entities


class AdminAssistantTestCase(TestCase):
    def setUp(self):
        # 1. Super Admin
        self.admin = User.objects.create_superuser(
            username='admin_boss',
            email='boss@sevabandhu.com',
            password='AdminPassword123!'
        )

        # 2. Customers
        self.u_cust1 = User.objects.create_user(username='rahul_verma', email='rahul@gmail.com', password='pass')
        self.cust_rahul = customer_signup.objects.create(
            user=self.u_cust1,
            username='rahul_verma',
            email='rahul@gmail.com',
            contact='9876543201',
            wallet_balance=Decimal('250.00')
        )

        self.u_cust2 = User.objects.create_user(username='soham_sen', email='soham@gmail.com', password='pass')
        self.cust_soham = customer_signup.objects.create(
            user=self.u_cust2,
            username='soham_sen',
            email='soham@gmail.com',
            contact='9876543202',
            wallet_balance=Decimal('100.00')
        )

        # 3. Technicians
        self.u_tech1 = User.objects.create_user(username='ramu_plumber', email='ramu@technician.com', password='pass')
        self.tech_ramu = Technician_signup.objects.create(
            user=self.u_tech1,
            username='ramu_plumber',
            email='ramu@technician.com',
            contact='9876543203',
            service_category='Plumbing',
            is_available=True,
            wallet_balance=Decimal('1200.00')
        )

        self.u_tech2 = User.objects.create_user(username='vikram_ac', email='vikram@technician.com', password='pass')
        self.tech_vikram = Technician_signup.objects.create(
            user=self.u_tech2,
            username='vikram_ac',
            email='vikram@technician.com',
            contact='9876543204',
            service_category='AC Repair',
            is_available=True,
            wallet_balance=Decimal('600.00')
        )

        # 4. Services
        self.serv_ac = Service.objects.create(name='AC Repair', price=600, is_enabled=True)
        self.serv_plumb = Service.objects.create(name='Plumbing', price=400, is_enabled=True)

        # 5. Service Address & Details
        self.addr = ServiceAddress.objects.create(
            house_flat_no='202',
            street_area='Park Street',
            city='Kolkata',
            pincode='700016'
        )
        self.det_ac = ServiceDetail.objects.create(
            service_category='AC Repair',
            problem_description='AC cooling low',
            priority='Medium',
            preferred_service_date=timezone.now().date(),
            preferred_time_slot='Morning',
            contact_number='9876543201'
        )
        self.det_plumb = ServiceDetail.objects.create(
            service_category='Plumbing',
            problem_description='Pipe leak',
            priority='Low',
            preferred_service_date=timezone.now().date(),
            preferred_time_slot='Evening',
            contact_number='9876543202'
        )

        # 6. Service Requests & Transactions
        # Booking 1: Rahul booked Vikram for AC Repair (Completed, ₹600)
        self.req1 = ServiceRequest.objects.create(
            customer_username=self.cust_rahul.username,
            technician_username=self.tech_vikram.username,
            service_detail=self.det_ac,
            service_address=self.addr,
            status='Completed',
            payment_status='paid',
            amount=Decimal('600.00')
        )
        TechnicianWalletTransaction.objects.create(
            technician=self.tech_vikram,
            service_request=self.req1,
            amount=Decimal('450.00'),
            transaction_type='CREDIT',
            description='Payout for job'
        )

        # Booking 2: Soham booked Ramu for Plumbing (Completed, ₹400)
        self.req2 = ServiceRequest.objects.create(
            customer_username=self.cust_soham.username,
            technician_username=self.tech_ramu.username,
            service_detail=self.det_plumb,
            service_address=self.addr,
            status='Completed',
            payment_status='paid',
            amount=Decimal('400.00')
        )
        TechnicianWalletTransaction.objects.create(
            technician=self.tech_ramu,
            service_request=self.req2,
            amount=Decimal('300.00'),
            transaction_type='CREDIT',
            description='Payout for job'
        )

        # Booking 3: Rahul booked Ramu for Plumbing (Pending, ₹400)
        self.req3 = ServiceRequest.objects.create(
            customer_username=self.cust_rahul.username,
            technician_username=self.tech_ramu.username,
            service_detail=self.det_plumb,
            service_address=self.addr,
            status='Pending',
            payment_status='pending',
            amount=Decimal('400.00')
        )

        # Ratings & Withdrawals
        TechnicianRating.objects.create(
            customer=self.cust_rahul,
            technician=self.tech_vikram,
            service_request=self.req1,
            rating=5
        )
        TechnicianWithdrawal.objects.create(
            technician=self.tech_ramu,
            amount=Decimal('500.00'),
            status='COMPLETED'
        )

        self.client = Client(SERVER_NAME='127.0.0.1')

    # ==========================================
    # 1. SEMANTIC SEPARATION TESTS
    # ==========================================
    def test_customer_spending_vs_technician_earnings(self):
        """Verify customer spending and technician earnings are strictly separate."""
        # Rahul's spending: Completed job amount = ₹600.00 (NOT ₹450 or ₹1000)
        res_spend = process_admin_query("How much did rahul_verma spend?")
        self.assertEqual(res_spend['status'], 'ok')
        self.assertIn("₹600.00", res_spend['answer'])
        self.assertIn("spent", res_spend['answer'].lower())

        # Vikram's earnings: Payout received = ₹450.00 (NOT ₹600)
        res_earn = process_admin_query("How much did vikram_ac earn?")
        self.assertEqual(res_earn['status'], 'ok')
        self.assertIn("₹450.00", res_earn['answer'])
        self.assertIn("earnings", res_earn['answer'].lower())

    def test_wallet_balance_vs_earnings(self):
        """Verify wallet balance is separate from earnings."""
        # Ramu's wallet balance: ₹1200.00, Ramu's earnings: ₹300.00
        res_bal = process_admin_query("What is ramu_plumber wallet balance?")
        self.assertEqual(res_bal['status'], 'ok')
        self.assertIn("₹1,200.00", res_bal['answer'])

        res_earn = process_admin_query("How much did ramu_plumber earn?")
        self.assertEqual(res_earn['status'], 'ok')
        self.assertIn("₹300.00", res_earn['answer'])

    def test_withdrawals_metric(self):
        """Verify actual completed withdrawals are reported."""
        res_wd = process_admin_query("How much has ramu_plumber withdrawn?")
        self.assertEqual(res_wd['status'], 'ok')
        self.assertIn("₹500.00", res_wd['answer'])
        self.assertIn("withdrawn", res_wd['answer'].lower())

    # ==========================================
    # 2. SERVICE METRIC TESTS
    # ==========================================
    def test_service_price_and_rating(self):
        """Verify service price, rating, and status queries."""
        res_price = process_admin_query("AC Repair price")
        self.assertEqual(res_price['status'], 'ok')
        self.assertIn("₹600.00", res_price['answer'])

        res_status = process_admin_query("AC Repair status")
        self.assertEqual(res_status['status'], 'ok')
        self.assertIn("Active", res_status['answer'])

        res_rating = process_admin_query("AC Repair rating")
        self.assertEqual(res_rating['status'], 'ok')
        self.assertIn("★", res_rating['answer'])

    # ==========================================
    # 3. CROSS-RELATIONAL TESTS
    # ==========================================
    def test_cross_relational_queries(self):
        """Verify cross-relational questions link entities properly."""
        # Customer who booked Vikram the most -> rahul_verma
        res1 = process_admin_query("Which customer booked vikram_ac the most?")
        self.assertEqual(res1['status'], 'ok')
        self.assertIn("rahul_verma", res1['answer'])

        # Technician who served Soham the most -> ramu_plumber
        res2 = process_admin_query("Which technician served soham_sen the most?")
        self.assertEqual(res2['status'], 'ok')
        self.assertIn("ramu_plumber", res2['answer'])

        # Service Soham booked most often -> Plumbing
        res3 = process_admin_query("Which service did soham_sen book most often?")
        self.assertEqual(res3['status'], 'ok')
        self.assertIn("Plumbing", res3['answer'])

        # Technician who generated the most sales from AC Repair -> vikram_ac
        res4 = process_admin_query("Which technician generated the most sales from AC Repair?")
        self.assertEqual(res4['status'], 'ok')
        self.assertIn("vikram_ac", res4['answer'])

    # ==========================================
    # 4. RANKING & SUPERLATIVES
    # ==========================================
    def test_rankings(self):
        """Verify ranking queries."""
        # Who earned the most? -> vikram_ac (450) vs ramu_plumber (300)
        res_rank = process_admin_query("Who earned the most?")
        self.assertEqual(res_rank['status'], 'ok')
        self.assertIn("vikram_ac", res_rank['answer'])

        # Who completed the most jobs?
        res_jobs = process_admin_query("Which technician completed the most jobs?")
        self.assertEqual(res_jobs['status'], 'ok')
        self.assertIn("vikram_ac", res_jobs['answer'])

        # Which service was booked the most? -> Plumbing (2) vs AC Repair (1)
        res_serv = process_admin_query("Which service was booked the most?")
        self.assertEqual(res_serv['status'], 'ok')
        self.assertIn("Plumbing", res_serv['answer'])

    # ==========================================
    # 5. MULTI-METRIC & CONTEXT CONTINUATION
    # ==========================================
    def test_multi_metric_and_context(self):
        """Verify multi-metric queries and pronoun continuation."""
        res_multi = process_admin_query("Show me ramu_plumber income and bookings")
        self.assertEqual(res_multi['status'], 'ok')
        self.assertIn("Technician Total Earnings", res_multi['answer'])
        self.assertIn("Total Bookings", res_multi['answer'])

        # Follow-up with context: "How many jobs did he complete?"
        ctx = res_multi['context']
        res_followup = process_admin_query("How many jobs did he complete?", context=ctx)
        self.assertEqual(res_followup['status'], 'ok')
        self.assertIn("ramu_plumber", res_followup['answer'])
        self.assertIn("1", res_followup['answer'])

    # ==========================================
    # 6. DISAMBIGUATION TEST
    # ==========================================
    def test_disambiguation_same_name(self):
        """Verify ambiguity detection when a customer and technician share the same name."""
        # Create customer named 'arun' and technician named 'arun'
        u_c = User.objects.create_user(username='arun_c', email='arun@cust.com', password='pass')
        customer_signup.objects.create(user=u_c, username='arun', email='arun@cust.com', contact='9999999991')

        u_t = User.objects.create_user(username='arun_t', email='arun@tech.com', password='pass')
        Technician_signup.objects.create(user=u_t, username='arun', email='arun@tech.com', contact='9999999992')

        # Generic query without context
        res = process_admin_query("Tell me about arun")
        self.assertEqual(res['status'], 'clarification')
        self.assertIn("technician", res['answer'].lower())
        self.assertIn("customer", res['answer'].lower())

    # ==========================================
    # 7. OUT OF SCOPE & SECURITY TESTS
    # ==========================================
    def test_out_of_scope_guardrail(self):
        """Verify external knowledge queries are politely declined."""
        res = process_admin_query("Who is the president of India?")
        self.assertEqual(res['status'], 'unsupported')
        self.assertIn("only retrieve and analyze data", res['answer'])

    def test_api_security(self):
        """Verify API endpoint enforces superuser-only access."""
        # Anonymous user -> 302 Redirect
        r_anon = self.client.post(
            '/super-admin/assistant/query/',
            data=json.dumps({'query': 'AC Repair price'}),
            content_type='application/json',
            HTTP_HOST='127.0.0.1'
        )
        self.assertEqual(r_anon.status_code, 302)

        # Regular user -> 302 Redirect
        self.client.force_login(self.u_cust1)
        r_user = self.client.post(
            '/super-admin/assistant/query/',
            data=json.dumps({'query': 'AC Repair price'}),
            content_type='application/json',
            HTTP_HOST='127.0.0.1'
        )
        self.assertEqual(r_user.status_code, 302)

        # Superuser -> 200 OK with JSON answer
        self.client.force_login(self.admin)
        r_admin = self.client.post(
            '/super-admin/assistant/query/',
            data=json.dumps({'query': 'AC Repair price'}),
            content_type='application/json',
            HTTP_HOST='127.0.0.1'
        )
        self.assertEqual(r_admin.status_code, 200)
        data = r_admin.json()
        self.assertEqual(data['status'], 'ok')
        self.assertIn("₹600.00", data['answer'])

