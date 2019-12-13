from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf.urls import include, url
from unplugged.routing import urlpatterns

application = ProtocolTypeRouter(
    {"websocket": AuthMiddlewareStack(URLRouter(urlpatterns))}
)
