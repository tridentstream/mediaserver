import logging

from django.db import models
from jsonfield import JSONField

from ...bases.metadata.models import BaseListingItemRelation

logger = logging.getLogger(__name__)


class EmbeddedInfo(models.Model):
    path = models.CharField(max_length=500)
    query_key = models.CharField(max_length=50)

    index = models.IntegerField(null=True)

    title = models.CharField(max_length=300, null=True)
    cover = models.URLField(null=True, max_length=1000)
    year = models.IntegerField(null=True)
    plot = models.TextField(null=True)
    duration = models.IntegerField(null=True)
    rating = models.DecimalField(null=True, decimal_places=2, max_digits=3)

    genres = JSONField(default=[])
    primary_language = models.CharField(max_length=50, null=True)

    file_source = models.CharField(null=True, max_length=100)
    group = models.CharField(max_length=300, null=True)

    mediainfo_resolution = models.CharField(null=True, max_length=100)
    mediainfo_codec = models.CharField(null=True, max_length=100)
    mediainfo_container = models.CharField(null=True, max_length=100)
    mediainfo_source = models.CharField(null=True, max_length=100)
    mediainfo_scene = models.BooleanField(default=False)
    mediainfo_dual_audio = models.BooleanField(default=False)
    mediainfo_audio = models.CharField(null=True, max_length=100)
    mediainfo_best = models.BooleanField(
        default=False
    )  # probably the best choice if you have to choose

    bittorrent_seeders = models.IntegerField(null=True)
    bittorrent_leechers = models.IntegerField(null=True)
    bittorrent_snatched = models.IntegerField(null=True)

    episodeinfo_episode_type = models.CharField(max_length=200, blank=True, null=True)

    episodeinfo_season = models.IntegerField(blank=True, null=True)
    episodeinfo_episode = models.IntegerField(blank=True, null=True)
    episodeinfo_year = models.IntegerField(blank=True, null=True)
    episodeinfo_month = models.IntegerField(blank=True, null=True)
    episodeinfo_day = models.IntegerField(blank=True, null=True)
    episodeinfo_sub_title = models.CharField(max_length=150, blank=True, null=True)

    datetime = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("query_key", "path"),)

    @property
    def metadata_name(self):
        return "embedded"

    @property
    def identifier(self):
        return self.pk

    def set_available(self):
        if self.file_source == "bittorrent":
            self.bittorrent_available = True
            self.save()


class ListingItemRelation(BaseListingItemRelation):
    metadata = models.ForeignKey(EmbeddedInfo, on_delete=models.CASCADE)
