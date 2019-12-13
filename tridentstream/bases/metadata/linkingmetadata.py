import logging
from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from unplugged import Schema

from ...plugins import MetadataHandlerPlugin
from .mixins import (
    GetMetadataStatsMixin,
    ListingItemRelinkingMixin,
    PopulateMetadataJSONAPIMixin,
    ResetFailedMixin,
)

logger = logging.getLogger(__name__)


class LinkingMetadataHandlerPlugin(
    ListingItemRelinkingMixin,
    PopulateMetadataJSONAPIMixin,
    GetMetadataStatsMixin,
    ResetFailedMixin,
    MetadataHandlerPlugin,
):
    linkable = False

    metadata_link_model = None
    user_field = None
    config_schema = Schema

    def link_metadata_listingitems(self, listing_build, fetch_metadata=True):
        listing_item_root = listing_build.listing_item_root
        linkable_metadata = listing_build.linkable_metadata

        metadata_mapping = defaultdict(set)
        for p in linkable_metadata:
            base_qs = p.listing_item_relation_model.objects.filter(
                Q(listingitem__parent=listing_item_root)
                | Q(listingitem=listing_item_root)
            )
            items_to_link = self.metadata_link_model.objects.filter(
                content_type=ContentType.objects.get_for_model(p.model),
                object_id__in=base_qs.values("metadata_id"),
            )

            local_metadata_mapping = defaultdict(list)
            if self.user_field:
                for pk, object_id, user_id in items_to_link.values_list(
                    "pk", "object_id", self.user_field
                ):
                    local_metadata_mapping[object_id].append((pk, user_id))
            else:
                for pk, object_id in items_to_link.values_list("pk", "object_id"):
                    local_metadata_mapping[object_id].append((pk, None))

            for listingitem_id, metadata_id in base_qs.filter(
                metadata_id__in=items_to_link.values("object_id")
            ).values_list("listingitem_id", "metadata_id"):
                for item in local_metadata_mapping[metadata_id]:
                    metadata_mapping[listingitem_id].add(item)

        self.listingitem_relinking(listing_item_root, metadata_mapping)

    def schedule_update(self):
        pass

    def unload(self):
        pass
