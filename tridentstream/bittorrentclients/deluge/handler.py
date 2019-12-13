import logging

import requests
from unplugged import Schema, fields
from unplugged.models import Log

from ...exceptions import PathNotFoundException
from ...plugins import BittorrentClientPlugin
from ...stream import Stream

logger = logging.getLogger(__name__)


class DelugeBittorrentClientSchema(Schema):
    url = fields.URL(required=True, require_tld=False, ui_schema={"ui:title": "URL"})
    username = fields.String(
        required=True, default="stream", ui_schema={"ui:title": "Username"}
    )
    password = fields.String(required=True, ui_schema={"ui:title": "Password"})
    label = fields.String(ui_schema={"ui:title": "Deluge Label"})

    class Meta:
        ui_schema = {"ui:order": ["url", "username", "password", "label"]}


class DelugeBittorrentClientPlugin(BittorrentClientPlugin):
    plugin_name = "deluge"
    simpleadmin_templates = True

    config_schema = DelugeBittorrentClientSchema

    def stream(self, info_hash, torrent_filelike_data, path=None):
        with Log.objects.start_chain(self, "TORRENT.ADD") as log:
            log.log(0, f"Queuing up torrent with infohash {info_hash}")

            url = self.config["url"]
            auth = (self.config["username"], self.config["password"])
            params = {
                "infohash": info_hash,
                "path": path or None,
                "wait_for_end_pieces": "1",
            }
            if self.config.get("label"):
                params["label"] = self.config["label"]

            r = requests.get(url, auth=auth, params=params).json()
            if r.get("status") != "success":
                r = requests.post(
                    url, auth=auth, params=params, data=torrent_filelike_data
                ).json()
                if r.get("status") != "success":
                    raise PathNotFoundException()

            return Stream(url=r["url"], playhandler="http", name=r["filename"])
