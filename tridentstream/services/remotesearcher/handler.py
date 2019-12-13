from django.conf.urls import url
from unplugged import (
    DefaultPermission,
    RelatedPluginField,
    Schema,
    ServicePlugin,
    fields,
)

from ...plugins import MetadataHandlerPlugin, SearcherPlugin
from .views import RemoteSearcherFiltersView, RemoteSearcherView


class RemoteSearcherSchema(Schema):
    searcher = RelatedPluginField(plugin_type=SearcherPlugin)


class RemoteSearcherServiceSchema(Schema):
    searchers = fields.Nested(RemoteSearcherSchema, many=True)
    availability = RelatedPluginField(
        plugin_type=MetadataHandlerPlugin, traits=["availability"]
    )


class RemoteSearcherService(ServicePlugin):
    plugin_name = "remotesearcher"
    config_schema = RemoteSearcherServiceSchema
    default_permission = DefaultPermission.DENY

    simpleadmin_templates = True

    def get_urls(self):
        return [
            url("^/?$", RemoteSearcherFiltersView.as_view(service=self)),
            url(
                "^(?P<searcher_name>[^/]+)/?$", RemoteSearcherView.as_view(service=self)
            ),
            url(
                "^(?P<searcher_name>[^/]+)/(?P<search_token>[^/]+)/?$",
                RemoteSearcherView.as_view(service=self),
            ),
            url(
                "^(?P<searcher_name>[^/]+)/(?P<search_token>[^/]+)/(?P<path>.+)$",
                RemoteSearcherView.as_view(service=self),
            ),
        ]
