import logging

import requests
from django.core.cache import cache
from thomas import Item
from unplugged import Schema, fields

from ...bases.websearcher.torrentsearcher import URLSearcherPluginBase
from ...exceptions import PathNotFoundException
from ...plugins import SearcherFilter, SearcherPlugin
from ...stream import Stream
from ...utils import urljoin

logger = logging.getLogger(__name__)


class RemoteStreamer:
    def __init__(self, plugin, stream_info, sub_path, priority):
        self.plugin = plugin
        self.stream_info = stream_info
        self.sub_path = sub_path
        self.priority = priority

    def evaluate(self):
        return self.priority

    def stream(self):
        return self.plugin.stream(self.stream_info, self.sub_path)


class RemoteSearcherSearcherSchema(Schema):
    url = fields.String()
    token = fields.String()
    searcher_name = fields.String()
    priority = fields.Integer(default=10)


class RemoteSearcherSearcher(URLSearcherPluginBase):
    plugin_name = "remotesearcher"
    config_schema = RemoteSearcherSearcherSchema

    simpleadmin_templates = True

    base_url = None
    search_path = ""

    @property
    def base_url(self):
        return urljoin(self.config["url"], self.config["searcher_name"])

    def get_headers(self):
        return {"Authorization": f"Token {self.config['token']}"}

    def do_query(self, session, url, query):
        return session.get(
            self.build_url(url, query), headers=self.get_headers()
        ).json()

    def stream(self, stream_info, sub_path):
        url = urljoin(self.base_url, stream_info["search_token"], stream_info["path"])
        params = {"sub_path": sub_path}
        with self.get_session() as session:
            r = session.post(url, headers=self.get_headers(), params=params)

        if r.status_code != 200:
            raise PathNotFoundException()

        return Stream.unserialize(r.json())

    def thomas_stream(self, item, stream_info, sub_path):
        return RemoteStreamer(self, stream_info, sub_path, self.config["priority"])

    def add_expand_routes(self, item, search_token, url, path="", skip=False):
        if not skip:
            if path:
                path = f"{path}/{item.id}"
            else:
                path = item.id

        if item.is_expanded:
            for nested_item in item.nested_items:
                self.add_expand_routes(nested_item, search_token, url, path)
        elif item.expandable:
            self.make_expandable(
                item, search_token, url, {"sub_path": path}, path, None
            )

    def parse_result(self, search_token, session, response, response_type):
        item = Item.unserialize(response["item"])
        self.add_stream_routes(
            item,
            {"search_token": response["search_token"], "path": response["path"]},
            ensure_already_streamable=True,
        )
        url = urljoin(self.base_url, response["search_token"], response["path"])
        self.add_expand_routes(item, search_token, url)
        return item

    @property
    def field_rewrite(self):
        return {k: k for k in self.filters.fields}

    @property
    def filters(self):
        cache_key = f"searcher:filters:{self.name}"
        cache_result = cache.get(cache_key)
        if not cache_result:
            r = requests.get(self.config["url"], headers=self.get_headers())
            if r.status_code != 200:
                return None
            r = r.json()
            cache.set(cache_key, r, 15 * 60)
        else:
            r = cache_result

        for f in r:
            if f["name"] == self.config["searcher_name"]:
                return SearcherFilter.unserialize(f["filters"])

    def check_site_usable(self, session):
        return True
