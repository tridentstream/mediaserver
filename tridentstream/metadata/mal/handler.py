import logging

from malparser import MAL  # NOQA
from rest_framework import serializers

from ...bases.metadata.remotemetadata import (
    MetadataSerializer,
    RemoteMetadataHandlerPlugin,
)
from .filters import MetadataFilter
from .models import ListingItemRelation, Metadata

logger = logging.getLogger(__name__)


class MALSeasonSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    season = serializers.CharField()


class MALMetadataSerializer(MetadataSerializer):
    anime_type = serializers.StringRelatedField()
    tv_rating = serializers.StringRelatedField()
    genres = serializers.StringRelatedField(many=True)
    season = MALSeasonSerializer()
    year = serializers.SerializerMethodField()

    class Meta(MetadataSerializer.Meta):
        model = Metadata

    def get_year(self, obj):
        if obj.season and obj.season.year:
            return obj.season.year


class MALMetadataHandlerPlugin(RemoteMetadataHandlerPlugin):
    plugin_name = "mal"
    select_related = ["season", "tv_rating", "anime_type"]
    prefetch_related = ["genres", "alternativetitle_set", "related"]
    serializer = MALMetadataSerializer
    model = Metadata
    filter = MetadataFilter
    listing_item_relation_model = ListingItemRelation
    fulltext_fields = ["title"]

    __traits__ = ["primary_metadata", "metadata_anime"]
