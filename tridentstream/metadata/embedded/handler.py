import logging
import uuid

from rest_framework import serializers

from ...bases.metadata.mixins import CoverSerializerMixin, PopulateMetadataJSONAPIMixin
from ...bases.metadata.schema import MetadataSchema
from ...plugins import MetadataHandlerPlugin
from .filters import EmbeddedInfoFilter
from .models import EmbeddedInfo, ListingItemRelation

logger = logging.getLogger(__name__)


class EmbeddedInfoSerializer(CoverSerializerMixin, serializers.ModelSerializer):
    id = serializers.SerializerMethodField("get_metadata_identifier")
    type = serializers.SerializerMethodField("get_metadata_type")
    populated = serializers.SerializerMethodField()
    genres = serializers.SerializerMethodField()

    cover = serializers.SerializerMethodField("get_cover_url")

    class Meta:
        model = EmbeddedInfo
        exclude = ("query_key", "path")

    def get_metadata_identifier(self, obj):
        return obj.identifier

    def get_metadata_type(self, obj):
        return "metadata_%s" % obj.metadata_name

    def get_populated(self, obj):
        return True

    def get_genres(self, obj):
        return obj.genres


class EmbeddedMetadataHandlerPlugin(
    PopulateMetadataJSONAPIMixin, MetadataHandlerPlugin
):
    plugin_name = "embedded"
    priority = -10
    config_schema = MetadataSchema
    linkable = False

    model = EmbeddedInfo
    filter = EmbeddedInfoFilter
    listing_item_relation_model = ListingItemRelation
    select_related = []
    prefetch_related = []
    serializer = EmbeddedInfoSerializer
    metadata_embed_method = "relate"  # choices: include, relate, embed

    data_mapping = {
        "metadata": {
            "title": "title",
            "cover": "cover",
            "year": "year",
            "source": "file_source",
            "plot": "plot",
            "genres": "genres",
            "primary_language": "primary_language",
            "rating": "rating",
            "duration": "duration",
            "available": "available",
            "group": "release_group",
        },
        "metadata:bittorrent": {
            "seeders": "bittorrent_seeders",
            "leechers": "bittorrent_leechers",
            "snatched": "bittorrent_snatched",
        },
        "metadata:mediainfo": {
            "resolution": "mediainfo_resolution",
            "codec": "mediainfo_codec",
            "container": "mediainfo_container",
            "source": "mediainfo_source",
            "scene": "mediainfo_scene",
            "audio": "mediainfo_audio",
            "dual_audio": "mediainfo_dual_audio",
            "best": "mediainfo_best",
        },
        "metadata:episodeinfo": {
            "season": "episodeinfo_season",
            "episode": "episodeinfo_episode",
            "year": "episodeinfo_year",
            "month": "episodeinfo_month",
            "day": "episodeinfo_day",
            "episode_type": "episodeinfo_episode_type",
            "sub_title": "episodeinfo_sub_title",  # with a space to avoid confusing with subtitles... hopefully
        },
    }

    def get_metadata(self, request, identifier):
        """
        Not something this type of metadata can actually handle
        """
        pass

    def link_metadata_listingitems(self, listing_build, fetch_metadata=True):
        item_creation_mapping = listing_build.item_creation_mapping
        listingitem_mapping = listing_build.listingitem_mapping

        query_key = str(uuid.uuid4())
        ListingItemRelation.objects.filter(
            listingitem__in=listingitem_mapping.values()
        ).delete()
        objs = []
        for path, item in item_creation_mapping.items():
            if path not in listingitem_mapping:
                continue

            obj = self.model(path=path, query_key=query_key)

            for key, values in self.data_mapping.items():
                if key not in item:
                    continue

                data = item[key]
                if not isinstance(data, dict):
                    continue

                for source_key, target in values.items():
                    if source_key not in data:
                        continue
                    setattr(obj, target, data[source_key])

            if "metadata:index" in item:
                obj.index = item["metadata:index"]

            objs.append(obj)

        self.model.objects.bulk_create(objs)
        lirs = []
        for obj in self.model.objects.filter(query_key=query_key):
            lirs.append(
                self.listing_item_relation_model(
                    metadata=obj, listingitem=listingitem_mapping[obj.path]
                )
            )
        self.listing_item_relation_model.objects.bulk_create(lirs)
