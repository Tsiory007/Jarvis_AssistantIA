"""
ASGI config for AssistantAi project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter

from channels.auth import AuthMiddlewareStack
import Jarvis.routingProtocol

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AssistantAi.settings')

application = ProtocolTypeRouter({'http': get_asgi_application(), 
                                    'websocket': AuthMiddlewareStack(
                                        URLRouter( Jarvis.routingProtocol.websocket_urlpatterns)
                                    )})
    