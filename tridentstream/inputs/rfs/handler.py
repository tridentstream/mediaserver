import logging
from urllib.parse import urljoin

import requests
from thomas import Item, StreamerBase, router
from unplugged import Schema, fields

from twisted.internet import threads

from ...exceptions import NotModifiedException, PathNotFoundException
from ...plugins import InputPlugin
from ...stream import Stream

logger = logging.getLogger(__name__)


class RemoteFilesystemInputSchema(Schema):
    url = fields.String()
    token = fields.String()

    priority = fields.Integer(default=5)


class RemoteFilesystemStreamer:
    def __init__(self, plugin, path):
        self.plugin = plugin
        self.path = path

    def evaluate(self):
        return self.plugin.config["priority"] + 1

    def stream(self):
        return self.plugin.stream(self.path)


class RemoteFilesystemInputPlugin(InputPlugin):
    plugin_name = "remotefilesystem"

    config_schema = RemoteFilesystemInputSchema

    simpleadmin_templates = True

    def __init__(self, config):
        self.config = config

        self.route_input_rfs_list = f"input_rfs_list_{self.name}"
        router.register_handler(
            self.route_input_rfs_list, self.thomas_list, False, True, False
        )

        self.route_input_rfs_stream = f"input_rfs_stream_{self.name}"
        router.register_handler(
            self.route_input_rfs_stream, self.thomas_stream, False, False, True
        )

    def unload(self):
        router.unregister_handler(self.route_input_rfs_list)
        router.unregister_handler(self.route_input_rfs_stream)

    def get_headers(self):
        return {"Authorization": f"Token {self.config['token']}"}

    def get_item(self, path):
        item = Item(id=path.strip().split("/")[-1], router=router)

        item.expandable = True
        item.streamable = True
        self.add_routes(item, path, skip=True)
        # item.add_route(self.route_input_rfs_list, False, True, False, kwargs={'path': path})

        # item.streamable = True
        # item.add_route(self.route_input_rfs_stream, False, False, True, kwargs={'path': path})

        return item

    def add_routes(self, item, path, skip=False):
        if not skip:
            if path:
                path = f"{path}/{item.id}"
            else:
                path = item.id

        if item.is_streamable:
            item.add_route(
                self.route_input_rfs_stream, False, False, True, kwargs={"path": path}
            )

        if item.is_listable:
            if item.is_expanded:
                for nested_item in item.nested_items:
                    self.add_routes(nested_item, path)
            else:
                item.add_route(
                    self.route_input_rfs_list, False, True, False, kwargs={"path": path}
                )

    def thomas_list(self, item, path, depth=0, modified_since=None):
        logger.info(f"Listing path {path!r} with depth {depth}")
        item_id = item.id
        headers = self.get_headers()
        if modified_since:
            headers["If-Modified-Since"] = modified_since.strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )

        r = requests.get(
            urljoin(self.config["url"].strip("/") + "/", path),
            params={"depth": depth},
            headers=headers,
        )

        if r.status_code == 200:
            item = Item.unserialize(r.json(), router=router)
            item.id = item_id
            self.add_routes(item, path, skip=True)
            return item
        elif r.status_code == 304:
            raise NotModifiedException()
        elif r.status_code == 404 or r.status_code == 403:
            raise PathNotFoundException()
        else:
            logger.warning(
                f"Unknown status code {r.status_code} while listing {self.name}/{path}"
            )

    def thomas_stream(self, item, path):
        logger.info(f"Trying to stream {path!r}")
        return RemoteFilesystemStreamer(self, path)

    def stream(self, path):
        logger.info(f"Trying to stream {path!r}")
        headers = self.get_headers()
        r = requests.post(
            urljoin(self.config["url"].strip("/") + "/", path), headers=headers
        )

        if r.status_code != 200:
            raise PathNotFoundException()

        return Stream.unserialize(r.json())
