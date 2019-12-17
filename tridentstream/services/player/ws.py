import json
import logging

from channels.exceptions import AcceptConnection, DenyConnection
from channels.generic.websocket import WebsocketConsumer
from channels.http import AsgiRequest
from django.contrib.auth import login
from jsonrpc import JSONRPCResponseManager
from jsonrpc.dispatcher import Dispatcher
from rest_framework import exceptions, permissions
from rest_framework.settings import api_settings
from unplugged import CascadingPermission

logger = logging.getLogger(__name__)


class DRFWebsocketConsumer(WebsocketConsumer):
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = api_settings.DEFAULT_PERMISSION_CLASSES

    def get_authenticators(self):
        return [auth() for auth in self.authentication_classes]

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    def check_permissions(self, request):
        for permission in self.get_permissions():
            if permission.has_permission(request, self):
                return True
        return False

    def authenticate(self, request):
        authenticators = self.get_authenticators()

        for authenticator in authenticators:
            try:
                result = authenticator.authenticate(request)
                if not result:
                    continue
                user, _ = result
                login(request, user)
                self.scope["user"] = user
                request.user = user
            except exceptions.AuthenticationFailed:
                continue
            else:
                break

    def connect(self):
        self.service = self.scope["service"]

        scope = dict(self.scope)
        scope["method"] = "get"
        request = AsgiRequest(scope, b"")
        request._request = request
        request.user = self.scope["user"]
        request.session = self.scope["session"]

        if not self.scope["user"].is_authenticated:
            self.authenticate(request)

        if self.check_permissions(request):
            raise AcceptConnection()
        else:
            raise DenyConnection()


class PlayerConsumer(DRFWebsocketConsumer):
    user = None
    permission_classes = (permissions.IsAuthenticated,)
    player_id = None
    controller = False

    def accept(self):
        super(PlayerConsumer, self).accept()
        self.user = self.scope["user"]
        self.player_coordinator = self.service.get_player_coordinator(self.user)

    def receive(self, text_data=None, bytes_data=None):
        logger.info(f"Got message from user {self.user!r}: {text_data}")
        response = JSONRPCResponseManager.handle(text_data, self.dispatcher).data
        return self.send(text_data=json.dumps(response))

    @property
    def dispatcher(self):  # TODO: make decorator or something
        d = Dispatcher()

        d.add_method(self.request_player_state, name="request_state")
        d.add_method(self.player_change_state, name="state")
        d.add_method(self.register_player, name="register")
        d.add_method(self.register_controller, name="subscribe")
        d.add_method(self.player_command, name="command")

        return d

    def register_player(self, player_id, name, commands, options):
        logger.debug(f"Adding a player:{player_id} for {self.user.username}")
        self.player_id = player_id
        self.player_coordinator.add_player(self, player_id, name, commands, options)

    def register_controller(self):
        logger.debug(f"Adding a controller for {self.user.username}")
        self.controller = True
        self.player_coordinator.add_controller(self)

    def player_command(self, player_id, method, *args):
        logger.debug(f"Calling command {method} on player_id {player_id}")
        player = self.player_coordinator.get_player(player_id)
        player.command(method, *args)

    def player_change_state(self, state, values, viewstate_id=None):
        player = self.player_coordinator.get_player(self.player_id)
        if not player:
            logger.info(f"Unknown player {self.player_id} found, dropping")
            self.close()
            return

        player.change_state(state, values, viewstate_id)

    def request_player_state(self, player_id, state, values):
        logger.debug("Called request player state")
        player = self.player_coordinator.get_player(player_id)
        player.request_state(state, values)

    def disconnect(self, message, **kwargs):
        logger.debug(f"User connection lost {self.user!r}")

        if self.controller:
            self.player_coordinator.remove_controller(self)

        if self.player_id:
            self.player_coordinator.remove_player(self.player_id)

    def jsonrpc_method(self, method, *args):
        self.send(
            text_data=json.dumps({"jsonrpc": "2.0", "method": method, "params": args})
        )
