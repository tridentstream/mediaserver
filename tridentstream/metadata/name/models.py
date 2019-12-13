import logging

from django.db import models

from ...bases.metadata.models import BaseListingItemRelation, BaseMetadata

logger = logging.getLogger(__name__)


class Metadata(BaseMetadata):
    name = models.CharField(max_length=255)

    @property
    def metadata_name(self):
        return "name"

    def populate(self, config):
        Metadata.objects.filter(last_update_status="pending").update(
            last_update_status="success"
        )


class ListingItemRelation(BaseListingItemRelation):
    metadata = models.ForeignKey(
        Metadata, db_index=True, on_delete=models.deletion.CASCADE
    )
