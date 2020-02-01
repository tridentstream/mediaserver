import logging
import time
from datetime import timedelta

import requests
from django.utils.timezone import now
from thomas import Item, router

from ...exceptions import PathNotFoundException, StreamFailedException
from ...plugins import SearcherPlugin
from ...utils import urljoin
from .mixins import (
    CacheSearchMixin,
    FilterRewriteMixin,
    LoginMixin,
    TorrentMixin,
    WebSessionMixin,
)
from .schema import LoginTorrentSearcherSchema, TorrentSearcherSchema, URLSearcherSchema

logger = logging.getLogger(__name__)


class URLSearcherPluginBase(
    CacheSearchMixin, FilterRewriteMixin, WebSessionMixin, SearcherPlugin
):
    base_url = None
    search_path = None
    config_schema = URLSearcherSchema

    def __init__(self, config):
        self.config = config
        self.priority = config.get("priority", 10)
        self.route_searcher_base_query = f"searcher_base_query_{self.name}"
        self.route_searcher_base_list = f"searcher_base_list_{self.name}"
        self.route_searcher_base_stream = f"searcher_base_stream_{self.name}"

        router.register_handler(
            self.route_searcher_base_query, self.thomas_query, False, True, False
        )
        router.register_handler(
            self.route_searcher_base_list, self.thomas_list, False, True, False
        )
        router.register_handler(
            self.route_searcher_base_stream, self.thomas_stream, False, False, True
        )

    def build_url(self, url, params=None):
        return (
            requests.Request("GET", urljoin(self.base_url, url), params=(params or {}))
            .prepare()
            .url
        )

    def get_item(self, search_token, search_query):
        query = self.parse_search_query(search_query)
        item = Item(id="")
        item.expandable = True
        kwargs = {
            "url": self.build_url(self.search_path),
            "query": query,
            "search_token": search_token,
            "path": "",
            "response_type": "root",
        }
        item.add_route(
            self.route_searcher_base_query,
            False,
            True,
            False,
            kwargs=kwargs,
            priority=self.priority,
        )

        return item

    def do_query(self, session, url, query, headers=None):
        return session.get(self.build_url(url, query), headers=headers)

    def add_cache_list_routes(self, item, search_token, root_path, path="", skip=False):
        if path:
            path = f"{path}/{item.id}"
        else:
            path = item.id

        if item.is_expanded:
            for nested_item in item.nested_items:
                self.add_cache_list_routes(nested_item, search_token, root_path, path)

            if not skip:
                item.expandable = True
                item.add_route(
                    self.route_searcher_base_list,
                    False,
                    True,
                    False,
                    kwargs={
                        "path": root_path,
                        "sub_path": path,
                        "search_token": search_token,
                    },
                )

    def add_stream_routes(
        self, item, stream_info, path="", skip=False, ensure_already_streamable=False
    ):
        if not skip:
            if path:
                path = f"{path}/{item.id}"
            else:
                path = item.id

        if not ensure_already_streamable or item.is_streamable:
            self.make_streamable(item, stream_info, path)

        if item.is_expanded:
            for nested_item in item.nested_items:
                self.add_stream_routes(nested_item, stream_info, path)

    def thomas_query(
        self,
        item,
        search_token,
        path,
        response_type,
        url,
        query,
        depth=0,
        modified_since=None,
    ):  # Fetches listing from website
        logger.debug(
            f"Trying to query search_token:{search_token} path:{path} response_type:{response_type} url:{url}"
        )

        cached_search_result = self.get_cache_results(search_token, path)
        if (
            cached_search_result
            and cached_search_result.modified > now() - self.search_result_cache_time
        ):
            logger.debug(
                f"We got a cached query result for search_token:{search_token}, using that"
            )
            return cached_search_result

        with self.get_session() as session:
            self.check_site_usable(session)

            response = self.do_query(session, url, query)

        item = self.parse_result(search_token, path, response, response_type)

        self.add_cache_list_routes(item, search_token, path, skip=True)

        item["modified"] = int(time.time())

        self.cache_search_result(search_token, path, item)

        return item

    def thomas_list(
        self, item, search_token, path, sub_path, depth=0, modified_since=None
    ):  # Queries a cache for a listing
        logger.debug(
            f"Trying to list search_token:{search_token} path:{path} sub_path:{sub_path}"
        )

        cached_search_result = self.get_cache_results(search_token, path)
        if not cached_search_result:
            logger.debug(
                f"Cannot list because we were unable to find cache for search_token:{search_token} path:{path}"
            )
            raise PathNotFoundException()

        item = cached_search_result.get_item_from_path(sub_path)
        return item

    def make_streamable(self, item, stream_info, sub_path=""):
        item.streamable = True
        item.add_route(
            self.route_searcher_base_stream,
            False,
            False,
            True,
            kwargs={"sub_path": sub_path, "stream_info": stream_info},
        )

    def make_expandable(self, item, search_token, url, query, path, response_type):
        item.expandable = True
        item.add_route(
            self.route_searcher_base_query,
            False,
            True,
            False,
            kwargs={
                "search_token": search_token,
                "url": url,
                "query": query,
                "path": path,
                "response_type": response_type,
            },
        )

    def mark_available(self, item):
        identifiers = [
            available["identifier"]
            for available in item.get("metadata:availability", [])
        ]
        availability_plugin = self.config.get("availability")
        if availability_plugin:
            for identifier in identifiers:
                availability_plugin.mark_available(self.name, identifier)

    def populate_available(self, item):
        availability_plugin = self.config.get("availability")
        if availability_plugin:
            availability_plugin.populate_available(item)

    def get_recently_downloaded_identifiers(self):
        recently_downloaded_identifiers = set()
        availability_plugin = self.config.get("availability")
        if availability_plugin:
            for available in availability_plugin.get_recently_made_available(
                self.name, now() - timedelta(hours=24)
            ):
                recently_downloaded_identifiers.add(available["identifier"])

        return list(recently_downloaded_identifiers)

    def thomas_stream(self, item, stream_info, sub_path):
        raise NotImplementedError()

    def parse_result(self, search_token, session, response, response_type):
        """
        Parse a response.
        """
        raise NotImplementedError


