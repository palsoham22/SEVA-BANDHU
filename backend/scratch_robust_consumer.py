import os

consumers_path = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\backend\core\consumers.py'
with open(consumers_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure AsyncWebsocketConsumer is imported
if "AsyncWebsocketConsumer" not in content:
    content = content.replace(
        "from channels.generic.websocket import AsyncJsonWebsocketConsumer", 
        "from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer"
    )

target_class = "class ChatConsumer(AsyncJsonWebsocketConsumer):"
replacement_class = "class ChatConsumer(AsyncWebsocketConsumer):"
content = content.replace(target_class, replacement_class)

target_receive = """    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message')

        if not message:
            return

        # Re-verify status
        self.service_request = await self.get_service_request(self.request_id)
        # Allow chatting even on completed requests for testing purposes

        conversation = await self.get_or_create_conversation(self.service_request)
        saved_msg = await self.save_message(conversation, self.user, message)

        # Broadcast
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender': self.user.username,
                'created_at': saved_msg.created_at.strftime("%b %d, %I:%M %p")
            }
        )"""

replacement_receive = """    async def receive(self, text_data=None, bytes_data=None):
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
            }))"""

if target_receive in content:
    content = content.replace(target_receive, replacement_receive)
else:
    # try with normalized line endings
    content = content.replace('\r\n', '\n').replace(target_receive.replace('\r\n', '\n'), replacement_receive.replace('\r\n', '\n'))

with open(consumers_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print("Rewrote ChatConsumer")
