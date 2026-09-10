import json
from django.utils import timezone
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class RequestConsumer(AsyncJsonWebsocketConsumer):

    @database_sync_to_async
    def save_live_location(self, request_id, latitude, longitude):
        from core.models import ServiceRequest
        ServiceRequest.objects.filter(id=request_id).update(
            technician_latitude=latitude,
            technician_longitude=longitude,
            technician_location_updated_at=timezone.now(),
        )

    #########################################################
    # CONNECT
    #########################################################

    async def connect(self):

        print("[ICON] SOCKET CONNECTED")

        #################################################
        # TECHNICIAN GROUP
        #################################################

        self.group_name = 'technicians'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        #################################################
        # REQUEST-SPECIFIC TRACKING GROUP
        #################################################

        self.request_id = self.scope['url_route']['kwargs'].get('id')

        if self.request_id:

            self.tracking_group_name = f"tracking_{self.request_id}"

            await self.channel_layer.group_add(
                self.tracking_group_name,
                self.channel_name
            )

        #################################################
        # ACCEPT SOCKET
        #################################################

        await self.accept()

        #################################################
        # SEND CONNECT MESSAGE
        #################################################

        await self.send(text_data=json.dumps({
            'message': 'Connected'
        }))

    #########################################################
    # DISCONNECT
    #########################################################

    async def disconnect(self, close_code):

        print("[ICON] SOCKET DISCONNECTED")

        #################################################
        # REMOVE TECHNICIAN GROUP
        #################################################

        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        #################################################
        # REMOVE TRACKING GROUP
        #################################################

        if hasattr(self, 'tracking_group_name'):

            await self.channel_layer.group_discard(
                self.tracking_group_name,
                self.channel_name
            )

    

    #########################################################
    # NEW REQUEST NOTIFICATION
    #########################################################

    async def new_request(self, event):

        print("[FIRE] CONSUMER RECEIVED EVENT")

        await self.send(text_data=json.dumps(
            event['content']
        ))

    #########################################################
    # REMOVE NOTIFICATION
    #########################################################

    async def notification_removed(self, event):

        print("[FIRE] notification_removed HIT")

        await self.send(text_data=json.dumps({
            'type': 'notification_removed',
            'request_id': event['request_id']
        }))

    #########################################################
    # TECHNICIAN MESSAGE
    #########################################################

    async def technicians_message(self, event):

        await self.send_json(event['content'])

    #########################################################
    # RECEIVE LIVE GPS
    #########################################################

    async def receive(self, text_data=None, bytes_data=None):

        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except (TypeError, json.JSONDecodeError):
            return

        print("[ICON] RECEIVED:", data)

        #################################################
        # LIVE LOCATION TRACKING
        ##################################
        if data.get('type') == 'live_location':

            try:
                latitude = float(data.get('latitude'))
                longitude = float(data.get('longitude'))
            except (TypeError, ValueError):
                return
            request_id = data.get('request_id')

            print(
                "[ICON] LIVE GPS:",
                latitude,
                longitude,
                "REQUEST:",
                request_id
            )

            #################################################
            # SEND TO REQUEST-SPECIFIC TRACKING GROUP
            #################################################

            if request_id:

                await self.save_live_location(request_id, latitude, longitude)

                await self.channel_layer.group_send(

                    f"tracking_{request_id}",

                    {
                        'type': 'location_update',

                        'latitude': latitude,
                        'longitude': longitude,
                    }
                )

    #########################################################
    # SEND LIVE LOCATION TO CUSTOMER
    #########################################################

    async def location_update(self, event):

        await self.send(text_data=json.dumps({

            'type': 'location_update',

            'latitude': event['latitude'],
            'longitude': event['longitude'],

        }))

