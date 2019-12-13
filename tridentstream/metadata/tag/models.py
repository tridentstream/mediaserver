import logging

from django.conf import settings
from django.db import models

from ...bases.metadata.models import BaseListingItemRelation, BaseMetadataLink

logger = logging.getLogger(__name__)


class Tag(BaseMetadataLink):
    """User who starred an item to follow it"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, db_index=True, on_delete=models.deletion.CASCADE
    )
    tag_name = models.CharField(max_length=30, db_index=True)
    created = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("user", "tag_name", "content_type", "object_id"),)

    @property
    def metadata_name(self):
        return "tag"

    @property
    def identifier(self):
        return self.pk


class ListingItemRelation(BaseListingItemRelation):
    metadata = models.ForeignKey(Tag, on_delete=models.deletion.CASCADE)
