from django.conf.urls import url
from unplugged import Schema, ServicePlugin

from .views import MetadataView


class MetadataServicePlugin(ServicePlugin):
    plugin_name = "metadata"
    config_schema = Schema
    __traits__ = ["metadata_server"]

    def get_urls(self):
        return [
            url(
                "^(?P<metadata_handler>[a-z_]+)/(?P<identifier>[^/]+)/?$",
                MetadataView.as_view(service=self),
                name="metadata",
            )
        ]
