from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [

    re_path(
        r'ws/requests/$',
        consumers.RequestConsumer.as_asgi()
    ),

    re_path(
        r'ws/tracking/(?P<id>\d+)/$',
        consumers.RequestConsumer.as_asgi()
    ),

    path('ws/chat/<int:request_id>/', consumers.ChatConsumer.as_asgi()),
]
