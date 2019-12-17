import logging
from threading import Lock

from imdbparser import IMDb  # NOQA
from rest_framework import serializers
from unplugged import fields

from ...bases.metadata.remotemetadata import (
    MetadataSerializer,
    RemoteMetadataHandlerPlugin,
)
from ...bases.metadata.schema import MetadataSchema
from .filters import MetadataFilter
from .models import ListingItemRelation, Metadata, MetadataResolutionLink

logger = logging.getLogger(__name__)


class IMDBMetadataSchema(MetadataSchema):
    search_resolve = fields.String(
        enum=["tv", "movie"], enum_names=["TV", "Movie"]
    )  # choices: tv, movies


class IMDBMetadataSerializer(MetadataSerializer):
    primary_language = serializers.StringRelatedField()
    genres = serializers.StringRelatedField(many=True)
    languages = serializers.StringRelatedField(many=True)
    countries = serializers.StringRelatedField(many=True)
    actors = serializers.StringRelatedField(many=True)
    writers = serializers.StringRelatedField(many=True)
    directors = serializers.StringRelatedField(many=True)

    class Meta(MetadataSerializer.Meta):
        model = Metadata


class IMDBMetadataHandlerPlugin(RemoteMetadataHandlerPlugin):
    plugin_name = "imdb"
    select_related = ["primary_language"]
    prefetch_related = [
        "genres",
        "alternativetitle_set",
        "languages",
        "countries",
        "actors",
        "writers",
        "directors",
    ]
    currently_updating_lock = Lock()
    serializer = IMDBMetadataSerializer
    model = Metadata
    filter = MetadataFilter
    listing_item_relation_model = ListingItemRelation
    metadata_resolution_link_model = MetadataResolutionLink
    fulltext_fields = ["title"]

    config_schema = IMDBMetadataSchema

    @property
    def __traits__(self):
        traits = ["primary_metadata"]
        if self.config.get("search_resolve"):
            traits.append(f"metadata_{self.config['search_resolve']}")
        return traits
