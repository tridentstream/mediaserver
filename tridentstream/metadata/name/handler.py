import logging

from rest_framework import serializers
from unplugged import Schema

from ...bases.metadata.remotemetadata import RemoteMetadataHandlerPlugin
from .models import ListingItemRelation, Metadata

logger = logging.getLogger(__name__)


class NameMetadataHandlerPlugin(RemoteMetadataHandlerPlugin):
    plugin_name = "name"
    serializer = serializers.Serializer
    model = Metadata
    listing_item_relation_model = ListingItemRelation

    config_schema = Schema
    metadata_embed_method = "skip"
    prepopulate_metadata = False
    priority = 50

    def get_identifier(self, item):
        return item.id.lower()