class ChatConsumer(AsyncWebsocketConsumer):

    @database_sync_to_async
    def get_service_request(self, request_id):
        from core.models import ServiceRequest
        try:
            return ServiceRequest.objects.get(id=request_id)
        except ServiceRequest.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, conversation, user, text):
        from core.models import ChatMessage
        return ChatMessage.objects.create(
            conversation=conversation,
            sender=user,
            message=text
        )

    @database_sync_to_async
    def get_or_create_conversation(self, service_request):
        from core.models import ChatConversation
        conversation, created = ChatConversation.objects.get_or_create(
            service_request=service_request
        )
        return conversation

    async def connect(self):
        try:
            self.user = self.scope.get("user")

            if not self.user or self.user.is_anonymous:
                await self.close(code=4401)
                return

            self.request_id = self.scope.get('url_route', {}).get('kwargs', {}).get('request_id')
            if not self.request_id:
                await self.close(code=4400)
                return

            self.service_request = await self.get_service_request(self.request_id)
            if not self.service_request:
                await self.close(code=4404)
                return

            # Only the customer and the assigned technician may join this chat.
            if self.user.username not in {
                self.service_request.customer_username,
                self.service_request.technician_username,
            }:
                await self.close(code=4403)
                return

            self.room_group_name = f'chat_{self.request_id}'

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        except Exception as e:
            # Do not leave the browser in CONNECTING when a server-side setup
            # failure occurs.  The close code is surfaced by the page UI.
            print(f"[CHAT ERROR] connect failed: {e}")
            await self.close(code=1011)

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if text_data:
                text_data_json = json.loads(text_data)
                message = text_data_json.get('message')

                if not message:
                    return

                # Ensure conversation exists
                conversation = await self.get_or_create_conversation(self.service_request)
                
                # Save message
                saved_msg = await self.save_message(conversation, self.user, message)
                
                created_at_str = saved_msg.created_at.strftime("%b %d, %I:%M %p") if hasattr(saved_msg, 'created_at') else "Just now"

                # Broadcast
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'sender': self.user.username,
                        'created_at': created_at_str
                    }
                )
        except Exception as e:
            print(f"[CHAT ERROR] receive failed: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to process message: ' + str(e)
            }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'created_at': event.get('created_at', '')
        }))


