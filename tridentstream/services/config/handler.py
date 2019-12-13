from django.conf.urls import url
from unplugged import RelatedPluginField, Schema, ServicePlugin

from ...plugins import ConfigPlugin
from .views import ConfigView


class ConfigServiceSchema(Schema):  # Default configs
    config = RelatedPluginField(plugin_type=ConfigPlugin, required=True)


class ConfigServicePlugin(ServicePlugin):
    plugin_name = "config"
    config_schema = ConfigServiceSchema

    def __init__(self, config):
        self.config = config["config"]

    def get_urls(self):
        return [url("^/?$", ConfigView.as_view(service=self))]
