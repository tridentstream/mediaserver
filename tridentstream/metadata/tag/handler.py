import logging

from rest_framework import serializers

from ...bases.metadata.linkingmetadata import LinkingMetadataHandlerPlugin
from .filters import MetadataFilter
from .models import ListingItemRelation, Tag

logger = logging.getLogger(__name__)


class TagSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField("get_metadata_identifier")
    type = serializers.SerializerMethodField("get_metadata_type")
    plugin_name = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ("id", "type", "plugin_name", "tag_name")

    def get_metadata_identifier(self, obj):
        return obj.metadata.identifier

    def get_metadata_type(self, obj):
        return "metadata_%s" % obj.metadata.metadata_name

    def get_plugin_name(self, obj):
        return "tag"


class TagMetadataHandlerPlugin(LinkingMetadataHandlerPlugin):
    plugin_name = "tag"
    priority = -10

    prefetch_related = ["metadata"]
    serializer = TagSerializer
    model = Tag
    listing_item_relation_model = ListingItemRelation
    metadata_link_model = Tag
    metadata_embed_method = "relate"
    filter = MetadataFilter
    user_field = "user"

    __traits__ = ["tag"]

    def get_metadata(self, request, identifier):
        pass
