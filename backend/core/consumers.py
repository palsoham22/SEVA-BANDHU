import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class RequestConsumer(AsyncJsonWebsocketConsumer):

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

        data = json.loads(text_data)

        print("[ICON] RECEIVED:", data)

        #################################################
        # LIVE LOCATION TRACKING
        ##################################
        if data.get('type') == 'live_location':

            latitude = data.get('latitude')
            longitude = data.get('longitude')
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
