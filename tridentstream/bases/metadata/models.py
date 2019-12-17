from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from jsonfield import JSONField
from unplugged.models import Plugin

from ..listing.models import ListingItem

COVERS_FOLDER = "covers"


class BaseUpdatable(models.Model):
    priority = models.SmallIntegerField(default=20)

    UPDATE_STATUS_DO_NOT_FETCH = (
        "do-not-fetch"  # be able to link, but not actually needed right now
    )
    UPDATE_STATUS_PENDING = "pending"
    UPDATE_STATUS_UPDATING = "updating"
    UPDATE_STATUS_FAILED = "failed"
    UPDATE_STATUS_SUCCESS = "success"

    UPDATE_STATUS_CHOICES = (
        (UPDATE_STATUS_DO_NOT_FETCH, "Do not fetch"),
        (UPDATE_STATUS_PENDING, "Pending"),
        (UPDATE_STATUS_UPDATING, "Updating"),
        (UPDATE_STATUS_FAILED, "Failed"),
        (UPDATE_STATUS_SUCCESS, "Success"),
    )
    last_update_status = models.CharField(
        max_length=20, choices=UPDATE_STATUS_CHOICES, default="pending", db_index=True
    )

    last_updated = models.DateTimeField(null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class BaseMetadata(BaseUpdatable):
    """Used by remote metadata downloaders as base"""

    identifier = models.CharField(max_length=255, unique=True)
    populated = models.BooleanField(default=False)

    plugin = models.ForeignKey(
        Plugin,
        null=True,
        blank=True,
        related_name="metadata_%(app_label)s",
        on_delete=models.deletion.CASCADE,
    )

    title = models.CharField(max_length=300, null=True)
    cover = models.URLField(null=True, max_length=1000)

    prefetch_related_denormalized = JSONField(blank=True, null=True)

    @property
    def metadata_name(self):
        raise NotImplementedError

    def get_absolute_url(self):
        if not hasattr(self, "__config__"):
            return

        if not self.__config__.get("metadata_server"):
            return

        metadata_server = self.__config__["metadata_server"]
        return reverse(
            f"unplugged:{metadata_server.name}:metadata",
            kwargs={
                "metadata_handler": self.metadata_name,
                "identifier": self.identifier,
            },
        )

    def populate(self, config):
        raise NotImplementedError

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.identifier} in {self.__class__.__name__}"


class BaseListingItemRelation(models.Model):
    listingitem = models.ForeignKey(
        ListingItem,
        related_name="%(app_label)s",
        db_index=True,
        on_delete=models.deletion.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="%(app_label)s",
        null=True,
        on_delete=models.deletion.CASCADE,
    )

    class Meta:
        abstract = True
        unique_together = (("listingitem", "metadata", "user"),)


class BaseMetadataLink(models.Model):
    """Used to link with metadata and add an additional field"""

    content_type = models.ForeignKey(ContentType, on_delete=models.deletion.CASCADE)
    object_id = models.PositiveIntegerField()
    metadata = GenericForeignKey()

    class Meta:
        abstract = True
        unique_together = (("content_type", "object_id"),)


class BaseMetadataResolutionLink(BaseUpdatable):
    """Used for auto-resolving a name to metadata when identifier is missing"""

    name = models.CharField(max_length=255)
    search_resolve = models.CharField(max_length=30)

    listingitems = models.ManyToManyField(
        ListingItem, related_name="resolution_%(app_label)s"
    )
    plugin = models.ForeignKey(
        Plugin,
        null=True,
        blank=True,
        related_name="resolution_%(app_label)s",
        on_delete=models.deletion.CASCADE,
    )

    class Meta:
        abstract = True
        unique_together = (("name", "search_resolve"),)

    def __str__(self):
        return "%s in %s" % (self.name, self.__class__.__name__)

    def build_search_strings(self, permutations):
        search_strings = []
        for listingitem in self.listingitems.all():  # TODO: something is wrong here
            iteminfos = listingitem.get_metadata("iteminfo") or []
            for iteminfo in iteminfos:
                title = iteminfo.title
                if title:
                    search_strings.append((title, iteminfo.year))

            if not search_strings:
                name_search_string = listingitem.name.strip()
                if " " not in name_search_string:
                    name_search_string = name_search_string.replace(".", " ").replace(
                        "_", " "
                    )

                search_strings.append((name_search_string, None))

            first_search_string = search_strings[0]
            for src, dst in permutations.items():
                search_strings.append(
                    (first_search_string[0].replace(src, dst), first_search_string[1])
                )

        seen = set()
        return [x for x in search_strings if not (x in seen or seen.add(x))]

    def populate(self, config):
        raise NotImplementedError
