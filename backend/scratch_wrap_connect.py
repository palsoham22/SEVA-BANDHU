import os

consumers_path = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\backend\core\consumers.py'
with open(consumers_path, 'r', encoding='utf-8') as f:
    content = f.read()

target_connect = """    async def connect(self):
        
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close()
            return

        self.request_id = self.scope['url_route']['kwargs'].get('request_id')
        if not self.request_id:
            await self.close()
            return

        self.service_request = await self.get_service_request(self.request_id)
        if not self.service_request:
            await self.close()
            return

        # Bypassing access control for debugging

        self.room_group_name = f'chat_{self.request_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()"""

replacement_connect = """    async def connect(self):
        try:
            await self.accept()
            
            self.user = self.scope.get("user")
            
            if not self.user or self.user.is_anonymous:
                await self.send(text_data=json.dumps({'type': 'error', 'message': 'User not authenticated'}))
                await self.close()
                return

            self.request_id = self.scope.get('url_route', {}).get('kwargs', {}).get('request_id')
            if not self.request_id:
                await self.send(text_data=json.dumps({'type': 'error', 'message': 'No request_id'}))
                await self.close()
                return

            self.service_request = await self.get_service_request(self.request_id)
            if not self.service_request:
                await self.send(text_data=json.dumps({'type': 'error', 'message': 'ServiceRequest not found'}))
                await self.close()
                return

            self.room_group_name = f'chat_{self.request_id}'

            if not self.channel_layer:
                await self.send(text_data=json.dumps({'type': 'error', 'message': 'No channel_layer'}))
                await self.close()
                return

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            try:
                await self.send(text_data=json.dumps({'type': 'error', 'message': f'Connect crashed: {err}'}))
            except:
                pass
            await self.close()"""

if target_connect in content:
    content = content.replace(target_connect, replacement_connect)
else:
    # try with normalized line endings
    content = content.replace('\r\n', '\n').replace(target_connect.replace('\r\n', '\n'), replacement_connect.replace('\r\n', '\n'))

with open(consumers_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print("Wrapped connect in try-except")
