import os

from django.conf import settings
from django.conf.urls import url
from unplugged import RelatedPluginField, Schema, ServicePlugin, fields

from ...plugins import ConfigPlugin
from ...utils import serve
from .views import IndexView


class WebinterfaceSchema(Schema):
    mount_at_root = fields.Boolean()
    config = RelatedPluginField(plugin_type=ConfigPlugin)


class FrontpageConfigSourceQuerySchema(Schema):
    key = fields.String(required=True)
    value = fields.String(required=True)


class FrontpageConfigDocChainSchema(Schema):
    type = fields.String(required=True)
    id = fields.String(required=False)


class FrontpageConfigSourceSchema(Schema):
    docChain = fields.Nested(FrontpageConfigDocChainSchema, many=True, required=True)
    contentType = fields.String(
        enum=settings.TRIDENTSTREAM_CONTENT_TYPES,
        enum_names=settings.TRIDENTSTREAM_CONTENT_TYPES_NAMES,
        default="",
    )
    template = fields.String(
        enum=settings.TRIDENTSTREAM_TEMPLATES,
        enum_names=settings.TRIDENTSTREAM_TEMPLATES_NAMES,
        default="cover",
        required=True,
    )
    query = fields.Nested(FrontpageConfigSourceQuerySchema, many=True)
    enabled = fields.Boolean()


class FrontpageConfigSchema(Schema):
    title = fields.String(required=True)
    sources = fields.Nested(FrontpageConfigSourceSchema, many=True, required=True)
    enabled = fields.Boolean()


class FrontpageConfigRootSchema(Schema):
    sections = fields.Nested(FrontpageConfigSchema, many=True)


class WebinterfaceServicePlugin(ServicePlugin):
    plugin_name = "webinterface"

    config_schema = WebinterfaceSchema

    default_config = {
        "sections": [
            {
                "title": "Shows you follow",
                "sources": [
                    {
                        "docChain": [{"type": "service_sections"}, {"type": "folder"}],
                        "contentType": "tvshows",
                        "template": "cover",
                        "enabled": True,
                        "query": [
                            {"key": "limit", "value": "12"},
                            {"key": "o", "value": "-datetime"},
                            {"key": "metadata_tag__tag_name", "value": "follow"},
                        ],
                    }
                ],
                "enabled": True,
            },
            {
                "title": "Good, new movies",
                "sources": [
                    {
                        "docChain": [{"type": "service_sections"}, {"type": "folder"}],
                        "contentType": "movies",
                        "template": "cover",
                        "enabled": True,
                        "query": [
                            {"key": "limit", "value": "24"},
                            {
                                "key": "o",
                                "value": "-metadata_firstseen__datetime,-datetime",
                            },
                        ],
                    }
                ],
                "enabled": True,
            },
        ]
    }

    def __init__(self, config):
        if config["mount_at_root"]:
            self.mount_at_root = True

        config_plugin = config.get("config")
        if config_plugin:
            namespace = f"{self.plugin_type}:{self.name}"
            key = "frontpage_listings"
            config_plugin.set_default_config(
                "system", namespace, key, self.default_config
            )
            config_plugin.set_config_schema(namespace, key, FrontpageConfigRootSchema)

    def get_urls(self):
        return [
            url(r"^/?$", IndexView.as_view(service=self)),
            url(r"^/index.html$", IndexView.as_view(service=self)),
            url(
                r"^(?P<path>.*)$",
                serve,
                kwargs={
                    "document_root": os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), "static"
                    )
                },
            ),
        ]
