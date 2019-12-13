import logging
import re

from django.utils.text import slugify
from unplugged import RelatedPluginField, Schema, fields

from ...bases.metadata.remotemetadata import (
    BaseMetadataSerializer,
    RemoteMetadataHandlerPlugin,
)
from .filters import MetadataFilter
from .models import ListingItemRelation, Metadata
from .plugins import ItemInfoPlugin

logger = logging.getLogger(__name__)


class ItemInfoTypeSchema(Schema):
    item_info = RelatedPluginField(plugin_type=ItemInfoPlugin)
    priority = fields.Integer(default=10)


class ItemInfoSchema(Schema):
    item_infos = fields.Nested(ItemInfoTypeSchema, many=True)


class ItemInfoMetadataSerializer(BaseMetadataSerializer):
    class Meta(BaseMetadataSerializer.Meta):
        model = Metadata
        exclude = BaseMetadataSerializer.Meta.exclude + ("cover", "name")


class ItemInfoMetadataHandlerPlugin(RemoteMetadataHandlerPlugin):
    plugin_name = "iteminfo"
    serializer = ItemInfoMetadataSerializer
    model = Metadata
    filter = MetadataFilter
    listing_item_relation_model = ListingItemRelation

    config_schema = ItemInfoSchema
    metadata_embed_method = "relate"
    prepopulate_metadata = True
    priority = 10

    def get_identifier(self, item):
        return slugify(re.sub(r"[-_\. ]+", "-", item.id))
