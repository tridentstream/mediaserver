import logging

from django.db import models

from ...bases.metadata.models import BaseListingItemRelation, BaseMetadata

logger = logging.getLogger(__name__)


class Metadata(BaseMetadata):
    name = models.CharField(max_length=200)

    year = models.IntegerField(blank=True, null=True)
    season = models.IntegerField(blank=True, null=True)
    episode = models.IntegerField(blank=True, null=True)
    episode_type = models.CharField(max_length=200, blank=True, null=True)

    source = models.CharField(max_length=100, blank=True, null=True)
    fix_type = models.CharField(max_length=100, blank=True, null=True)

    @property
    def metadata_name(self):
        return "iteminfo"

    def populate(self, config):
        result = {}

        for item_info in sorted(config["item_infos"], key=lambda x: x["priority"]):
            item_info = item_info["item_info"]
            result.update(item_info.get_info(self.name))

        self.title = result.get("title")
        self.season = result.get("season")
        self.episode = result.get("episode")
        self.episode_type = result.get("episode_type")

        self.source = result.get("source")
        self.year = result.get("year")
        self.fix_type = result.get("fix_type")


class ListingItemRelation(BaseListingItemRelation):
    metadata = models.ForeignKey(
        Metadata, db_index=True, on_delete=models.deletion.CASCADE
    )
