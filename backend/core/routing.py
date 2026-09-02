from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    path('ws/requests/', consumers.RequestConsumer.as_asgi()),
    path('ws/tracking/<int:id>/', consumers.RequestConsumer.as_asgi()),
    path('ws/chat/<int:request_id>/', consumers.ChatConsumer.as_asgi()),
]
