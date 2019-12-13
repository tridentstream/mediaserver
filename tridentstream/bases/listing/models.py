from urllib.parse import quote

from django.db import models
from jsonfield import JSONField
from thomas import Item, router


class ListingItem(models.Model):
    """An item in a listing view"""

    app = models.CharField(max_length=30)
    name = models.CharField(max_length=200, db_index=True, default="")
    path = models.CharField(max_length=500)  # absolute path
    parent = models.ForeignKey(
        "self", null=True, db_index=True, on_delete=models.deletion.CASCADE
    )
    datetime = models.DateTimeField()
    config = JSONField(default=dict)
    attributes = JSONField(default=dict)

    LISTINGITEM_TYPE_FILE = "file"
    LISTINGITEM_TYPE_FOLDER = "folder"
    LISTINGITEM_TYPES = (
        (LISTINGITEM_TYPE_FILE, "File"),
        (LISTINGITEM_TYPE_FOLDER, "Folder"),
    )
    item_type = models.CharField(max_length=10, choices=LISTINGITEM_TYPES)
    is_root = models.BooleanField(default=False)
    last_updated = models.DateTimeField(null=True)
    last_checked = models.DateTimeField(null=True)

    class Meta:
        ordering = ("datetime",)
        unique_together = (("app", "path"),)

    def __str__(self):
        return self.path

    def get_absolute_url(self):
        url = "/%s/%s" % (self.app, self.path)
        return quote(url.encode("utf-8"))

    def get_name(self):
        return self.path.split("/")[-1]

    def get_full_path(self):
        if self.path:
            return "%s/%s" % (self.app, self.path)
        else:
            return self.app

    def get_local_path(self):
        return "/".join(self.path.split("/")[1:])

    def get_metadata(self, metadata):
        related = getattr(self, "metadata_%s" % (metadata,), None)
        if not related:
            return []

        return [m.metadata for m in related.all().select_related("metadata")]

    def get_all_related_metadata(self):
        metadatas = []

        for ro in self._meta.related_objects:
            if not ro.name.startswith("metadata_"):
                continue

            related = getattr(self, ro.name, None)
            metadatas.extend(
                [m.metadata for m in related.all().select_related("metadata")]
            )

        return metadatas

    def get_original_item(self):
        return Item.unserialize(self.config["original_item"], router=router)
