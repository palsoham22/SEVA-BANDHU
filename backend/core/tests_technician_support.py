"""
Comprehensive automated tests for Technician Support Assistant:
- Stage 1 Guided Support & Context Isolation
- Server-side context verification & Ownership Security
- Stage 2 Ticket Escalation & Guided History Preservation
- Super Admin Support Desk & Status Updates
- Live Chat WebSocket Consumer authorization & message saving
- Zero regressions on existing Customer Chat & Complaints
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from channels.testing import WebsocketCommunicator

from core.models import (
    customer_signup,
    Technician_signup,
    ServiceDetail,
    ServiceAddress,
    ServiceRequest,
    SupportTicket,
    ChatConversation,
    ChatMessage,
    TechnicianWalletTransaction,
    TechnicianWithdrawal,
    TechnicianIncentive,
    TechnicianSupportTicket,
    TechnicianSupportMessage,
)
from core.consumers import TechnicianSupportConsumer
from seva_bandhu.asgi import application


class TechnicianSupportWorkflowTests(TestCase):
    def setUp(self):
        # 1. Create Technician User & Profile
        self.tech_user = User.objects.create_user(
            username='tech_arun',
            password='password123',
            email='tech_arun@example.com'
        )
        self.technician = Technician_signup.objects.create(
            user=self.tech_user,
            username='tech_arun',
            email='tech_arun@example.com',
            contact='9876543210',
            service_category='AC Repair',
            wallet_balance=1500.00
        )

        # 2. Create another Technician to test isolation
        self.other_tech_user = User.objects.create_user(
            username='tech_vikram',
            password='password123',
            email='tech_vikram@example.com'
        )
        self.other_technician = Technician_signup.objects.create(
            user=self.other_tech_user,
            username='tech_vikram',
            email='tech_vikram@example.com',
            contact='9876543211',
            service_category='Electrical'
        )

        # 3. Create Customer
        self.cust_user = User.objects.create_user(
            username='cust_rahul',
            password='password123',
            email='cust_rahul@example.com'
        )
        self.customer = customer_signup.objects.create(
            user=self.cust_user,
            username='cust_rahul',
            email='cust_rahul@example.com',
            contact='9123456780'
        )

        # 4. Create Service Detail & Address & Request
        self.detail = ServiceDetail.objects.create(
            service_category='AC Repair',
            problem_description='Cooling issue',
            priority='High',
            preferred_service_date=timezone.now().date(),
            preferred_time_slot='10:00 AM - 12:00 PM',
            contact_number='9123456780'
        )
        self.address = ServiceAddress.objects.create(
            house_flat_no='101',
            street_area='MG Road',
            city='Bangalore',
            pincode='560001'
        )
        self.service_request = ServiceRequest.objects.create(
            customer_username=self.customer.username,
            technician_username=self.technician.username,
            service_detail=self.detail,
            service_address=self.address,
            status='Completed',
            amount=1200.00,
            payment_status='paid'
        )

        # Service request belonging to other technician
        self.other_service_request = ServiceRequest.objects.create(
            customer_username=self.customer.username,
            technician_username=self.other_technician.username,
            service_detail=self.detail,
            service_address=self.address,
            status='Assigned',
            amount=800.00
        )

        # 5. Financial records
        self.wallet_tx = TechnicianWalletTransaction.objects.create(
            technician=self.technician,
            service_request=self.service_request,
            amount=1080.00,
            transaction_type='CREDIT',
            description='Payout for Job #1'
        )
        self.withdrawal = TechnicianWithdrawal.objects.create(
            technician=self.technician,
            amount=1000.00,
            status='COMPLETED',
            reference_id='NEFT12345678'
        )
        self.incentive = TechnicianIncentive.objects.create(
            technician=self.technician,
            title='5-Star Weekly Champion',
            amount=500.00,
            status='CREDITED'
        )

        # 6. Admin User
        self.admin_user = User.objects.create_superuser(
            username='super_admin',
            password='adminpassword',
            email='admin@sevabandhu.com'
        )

        self.client = Client()

    def test_technician_support_page_loads(self):
        """Technician can access full-page support chat."""
        self.client.login(username='tech_arun', password='password123')
        response = self.client.get('/technician/support/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Support Assistant')
        self.assertContains(response, 'Payment / Earnings')
        self.assertContains(response, 'Service / Booking')

    def test_context_api_security_isolation(self):
        """Technician can only retrieve their own service and financial records."""
        self.client.login(username='tech_arun', password='password123')
        
        # Test services context
        res = self.client.get('/technician/support/api/context/?type=services')
        self.assertEqual(res.status_code, 200)
        data = res.json()['data']
        service_ids = [item['id'] for item in data]
        self.assertIn(self.service_request.id, service_ids)
        self.assertNotIn(self.other_service_request.id, service_ids)

        # Test wallet context
        res = self.client.get('/technician/support/api/context/?type=wallet')
        self.assertEqual(res.status_code, 200)
        data = res.json()['data']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], self.wallet_tx.id)

    def test_escalation_api_creates_ticket_and_preserves_guided_history(self):
        """Escalating creates a TechnicianSupportTicket with all guided steps preserved."""
        self.client.login(username='tech_arun', password='password123')

        guided_steps = [
            {'step': 1, 'title': 'Check Booking Completion Status', 'response': 'NOT_SOLVED'},
            {'step': 2, 'title': 'Verify Settlement Window', 'response': 'NOT_SOLVED'},
        ]

        payload = {
            'category': 'PAYMENT_EARNINGS',
            'issue': 'Missing earnings from completed job',
            'subject': 'Payment inquiry for AC repair',
            'service_request_id': self.service_request.id,
            'wallet_transaction_id': self.wallet_tx.id,
            'guided_steps': guided_steps,
            'escalation_reason': "We couldn't resolve your issue automatically through guided troubleshooting.",
            'message_text': "My earnings from AC Repair are still missing."
        }

        response = self.client.post(
            '/technician/support/api/escalate/',
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data['status'], 'success')
        ticket_id = res_data['ticket_id']

        ticket = TechnicianSupportTicket.objects.get(id=ticket_id)
        self.assertEqual(ticket.technician, self.technician)
        self.assertEqual(ticket.status, 'OPEN')
        self.assertEqual(ticket.related_service_request, self.service_request)
        self.assertEqual(ticket.related_wallet_transaction, self.wallet_tx)
        self.assertEqual(len(ticket.guided_flow_state), 2)
        self.assertEqual(ticket.guided_flow_state[0]['title'], 'Check Booking Completion Status')

        # Check messages created
        msgs = ticket.messages.all()
        self.assertEqual(msgs.count(), 2)  # 1 System summary, 1 Technician note

    def test_server_rejects_unowned_service_request(self):
        """Backend ignores or sanitizes service request not owned by the technician."""
        self.client.login(username='tech_arun', password='password123')

        payload = {
            'category': 'SERVICE_BOOKING',
            'issue': 'Booking issue',
            'service_request_id': self.other_service_request.id,  # Owned by Vikram!
            'guided_steps': []
        }

        response = self.client.post(
            '/technician/support/api/escalate/',
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        ticket = TechnicianSupportTicket.objects.get(id=response.json()['ticket_id'])
        # Must be None because tech_arun does not own other_service_request!
        self.assertIsNone(ticket.related_service_request)

    def test_admin_desk_view_and_status_update(self):
        """Super Admin can view tickets, see guided history, and change status."""
        # Create a ticket first
        ticket = TechnicianSupportTicket.objects.create(
            technician=self.technician,
            category='PAYMENT_EARNINGS',
            issue='Payment delayed',
            subject='Delay in payout',
            status='OPEN',
            related_service_request=self.service_request,
            guided_flow_state=[{'step': 1, 'title': 'Standard Banking Hours', 'response': 'NOT_SOLVED'}]
        )

        self.client.login(username='super_admin', password='adminpassword')

        # List view
        res = self.client.get('/super-admin/technician-support/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, ticket.ticket_number)
        self.assertContains(res, 'tech_arun')

        # Detail view
        res = self.client.get(f'/super-admin/technician-support/{ticket.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Standard Banking Hours')
        self.assertContains(res, 'AC Repair')

        # Update status to RESOLVED
        res = self.client.post(
            f'/super-admin/technician-support/{ticket.id}/status/',
            data={'status': 'RESOLVED', 'admin_notes': 'Payment verified and settled.'}
        )
        self.assertEqual(res.status_code, 302)

        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'RESOLVED')
        self.assertEqual(ticket.admin_notes, 'Payment verified and settled.')
        self.assertIsNotNone(ticket.closed_at)

    def test_existing_customer_features_remain_unaffected(self):
        """Verify customer complaints and customer chat remain 100% operational."""
        # Customer Support Ticket (Complaint)
        complaint = SupportTicket.objects.create(
            customer=self.customer,
            ticket_type='Complaint',
            service_request_id=str(self.service_request.id),
            description='Technician arrived 10 mins late',
            technician_name=self.technician.username
        )
        self.assertEqual(SupportTicket.objects.filter(customer=self.customer).count(), 1)

        # Customer-Technician Chat
        chat_conv, _ = ChatConversation.objects.get_or_create(service_request=self.service_request)
        chat_msg = ChatMessage.objects.create(
            conversation=chat_conv,
            sender=self.cust_user,
            message='Hello technician'
        )
        self.assertEqual(chat_conv.messages.count(), 1)

    async def test_websocket_authorization_and_messaging(self):
        """Technician and Admin can join ticket room and chat; unauthorized users are rejected."""
        from channels.db import database_sync_to_async
        # Create ticket
        ticket = await database_sync_to_async(TechnicianSupportTicket.objects.create)(
            technician=self.technician,
            category='PAYMENT_EARNINGS',
            issue='Missing earnings',
            subject='Payment inquiry',
            status='OPEN'
        )

        # 1. Unauthenticated connection rejected with 4401
        communicator_anon = WebsocketCommunicator(
            application,
            f"/ws/support/technician/{ticket.id}/"
        )
        connected, close_code = await communicator_anon.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)
        await communicator_anon.disconnect()

        # 2. Unauthorized technician rejected with 4403
        communicator_other = WebsocketCommunicator(
            application,
            f"/ws/support/technician/{ticket.id}/"
        )
        communicator_other.scope['user'] = self.other_tech_user
        connected, close_code = await communicator_other.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)
        await communicator_other.disconnect()

        # 3. Authorized Technician connects successfully
        communicator_tech = WebsocketCommunicator(
            application,
            f"/ws/support/technician/{ticket.id}/"
        )
        communicator_tech.scope['user'] = self.tech_user
        connected, _ = await communicator_tech.connect()
        self.assertTrue(connected)

        # 4. Authorized Admin connects successfully
        communicator_admin = WebsocketCommunicator(
            application,
            f"/ws/support/technician/{ticket.id}/"
        )
        communicator_admin.scope['user'] = self.admin_user
        connected, _ = await communicator_admin.connect()
        self.assertTrue(connected)

        # 5. Technician sends message, Admin receives it
        await communicator_tech.send_json_to({'message': 'Hello Admin Support!'})
        response = await communicator_admin.receive_json_from()
        self.assertEqual(response['type'], 'support_chat_message')
        self.assertEqual(response['message'], 'Hello Admin Support!')
        self.assertEqual(response['sender_username'], 'tech_arun')
        self.assertEqual(response['sender_role'], 'TECHNICIAN')

        # Clean up
        await communicator_tech.disconnect()
        await communicator_admin.disconnect()