class TorrentStreamer:
    def __init__(self, plugin, item, torrent_info, torrent_path, priority):
        self.plugin = plugin
        self.item = item
        self.torrent_info = torrent_info
        self.torrent_path = torrent_path
        self.priority = priority

    def evaluate(self):
        return self.priority

    def stream(self):
        torrent_file = self.plugin.get_torrent(**self.torrent_info)

        self.plugin.mark_available(self.item)

        client = self.plugin.config["bittorrent_client"]
        return self.plugin.stream_torrent(client, torrent_file, self.torrent_path)


class TorrentSearcherPluginBase(TorrentMixin, URLSearcherPluginBase):
    config_schema = TorrentSearcherSchema

    def __init__(self, config):
        super().__init__(config)
        self.route_searcher_base_list_torrent = (
            f"searcher_base_list_torrent_{self.name}"
        )
        router.register_handler(
            self.route_searcher_base_list_torrent,
            self.thomas_list_torrent,
            False,
            True,
            False,
        )

    def thomas_list_torrent(
        self, item, search_token, path, torrent_info, depth=0, modified_since=None
    ):
        torrent_file = self.get_torrent(**torrent_info)

        item = self.list_torrent(item, torrent_file)

        self.add_stream_routes(item, torrent_info, skip=True)
        self.add_cache_list_routes(item, search_token, path, skip=True)
        self.cache_search_result(search_token, path, item)

        return item

    def thomas_stream(self, item, stream_info, sub_path):
        self.populate_available(item)
        is_available = item.get("metadata", {}).get("available", False)
        if (
            not is_available
            and len(self.get_recently_downloaded_identifiers())
            >= self.config.get("daily_download_count_cap", 0)
            > 0
        ):
            logger.info(
                f"Cannot stream name:{self.name} item:{item!r} because we have reached cap"
            )
            raise StreamFailedException()

        return TorrentStreamer(
            self, item, stream_info, sub_path, self.priority + (is_available * 100)
        )

    def make_expandable_torrent(self, item, search_token, path, torrent_info):
        item.expandable = True
        item.add_route(
            self.route_searcher_base_list_torrent,
            False,
            True,
            False,
            kwargs={
                "search_token": search_token,
                "path": path,
                "torrent_info": torrent_info,
            },
        )

    def get_torrent(self, url):
        return self.fetch_torrent(url)


class LoginTorrentSearcherPluginBase(LoginMixin, TorrentSearcherPluginBase):
    config_schema = LoginTorrentSearcherSchema
