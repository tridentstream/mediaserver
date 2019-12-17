import uuid

from django.conf import settings
from django.db import models
from jsonfield import JSONField

from ...bases.metadata.models import BaseListingItemRelation, BaseMetadataLink


class History(models.Model):
    app = models.CharField(max_length=30, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, db_index=True, on_delete=models.deletion.CASCADE
    )
    name = models.CharField(max_length=200, db_index=True)
    listingitem_app = models.CharField(max_length=30, null=True)
    listingitem_path = models.CharField(max_length=500, null=True)
    last_watched = models.DateTimeField()
    created = models.DateTimeField(auto_now_add=True)

    @property
    def identifier(self):
        return self.pk

    class Meta:
        ordering = ["-last_watched"]

    def __str__(self):
        return f"{self.user!r} watched {self.name} at {self.last_watched}"


class HistoryMetadata(BaseMetadataLink):
    """Metadata related to what the user saw"""

    history = models.ForeignKey(History, on_delete=models.deletion.CASCADE)
    primary_metadata = models.BooleanField(default=False)

    class Meta:
        unique_together = (("content_type", "object_id", "history"),)


class ViewState(models.Model):
    identifier = models.UUIDField(default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.deletion.CASCADE
    )
    history = models.ForeignKey(History, on_delete=models.deletion.CASCADE)
    values = JSONField(default=dict, blank=True)

    last_update = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("identifier", "user"),)


class ListingItemRelation(BaseListingItemRelation):
    metadata = models.ForeignKey(
        HistoryMetadata, db_index=True, on_delete=models.deletion.CASCADE
    )
