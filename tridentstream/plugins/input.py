import hashlib
import json
import logging
from abc import abstractmethod
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from thomas import router
from unplugged import PluginBase, pluginhandler

from ..exceptions import NotModifiedException, PathNotFoundException
from ..stream import Stream
from ..utils import hash_string

logger = logging.getLogger(__name__)

LISTING_CACHE_TIME = timedelta(days=7)
THOMAS_LIST_HANDLER_NAME = "ts_list"


class InputPlugin(PluginBase):
    plugin_type = "input"

    @abstractmethod
    def get_item(self, path):
        """
        Return an item for a given path.

        Does not have to be populated with correct data but it should
        contain the correct routes.
        """


def _listing_cache_key(prefix, plugin, path, depth):
    return f"listing:{prefix}:{plugin}:{depth}:{hash_string(path)}"


class InputPluginManager:
    @staticmethod
    def get_item_multiple(
        plugin_path_pairs,
    ):  # get an item for all paths and merge into one
        item = None
        for plugin, path in plugin_path_pairs:
            plugin_item = plugin.get_item(path)
            if item:
                item.merge(plugin_item)
            else:
                item = plugin_item

        return item

    @staticmethod
    def get_item(plugin, path):
        return InputPluginManager.get_item_multiple([(plugin, path)])

    @staticmethod
    def cached_list(f, item, _route_name, **kwargs):
        key = json.dumps((item.id, _route_name, sorted(kwargs.items()))).encode("utf-8")
        cache_key = hashlib.sha1(key).hexdigest()
        cache_key_date = f"date:{cache_key}"
        cache_key_listing = f"listing:{cache_key}"

        cached_date = cache.get(cache_key_date)
        if cached_date:
            logger.debug(
                f"We found a cache date {cached_date}, looking for listing too"
            )
            cached_listing = cache.get(cache_key_listing)
        else:
            cached_listing = None

        if not cached_listing:
            cached_date = None

        listed = False
        kwargs["modified_since"] = cached_date
        try:
            listing = f(item, **kwargs)
            listed = True
        except NotModifiedException:
            listing = item.__class__.unserialize(cached_listing, router=item.router)
        except PathNotFoundException:
            logger.debug(f"Path not found on {f!r}")
            item.expandable = False
            return None
        except Exception:
            logger.exception(f"Failed to list {f!r}")
            item.expandable = False
            return None

        if listed and listing:
            cache.set(
                cache_key_date,
                listing.modified + timedelta(seconds=2),
                LISTING_CACHE_TIME.total_seconds(),
            )
            cache.set(
                cache_key_listing,
                listing.serialize(include_routes=True),
                LISTING_CACHE_TIME.total_seconds(),
            )
            logger.debug(
                f"Caching listing for item:{item} with modified:{listing.modified} and using f:{f!r} kwargs:{kwargs!r}"
            )

        return listing


router.list_decorator = InputPluginManager.cached_list
