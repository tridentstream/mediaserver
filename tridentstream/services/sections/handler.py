import logging

from django.conf.urls import url
from unplugged import DefaultPermission, RelatedPluginField, Schema, command, fields

from ...bases.listing.handler import BaseListingService
from ...bases.listing.models import ListingItem
from ...bases.listing.schema import BaseSchema, ListingSchema
from ...plugins import InputPlugin, InputPluginManager
from .views import SectionsListView

logger = logging.getLogger(__name__)


class SectionInputSchema(Schema):
    path = fields.String(default="")
    preference = fields.Integer(default=10)
    input = RelatedPluginField(plugin_type=InputPlugin, required=True)


class SectionSchema(ListingSchema):
    inputs = fields.Nested(SectionInputSchema, many=True, default=list)


class SectionServiceSchema(BaseSchema):
    sections = fields.Nested(SectionSchema, many=True, default=list)


class SectionsService(BaseListingService):
    plugin_name = "sections"
    config_schema = SectionServiceSchema
    default_permission = DefaultPermission.ALLOW

    simpleadmin_templates = [
        {
            "template": {
                "display_name": {"simpleAdminMethod": "userInput", "required": True},
                "inputs": {
                    "simpleAdminMethod": "userInput",
                    "hideFields": ["preference"],
                },
                "name": {"simpleAdminMethod": "slugify", "source": "display_name"},
                "histories": [
                    {
                        "simpleAdminMethod": "lookupPlugin",
                        "plugin_type": "history",
                        "name": "history",
                    }
                ],
                "primary_metadata_plugin": {
                    "simpleAdminMethod": "injectablePlugin",
                    "plugin_type": "metadatahandler",
                    "required": False,
                    "traits": ["primary_metadata", "metadata_movie"],
                },
                "rebuild_automatically": True,
                "levels": [
                    {
                        "indexer": {
                            "simpleAdminMethod": "createPlugin",
                            "plugin_type": "indexer",
                            "plugin_name": "whoosh",
                            "name": "index_automanaged_%(name)s",
                            "config": {"path": "index_automanaged_%(name)s"},
                        },
                        "depth": 0,
                        "content_type": "movies",
                        "default_ordering": "-metadata_firstseen__datetime,-datetime",
                        "listing_depth": 0,
                        "tags": [
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "tag",
                                "name": "tag",
                            }
                        ],
                        "metadata_handlers": [
                            {
                                "simpleAdminMethod": "injectedPlugin",
                                "id": "primary_metadata_plugin",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "historymetadata",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "iteminfo",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "firstseen",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "name",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "tag",
                            },
                        ],
                    }
                ],
            },
            "description": "A folder with movies in it",
            "id": "movies",
            "update_method": "modify_key",
            "modify_key": "sections",
            "display_name": "Movies",
        },
        {
            "template": {
                "display_name": {"simpleAdminMethod": "userInput", "required": True},
                "inputs": {
                    "simpleAdminMethod": "userInput",
                    "hideFields": ["preference"],
                },
                "name": {"simpleAdminMethod": "slugify", "source": "display_name"},
                "histories": [
                    {
                        "simpleAdminMethod": "lookupPlugin",
                        "plugin_type": "history",
                        "name": "history",
                    }
                ],
                "primary_metadata_plugin": {
                    "simpleAdminMethod": "injectablePlugin",
                    "plugin_type": "metadatahandler",
                    "traits": ["primary_metadata", "metadata_tv"],
                },
                "rebuild_automatically": True,
                "levels": [
                    {
                        "indexer": {
                            "simpleAdminMethod": "createPlugin",
                            "plugin_type": "indexer",
                            "plugin_name": "whoosh",
                            "name": "index_automanaged_%(name)s",
                            "config": {"path": "index_automanaged_%(name)s"},
                        },
                        "depth": 0,
                        "content_type": "tvshows",
                        "default_ordering": "-datetime",
                        "listing_depth": 0,
                        "tags": [
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "tag",
                                "name": "tag",
                            }
                        ],
                        "metadata_handlers": [
                            {
                                "simpleAdminMethod": "injectedPlugin",
                                "id": "primary_metadata_plugin",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "tag",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "firstseen",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "name",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "tag",
                            },
                        ],
                    },
                    {
                        "indexer": None,
                        "depth": 1,
                        "content_type": "episodes",
                        "default_ordering": "-metadata_iteminfo__season,-metadata_iteminfo__episode",
                        "listing_depth": 0,
                        "metadata_handlers": [
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "historymetadata",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "iteminfo",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "firstseen",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "name",
                            },
                        ],
                    },
                ],
            },
            "description": "Folder with TV shows.\n\n"
            "The folder must have the organization /tv/show/episode.\n"
            "An example could be /TVFolder/A.Good.Show/A.Good.Show.S03E03",
            "id": "tv-episode",
            "update_method": "modify_key",
            "modify_key": "sections",
            "display_name": "TV /tv/show/episode",
        },
        {
            "template": {
                "display_name": {"simpleAdminMethod": "userInput", "required": True},
                "inputs": {
                    "simpleAdminMethod": "userInput",
                    "hideFields": ["preference"],
                },
                "name": {"simpleAdminMethod": "slugify", "source": "display_name"},
                "histories": [
                    {
                        "simpleAdminMethod": "lookupPlugin",
                        "plugin_type": "history",
                        "name": "history",
                    }
                ],
                "primary_metadata_plugin": {
                    "simpleAdminMethod": "injectablePlugin",
                    "plugin_type": "metadatahandler",
                    "traits": ["primary_metadata", "metadata_tv"],
                },
                "rebuild_automatically": True,
                "levels": [
                    {
                        "indexer": {
                            "simpleAdminMethod": "createPlugin",
                            "plugin_type": "indexer",
                            "plugin_name": "whoosh",
                            "name": "index_automanaged_%(name)s",
                            "config": {"path": "index_automanaged_%(name)s"},
                        },
                        "depth": 0,
                        "content_type": "tvshows",
                        "default_ordering": "-datetime",
                        "listing_depth": 0,
                        "tags": [
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "tag",
                                "name": "tag",
                            }
                        ],
                        "metadata_handlers": [
                            {
                                "simpleAdminMethod": "injectedPlugin",
                                "id": "primary_metadata_plugin",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "tag",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "firstseen",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "name",
                            },
                        ],
                    },
                    {
                        "indexer": None,
                        "depth": 1,
                        "content_type": "seasons",
                        "default_ordering": "-metadata_iteminfo__season",
                        "listing_depth": 0,
                        "metadata_handlers": [
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "iteminfo",
                            }
                        ],
                    },
                    {
                        "indexer": None,
                        "depth": 2,
                        "content_type": "episodes",
                        "default_ordering": "-metadata_iteminfo__season,-metadata_iteminfo__episode",
                        "listing_depth": 0,
                        "metadata_handlers": [
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "historymetadata",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "iteminfo",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "firstseen",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "name",
                            },
                        ],
                    },
                ],
            },
            "description": "Folder with TV shows.\n\n"
            "The folder must have the organization /tv/show/season/episode.\n"
            "An example could be /TVFolder/A.Good.Show/Season.03/A.Good.Show.S03E03",
            "id": "tv-season-episode",
            "update_method": "modify_key",
            "modify_key": "sections",
            "display_name": "TV /tv/show/season/episode",
        },
    ]

    def get_urls(self):
        return [
            url(
                r"^(?P<path>.*)$",
                SectionsListView.as_view(
                    service=self, listing_builder=self.listing_builder
                ),
            )
        ]

    def get_item(self, config, path):
        if not config.get("inputs"):
            return None

        plugin_path_pairs = []
        for input_config in config["inputs"]:
            input_path = input_config.get("path", "").strip("/")
            listing_path = f"{input_path}/{config['path']}"
            plugin_path_pairs.append((input_config["input"], listing_path.strip("/")))

        logger.info(f"Trying to create listing for {plugin_path_pairs!r} - path:{path}")
        item = InputPluginManager.get_item_multiple(plugin_path_pairs)
        if "/" not in path and "display_name" in config:
            item.id = config["display_name"]
        return item
