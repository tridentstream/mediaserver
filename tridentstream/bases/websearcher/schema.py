from unplugged import RelatedPluginField, Schema, fields

from ...plugins import (
    BittorrentClientPlugin,
    MagnetResolverPlugin,
    MetadataHandlerPlugin,
)


class URLSearcherSchema(Schema):
    availability = RelatedPluginField(
        plugin_type=MetadataHandlerPlugin, traits=["availability"]
    )
    priority = fields.Integer(default=10, ui_schema={"ui:title": "Priority"})


class TorrentSearcherSchema(URLSearcherSchema):
    bittorrent_client = RelatedPluginField(
        plugin_type=BittorrentClientPlugin,
        required=True,
        ui_schema={"ui:title": "Torrent client"},
    )
    daily_download_count_cap = fields.Integer(
        default=12, ui_schema={"ui:title": "Daily download cap"}
    )
    magnet_resolver = RelatedPluginField(
        plugin_type=MagnetResolverPlugin,
        required=False,
        ui_schema={"ui:title": "Resolve magnet links"},
    )


class LoginTorrentSearcherSchema(TorrentSearcherSchema):
    username = fields.String(required=True, ui_schema={"ui:title": "Username"})
    password = fields.String(
        required=True, ui_schema={"ui:widget": "password", "ui:title": "Password"}
    )
