import functools
import logging

from django.urls import path
from unplugged import Schema, ServicePlugin

from .ws import PlayerConsumer

logger = logging.getLogger(__name__)


def inject_into_scope(func, extra_scope):
    @functools.wraps(func)
    def inner(scope, *args, **kwargs):
        scope.update(extra_scope)
        return func(scope, *args, **kwargs)

    return inner


class PlayerServicePlugin(ServicePlugin):
    plugin_name = "player"
    config_schema = Schema

    __traits__ = ["player"]

    def __init__(self, config):
        self.player_coordinators = {}

    def get_channels(self):
        return [("", inject_into_scope(PlayerConsumer, {"service": self}))]

    def unload(self):
        for player_cordinator in self.player_coordinators.values():
            player_cordinator.shutdown()

        super().unload()

    def get_player_coordinator(self, user):
        if user not in self.player_coordinators:
            self.player_coordinators[user] = PlayerCoordinator(user)

        return self.player_coordinators[user]

    def play(self, payload, viewstate, player_id):
        logger.debug(f"Sending play to player_id:{player_id} user:{viewstate.user!r}")
        player_coordinator = self.get_player_coordinator(viewstate.user)

        player = player_coordinator.get_player(player_id)
        # TODO: ensure player exists

        player.connect_viewstate(viewstate)
        player.command("play", payload, viewstate.serialize())


class Player:
    def __init__(
        self, player_coordinator, websocket, player_id, name, commands, options
    ):
        self.player_coordinator = player_coordinator
        self.websocket = websocket
        self.player_id = player_id
        self.name = name
        self.state = "stopped"
        self.values = {}
        self.commands = commands
        self.options = options
        self.viewstate = None

    def command(self, method, *args):
        self.websocket.jsonrpc_method(method, *args)

    def change_state(
        self, state, values, viewstate_id=None
    ):  # we need to viewstate_id something
        if state != self.state:
            logger.debug(
                f"Main state changed for {self.player_id} from {self.state} to {state}, clearing values"
            )
            self.values = {}

        self.state = state
        self.values.update(values)
        if values and self.viewstate is not None and self.viewstate.id == viewstate_id:
            logger.debug(f"Updating viewstate {viewstate_id}")
            self.viewstate.update(values)

        self.publish_state()

    def request_state(self, state, values):
        logger.debug(f"Requesting state on id:{self.player_id} {state}/{values!r}")
        self.command("request_state", state, values)

    def connect_viewstate(self, viewstate):
        logger.debug(f"Connected player {self.player_id} with viewstate {viewstate.id}")
        self.viewstate = viewstate
        self.viewstate.player_connected = True

    def close(self):
        logger.debug(f"Closing connection to player_id:{self.player_id}")
        self.websocket.close()

    def serialize(self):
        return {
            "player_id": self.player_id,
            "name": self.name,
            "state": self.state,
            "values": self.values,
            "options": self.options,
            "commands": self.commands,
        }

    def publish_state(self):
        self.player_coordinator.command("update", self.serialize())


class PlayerCoordinator:
    def __init__(self, user):
        self.user = user
        self.players = {}
        self.controllers = []

    def add_player(self, websocket, player_id, name, commands, options):
        self.remove_player(player_id)

        player = Player(self, websocket, player_id, name, commands, options)
        self.players[player_id] = player

        player.publish_state()

    def remove_player(self, player_id):
        player = self.players.pop(player_id, None)
        if player:
            logger.debug(f"Player {player_id} gone")
            player.close()

        self.command("disconnected", {"player_id": player_id})

    def get_player(self, player_id):
        return self.players.get(player_id)

    def add_controller(self, websocket):
        logger.debug("Controller added")

        for player in self.players.values():
            websocket.jsonrpc_method("update", player.serialize())

        self.controllers.append(websocket)

    def remove_controller(self, websocket):
        logger.debug("Controller gone")
        if websocket in self.controllers:
            self.controllers.remove(websocket)

    def shutdown(self):
        for player in self.players.values():
            player.close()

        for controller in self.controllers:
            controller.close()

    def command(self, method, *args):
        for controller in self.controllers:
            controller.jsonrpc_method(method, *args)
