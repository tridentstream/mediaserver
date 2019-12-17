import logging

from django.contrib.auth.models import User
from unplugged import RelatedPluginField, Schema, fields
from wampyre.realm import realm_manager

from ...plugins import ConfigPlugin, NotifierPlugin

logger = logging.getLogger(__name__)


class WAMPSchema(Schema):
    config = RelatedPluginField(plugin_type=ConfigPlugin)


class NotifyFilterSchema(Schema):
    patterns = fields.List(fields.String, many=True, default=list)


class WAMPNotifierHandlerPlugin(NotifierPlugin):
    plugin_name = "wamp"
    config_schema = WAMPSchema

    default_config = {"patterns": ["admin.*"]}

    def __init__(self, config):
        self.config = config

        config_plugin = config.get("config")
        if config_plugin:
            namespace, key = self.get_config_values()
            config_plugin.set_default_config(
                "system", namespace, key, self.default_config
            )
            config_plugin.set_config_schema(namespace, key, NotifyFilterSchema)

    def get_config_values(self):
        return f"{self.plugin_type}:{self.name}", "notification_filters"

    def notify(self, notification):
        config_plugin = self.config.get("config")
        if not config_plugin:
            return

        namespace, key = self.get_config_values()

        for realm in realm_manager.get_realms():  # TODO: optimize !
            if not realm.realm.startswith("user."):
                continue

            username = realm.realm[5:]
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                continue

            if not notification.is_allowed(user):
                continue

            config = config_plugin.get_user_config(user, namespace, key)

            if not notification.match_patterns(config.get("patterns", [])):
                continue

            realm.publish(
                {},
                "notification",
                args=(),
                kwargs={
                    "topic": notification.topic,
                    "type": notification.type,
                    "title": notification.title,
                    "body": notification.body,
                },
            )
