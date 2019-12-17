import logging

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from rest_framework import serializers

from ...bases.metadata.linkingmetadata import LinkingMetadataHandlerPlugin
from .filters import MetadataFilter
from .models import FirstSeen, ListingItemRelation

logger = logging.getLogger(__name__)


class FirstSeenSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField("get_metadata_identifier")
    type = serializers.SerializerMethodField("get_metadata_type")

    class Meta:
        model = FirstSeen
        fields = ("id", "type", "datetime")

    def get_metadata_identifier(self, obj):
        return obj.metadata.identifier

    def get_metadata_type(self, obj):
        return f"metadata_{obj.metadata.metadata_name}"


class FirstSeenMetadataHandlerPlugin(LinkingMetadataHandlerPlugin):
    plugin_name = "firstseen"
    priority = -10

    prefetch_related = ["metadata"]
    serializer = FirstSeenSerializer
    model = FirstSeen
    filter = MetadataFilter
    listing_item_relation_model = ListingItemRelation
    metadata_link_model = FirstSeen
    metadata_embed_method = "relate"

    def link_metadata_listingitems(self, listing_build, fetch_metadata=True):
        listing_item_root = listing_build.listing_item_root
        linkable_metadata = listing_build.linkable_metadata

        logger.info(f"Linking with metadata:{linkable_metadata!r}")
        for p in linkable_metadata:
            content_type = ContentType.objects.get_for_model(p.model)

            base_qs = p.listing_item_relation_model.objects.filter(
                Q(listingitem__parent=listing_item_root)
                | Q(listingitem=listing_item_root)
            )
            existing_items = self.metadata_link_model.objects.filter(
                content_type=content_type, object_id__in=base_qs.values("metadata_id")
            )
            missing_items = base_qs.exclude(
                metadata_id__in=existing_items.values("object_id")
            )

            create_objs = []
            for metadata_id in missing_items.values_list(
                "metadata_id", flat=True
            ).distinct():
                logger.debug(
                    f"Preparing to create object_id:{metadata_id!r}, content_type:{content_type!r}"
                )
                create_objs.append(
                    self.model(object_id=metadata_id, content_type=content_type)
                )
            self.model.objects.bulk_create(create_objs)
            logger.debug(f"Created {len(create_objs)} missing objects")

        return super(FirstSeenMetadataHandlerPlugin, self).link_metadata_listingitems(
            listing_build, fetch_metadata
        )

    def get_metadata(self, request, identifier):
        pass
