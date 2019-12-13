from django.conf import settings
from unplugged import RelatedPluginField, Schema, ServicePlugin, fields

from ...plugins import HistoryPlugin, IndexerPlugin, MetadataHandlerPlugin, TagPlugin


class ListingLevelSchema(Schema):
    depth = fields.Integer(required=True)
    listing_depth = fields.Integer(required=True)
    metadata_handlers = fields.List(
        RelatedPluginField(plugin_type=MetadataHandlerPlugin), many=True, default=list
    )
    indexer = RelatedPluginField(plugin_type=IndexerPlugin, required=False)
    content_type = fields.String(
        enum=settings.TRIDENTSTREAM_CONTENT_TYPES,
        enum_names=settings.TRIDENTSTREAM_CONTENT_TYPES_NAMES,
        default="",
    )
    tags = fields.List(
        RelatedPluginField(plugin_type=TagPlugin), many=True, default=list
    )
    background_recheck = fields.Boolean(default=False)
    default_ordering = fields.String(default="")


class ListingSchema(Schema):
    name = fields.String(required=True)
    display_name = fields.String(default="", ui_schema={"ui:title": "Name"})
    levels = fields.Nested(ListingLevelSchema, many=True, default=list)
    histories = fields.List(
        RelatedPluginField(plugin_type=HistoryPlugin), many=True, default=list
    )
    rebuild_automatically = fields.Boolean(default=True)


class BaseSchema(Schema):
    display_name = fields.String(
        default="", description="Display Name", ui_schema={"ui:title": "Name"}
    )
    player_service = RelatedPluginField(plugin_type=ServicePlugin, traits=["player"])
