import logging
from threading import Lock

import tvdb_api  # NOQA
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


class TheTVDBMetadataSchema(MetadataSchema):
    search_resolve = fields.Boolean()
    search_language = fields.String(
        enum=["en", "da"], enum_names=["English", "Danish"]
    )  # choices, should also try to change language to local names
    episodic = fields.Boolean()  # Resolve to episodes


class TheTVDBMetadataSerializer(MetadataSerializer):
    primary_language = serializers.StringRelatedField()
    genres = serializers.StringRelatedField(many=True)

    class Meta(MetadataSerializer.Meta):
        model = Metadata


class TheTVDBMetadataHandlerPlugin(RemoteMetadataHandlerPlugin):
    plugin_name = "thetvdb"
    select_related = [
        "primary_language",
        "network",
        "content_rating",
        "primary_language",
        "status",
    ]
    prefetch_related = ["genres"]
    currently_updating_lock = Lock()
    serializer = TheTVDBMetadataSerializer
    model = Metadata
    filter = MetadataFilter
    listing_item_relation_model = ListingItemRelation
    metadata_resolution_link_model = MetadataResolutionLink
    fulltext_fields = ["title"]

    config_schema = TheTVDBMetadataSchema

    simpleadmin_templates = [
        {
            "template": {
                "search_resolve": True,
                "search_language": {"simpleAdminMethod": "userInput"},
            },
            "description": "Fetch metadata from TheTVDB",
            "id": "default",
            "update_method": "full",
            "display_name": "TheTVDB",
        }
    ]

    __traits__ = ["primary_metadata", "metadata_tv"]
