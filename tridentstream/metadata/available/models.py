import logging

from django.db import models

from ...bases.listing.models import ListingItem
from ...bases.metadata.models import BaseListingItemRelation

logger = logging.getLogger(__name__)


class Availability(models.Model):
    app = models.CharField(max_length=50)
    identifier = models.CharField(max_length=250)

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("app", "identifier"),)

    @property
    def metadata_name(self):
        return "available"


class ListingItemRelation(BaseListingItemRelation):
    metadata = models.ForeignKey(Availability, on_delete=models.CASCADE)


class ListingItemAvailability(models.Model):
    app = models.CharField(max_length=50)
    identifier = models.CharField(max_length=250)

    listingitem = models.ForeignKey(ListingItem, on_delete=models.CASCADE)

    class Meta:
        indexes = [models.Index(fields=["app", "identifier"])]
