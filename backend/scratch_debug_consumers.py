import os

consumers_path = r'c:\Users\palso\OneDrive\Desktop\SevaBandhu\backend\core\consumers.py'
with open(consumers_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    async def connect(self):
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

        # Access control
        is_customer = self.service_request.customer_username == self.user.username
        is_technician = self.service_request.technician_username == self.user.username

        if not (is_customer or is_technician):
            await self.close()
            return

        # Check status (allow if Assigned, In Progress, or Completed for history)
        if self.service_request.status == 'Pending':
            await self.close()
            return

        self.room_group_name = f'chat_{self.request_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()"""

replacement = """    async def connect(self):
        with open('ws_debug.log', 'a') as f:
            f.write(f"\\n--- CONNECT ATTEMPT ---\\n")
        
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            with open('ws_debug.log', 'a') as f: f.write("Rejected: Anonymous user\\n")
            await self.close()
            return

        self.request_id = self.scope['url_route']['kwargs'].get('request_id')
        if not self.request_id:
            with open('ws_debug.log', 'a') as f: f.write("Rejected: No request_id\\n")
            await self.close()
            return

        self.service_request = await self.get_service_request(self.request_id)
        if not self.service_request:
            with open('ws_debug.log', 'a') as f: f.write("Rejected: ServiceRequest not found\\n")
            await self.close()
            return

        # Access control
        is_customer = self.service_request.customer_username == self.user.username
        is_technician = self.service_request.technician_username == self.user.username

        with open('ws_debug.log', 'a') as f: 
            f.write(f"Customer username on req: {self.service_request.customer_username}, Tech username on req: {self.service_request.technician_username}, User trying to connect: {self.user.username}\\n")

        if not (is_customer or is_technician):
            with open('ws_debug.log', 'a') as f: f.write("Rejected: Access control failed\\n")
            await self.close()
            return

        if self.service_request.status == 'Pending':
            with open('ws_debug.log', 'a') as f: f.write("Rejected: Pending status\\n")
            await self.close()
            return

        self.room_group_name = f'chat_{self.request_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        with open('ws_debug.log', 'a') as f: f.write("Accepted connection!\\n")"""

content = content.replace(target.replace('\r\n', '\n'), replacement.replace('\r\n', '\n'))
with open(consumers_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print("Added debug logs")
