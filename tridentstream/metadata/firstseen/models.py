import logging

from django.db import models

from ...bases.metadata.models import BaseListingItemRelation, BaseMetadataLink

logger = logging.getLogger(__name__)


class FirstSeen(BaseMetadataLink):
    """Metadata related to what the user saw"""

    datetime = models.DateTimeField(auto_now_add=True)

    @property
    def metadata_name(self):
        return "firstseen"

    @property
    def identifier(self):
        return self.metadata.identifier


class ListingItemRelation(BaseListingItemRelation):
    metadata = models.ForeignKey(FirstSeen, on_delete=models.deletion.CASCADE)
