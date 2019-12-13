from django.conf.urls import url
from unplugged import (
    DefaultPermission,
    RelatedPluginField,
    Schema,
    ServicePlugin,
    fields,
)

from ...plugins import InputPlugin
from .views import RemoteFilesystemView


class RemoteFilesystemInputSchema(Schema):
    input = RelatedPluginField(plugin_type=InputPlugin, required=True)


class RemoteFilesystemServiceSchema(Schema):
    inputs = fields.Nested(RemoteFilesystemInputSchema, many=True)


class RemoteFilesystemService(ServicePlugin):
    plugin_name = "rfs"
    config_schema = RemoteFilesystemServiceSchema
    default_permission = DefaultPermission.DENY

    def get_urls(self):
        return [url("^(?P<path>.*)", RemoteFilesystemView.as_view(service=self))]
