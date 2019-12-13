import logging

from django.contrib.auth.models import User
from unplugged import RelatedPluginField, Schema, fields
from wampyre.realm import realm_manager

from ...plugins import NotifierPlugin

logger = logging.getLogger(__name__)


class MultiNotifierSchema(Schema):
    notifiers = fields.List(
        RelatedPluginField(plugin_type=NotifierPlugin), many=True, default=list
    )


class MultiNotifierNotifierHandlerPlugin(NotifierPlugin):
    plugin_name = "multinotifier"
    config_schema = MultiNotifierSchema

    def notify(self, notification):
        for notifier in self.config.get("notifiers", []):
            notifier.notify(notification)
