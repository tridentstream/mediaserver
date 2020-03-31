import logging
from datetime import timedelta

from django.conf.urls import url
from django.utils.timezone import now
from unplugged import DefaultPermission, RelatedPluginField, Schema, fields

from ...bases.listing.handler import BaseListingService
from ...bases.listing.schema import BaseSchema, ListingSchema
from ...exceptions import NotModifiedException
from ...plugins import SearcherPlugin, SearcherPluginManager
from .models import SearchQueryCache
from .views import StoreListView

logger = logging.getLogger(__name__)
LISTING_CACHE_TIME = timedelta(minutes=10)


class StoreSearcherSchema(Schema):
    preference = fields.Integer(default=10)
    searcher = RelatedPluginField(plugin_type=SearcherPlugin)


class StoreSchema(ListingSchema):
    searchers = fields.Nested(StoreSearcherSchema, many=True, default=list)
    rebuild_automatically = fields.Boolean(default=False)


class StoreServiceSchema(BaseSchema):
    sections = fields.Nested(StoreSchema, many=True, default=list)


class StoreService(BaseListingService):
    plugin_name = "store"
    config_schema = StoreServiceSchema
    default_permission = DefaultPermission.ALLOW

    simpleadmin_templates = [
        {
            "template": {
                "display_name": {"simpleAdminMethod": "userInput", "required": True},
                "searchers": {"simpleAdminMethod": "userInput"},
                "name": {"simpleAdminMethod": "slugify", "source": "display_name"},
                "histories": [
                    {
                        "simpleAdminMethod": "lookupPlugin",
                        "plugin_type": "history",
                        "name": "history",
                    }
                ],
                "rebuild_automatically": False,
                "levels": [
                    {
                        "indexer": None,
                        "depth": 1,
                        "content_type": "movies",
                        "listing_depth": 0,
                        "default_ordering": "metadata_embedded__index",
                        "metadata_handlers": [
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "historymetadata",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "embedded",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "imdb",
                            },
                        ],
                    },
                    {
                        "indexer": None,
                        "depth": 2,
                        "content_type": "movie",
                        "listing_depth": 0,
                        "default_ordering": "metadata_embedded__index",
                        "metadata_handlers": [
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "name",
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
                                "name": "embedded",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "available",
                            },
                        ],
                    },
                ],
            },
            "description": "Search for movies",
            "id": "movies",
            "update_method": "modify_key",
            "modify_key": "sections",
        },
        {
            "template": {
                "display_name": {"simpleAdminMethod": "userInput", "required": True},
                "searchers": {"simpleAdminMethod": "userInput"},
                "name": {"simpleAdminMethod": "slugify", "source": "display_name"},
                "histories": [
                    {
                        "simpleAdminMethod": "lookupPlugin",
                        "plugin_type": "history",
                        "name": "history",
                    }
                ],
                "rebuild_automatically": False,
                "levels": [
                    {
                        "indexer": None,
                        "depth": 1,
                        "content_type": "tvshows",
                        "listing_depth": 0,
                        "default_ordering": "metadata_embedded__index",
                        "metadata_handlers": [
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "historymetadata",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "embedded",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "imdb",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "mal",
                            },
                        ],
                    },
                    {
                        "indexer": None,
                        "depth": 2,
                        "content_type": "seasons",
                        "default_ordering": "-metadata_embedded__season,metadata_embedded__index",
                        "listing_depth": 0,
                        "metadata_handlers": [
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "embedded",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "available",
                            },
                        ],
                    },
                    {
                        "indexer": None,
                        "depth": 3,
                        "content_type": "episodes",
                        "default_ordering": "-metadata_embedded__season,-metadata_embedded__episode,-metadata_iteminfo__season,-metadata_iteminfo__episode,metadata_embedded__index",
                        "listing_depth": 0,
                        "metadata_handlers": [
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "name",
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
                                "name": "embedded",
                            },
                            {
                                "simpleAdminMethod": "lookupPlugin",
                                "plugin_type": "metadatahandler",
                                "name": "available",
                            },
                        ],
                    },
                ],
            },
            "description": "Search for TV Shows\n"
            "Data must be stored in show/season.01/episode.01 format",
            "id": "tv-season-episode",
            "update_method": "modify_key",
            "modify_key": "sections",
        },
    ]

    def get_urls(self):
        return [
            url(
                r"^(?P<path>.*)$",
                StoreListView.as_view(
                    service=self, listing_builder=self.listing_builder
                ),
            )
        ]

    def get_filters(self, config):
        return SearcherPluginManager.filters_multiple(
            [searcher["searcher"] for searcher in config["searchers"]]
        )

    def get_path_config(self, path):
        config = super(StoreService, self).get_path_config(path)
        config["fetch_metadata"] = False
        return config

    def get_item(self, config, path):
        logger.debug("Getting item for %s" % (path,))
        if not config.get("searchers"):
            return None
        path = path.split("/")
        root_path, query_hash = path[:2]
        trailing_path = "/".join(path[2:])
        try:
            search_query_cache = SearchQueryCache.objects.get(query_hash=query_hash)
        except SearchQueryCache.DoesNotExist:
            logger.info(f"Trying to list a non-existant query_hash {query_hash}")
            return None

        searchers = [searcher["searcher"] for searcher in config["searchers"]]

        if (
            trailing_path
        ):  # We cant create an item for a subpath, we need to have the original query
            return None

        filters = self.get_filters(config)
        search_query = search_query_cache.get_search_query(filters)
        item = SearcherPluginManager.get_item_multiple(
            searchers, query_hash, search_query
        )

        logger.debug(f"we are at {trailing_path} - {config!r}")

        if not trailing_path and "display_name" in config:
            item.id = config["display_name"]

        return item