class TechnicianSupportConsumer(AsyncWebsocketConsumer):
    """
    Dedicated WebSocket consumer for Technician <-> Admin live support chat.
    Completely isolated from customer <-> technician chat.
    Enforces authentication, ticket ownership or admin authorization, and safe message broadcasting.
    """

    @database_sync_to_async
    def get_ticket(self, ticket_id):
        from core.models import TechnicianSupportTicket
        try:
            return TechnicianSupportTicket.objects.select_related('technician', 'technician__user').get(id=ticket_id)
        except TechnicianSupportTicket.DoesNotExist:
            return None

    @database_sync_to_async
    def check_authorization(self, ticket, user):
        is_admin = bool(user.is_staff or user.is_superuser)
        is_owner = False
        if ticket.technician:
            if ticket.technician.user_id == user.id:
                is_owner = True
            elif ticket.technician.username.strip().lower() == user.username.strip().lower():
                is_owner = True
        return is_admin, is_owner

    @database_sync_to_async
    def save_message(self, ticket_id, user, role, message_text):
        from core.models import TechnicianSupportTicket, TechnicianSupportMessage
        ticket = TechnicianSupportTicket.objects.get(id=ticket_id)
        
        old_status = ticket.status
        # If admin replies and ticket was OPEN, transition to IN_PROGRESS
        if role == 'ADMIN' and ticket.status == 'OPEN':
            ticket.status = 'IN_PROGRESS'
            ticket.assigned_admin = user
            ticket.save(update_fields=['status', 'assigned_admin'])
            
        msg = TechnicianSupportMessage.objects.create(
            ticket=ticket,
            sender=user,
            sender_role=role,
            message=message_text
        )
        return msg, old_status, ticket.status

    @database_sync_to_async
    def mark_incoming_as_read(self, ticket_id, current_role):
        from core.models import TechnicianSupportMessage
        from django.utils import timezone
        opposite_role = 'ADMIN' if current_role == 'TECHNICIAN' else 'TECHNICIAN'
        TechnicianSupportMessage.objects.filter(
            ticket_id=ticket_id,
            sender_role=opposite_role,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())

    async def connect(self):
        try:
            self.user = self.scope.get("user")
            if not self.user or self.user.is_anonymous:
                print(f"[TECH SUPPORT WS] Connect rejected: Anonymous or unauthenticated session.")
                await self.close(code=4401)
                return

            self.ticket_id = self.scope.get('url_route', {}).get('kwargs', {}).get('ticket_id')
            if not self.ticket_id:
                print(f"[TECH SUPPORT WS] Connect rejected: Missing ticket_id.")
                await self.close(code=4400)
                return

            self.ticket = await self.get_ticket(self.ticket_id)
            if not self.ticket:
                print(f"[TECH SUPPORT WS] Connect rejected: Ticket #{self.ticket_id} does not exist.")
                await self.close(code=4404)
                return

            is_admin, is_owner = await self.check_authorization(self.ticket, self.user)
            if not (is_admin or is_owner):
                print(f"[TECH SUPPORT WS] Connect rejected: User '{self.user.username}' is neither Admin nor Owner of ticket #{self.ticket_id}.")
                await self.close(code=4403)
                return

            self.sender_role = 'ADMIN' if is_admin else 'TECHNICIAN'
            self.room_group_name = f'technician_support_{self.ticket_id}'

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            print(f"[TECH SUPPORT WS] [OK] CONNECTED: '{self.user.username}' ({self.sender_role}) joined room '{self.room_group_name}'.")

            # Mark any unread messages from the other party as read
            await self.mark_incoming_as_read(self.ticket_id, self.sender_role)

        except Exception as e:
            print(f"[TECH SUPPORT WS ERROR] connect failed: {e}")
            await self.close(code=1011)

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        u = getattr(self, 'user', 'Anonymous')
        r = getattr(self, 'sender_role', 'UNKNOWN')
        print(f"[TECH SUPPORT WS] [DISCONNECT] User '{u}' ({r}) disconnected with code={close_code}.")

    async def receive(self, text_data=None, bytes_data=None):
        try:
            if not text_data:
                return

            data = json.loads(text_data)
            action = data.get('action')

            if action == 'mark_read':
                await self.mark_incoming_as_read(self.ticket_id, self.sender_role)
                return

            message = data.get('message', '').strip()
            if not message:
                return

            saved_msg, old_status, new_status = await self.save_message(self.ticket_id, self.user, self.sender_role, message)
            created_at_str = saved_msg.created_at.strftime("%b %d, %I:%M %p")

            # If status transitioned from OPEN to IN_PROGRESS because admin replied, notify group
            if self.sender_role == 'ADMIN' and old_status == 'OPEN' and new_status == 'IN_PROGRESS':
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'ticket_status_updated',
                        'new_status': 'IN_PROGRESS',
                        'status_display': 'In Progress',
                        'message': f"Admin {self.user.username} joined the chat. Ticket marked In Progress."
                    }
                )

            # Broadcast to support ticket room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'support_chat_message',
                    'message': message,
                    'sender_username': self.user.username,
                    'sender_role': self.sender_role,
                    'created_at': created_at_str,
                    'message_id': saved_msg.id
                }
            )

        except Exception as e:
            print(f"[TECH SUPPORT CHAT ERROR] receive failed: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to process message: ' + str(e)
            }))

    async def support_chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'support_chat_message',
            'message': event['message'],
            'sender_username': event['sender_username'],
            'sender_role': event['sender_role'],
            'created_at': event.get('created_at', ''),
            'message_id': event.get('message_id')
        }))

    async def ticket_status_updated(self, event):
        """Notification when admin changes ticket status."""
        await self.send(text_data=json.dumps({
            'type': 'ticket_status_updated',
            'new_status': event['new_status'],
            'status_display': event['status_display'],
            'message': event.get('message', '')
        }))

