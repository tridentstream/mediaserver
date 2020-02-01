import logging
import re
from datetime import date

from django.db import models

from ...bases.metadata.models import (
    BaseListingItemRelation,
    BaseMetadata,
    BaseMetadataResolutionLink,
)

logger = logging.getLogger(__name__)

THETVDB_APIKEY = "E86EAF8A9978C847"


class Language(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Network(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class ContentRating(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Status(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Metadata(BaseMetadata):
    imdb_id = models.IntegerField(null=True)

    rating = models.DecimalField(null=True, decimal_places=2, max_digits=4)
    votes = models.IntegerField(null=True)
    duration = models.IntegerField(null=True)
    year = models.IntegerField(null=True)
    synopsis = models.TextField(null=True)

    network = models.ForeignKey(Network, null=True, on_delete=models.deletion.CASCADE)
    content_rating = models.ForeignKey(
        ContentRating, null=True, on_delete=models.deletion.CASCADE
    )
    primary_language = models.ForeignKey(
        Language, null=True, on_delete=models.deletion.CASCADE
    )
    status = models.ForeignKey(Status, null=True, on_delete=models.deletion.CASCADE)

    genres = models.ManyToManyField(Genre)

    @property
    def metadata_name(self):
        return "thetvdb"

    def populate(self, config):
        import tvdb_api

        image_cache = config["image_cache"]

        tvdb = tvdb_api.Tvdb(apikey=THETVDB_APIKEY, banners=True)
        identifier = int(self.identifier)
        tv_show = tvdb[identifier]

        if tv_show.data["seriesName"] == "** 403: Series Not Permitted **":
            return

        self.genres.clear()

        self.network = None
        self.content_rating = None
        self.primary_language = None
        self.status = None
        self.imdb_id = None

        self.title = tv_show.data["seriesName"]
        self.rating = tv_show.data["siteRating"]
        self.votes = tv_show.data["siteRatingCount"]
        self.duration = tv_show.data["runtime"]

        if tv_show.data.get("imdb_id"):
            imdb_id = re.findall("tt(\d+)", tv_show.data["imdbId"])
            if imdb_id:
                self.imdb_id = imdb_id[0]

        self.year = None
        if tv_show.data.get("firstAired"):
            self.year = tv_show.data.get("firstAired").split("-")[0]

        self.synopsis = tv_show.data["overview"]

        if (
            tv_show.data.get("_banners", {}).get("poster", {}).get("raw")
        ):  # this is retarded design
            posters = sorted(
                tv_show.data["_banners"]["poster"]["raw"],
                key=lambda x: x["ratingsInfo"]["count"],
            )
            if posters:
                best_id = posters[-1]["id"]
                for _, v in tv_show.data["_banners"]["poster"].items():
                    if best_id in v:
                        self.cover = v[best_id]["_bannerpath"]
                        image_cache.get_image_path(self.cover)
                        break

        if tv_show.data.get("network"):
            self.network, _ = Network.objects.get_or_create(
                name=tv_show.data["network"]
            )

        if tv_show.data.get("rating"):
            self.content_rating, _ = ContentRating.objects.get_or_create(
                name=tv_show.data["rating"]
            )

        if tv_show.data.get("language"):
            self.primary_language, _ = Language.objects.get_or_create(
                name=tv_show.data["language"]
            )

        if tv_show.data.get("status"):
            self.status, _ = Status.objects.get_or_create(name=tv_show.data["status"])

        if tv_show.data["genre"]:
            for genre in tv_show.data["genre"]:
                genre, _ = Genre.objects.get_or_create(name=genre)
                self.genres.add(genre)

        Episode.objects.filter(metadata=self).delete()

        for season, episodes in tv_show.items():
            for episode, episode_info in episodes.items():
                e = Episode(metadata=self, season=season, episode=episode)
                e.title = episode_info["episodeName"]
                if episode_info.get("firstAired"):
                    e.air_date = date(
                        *[int(x) for x in episode_info["firstAired"].split("-")]
                    )

                e.save()


class Episode(models.Model):
    metadata = models.ForeignKey(Metadata, on_delete=models.deletion.CASCADE)
    season = models.IntegerField()
    episode = models.IntegerField()

    title = models.CharField(max_length=200, null=True)
    air_date = models.DateField(null=True)

    class Meta:
        unique_together = (("metadata", "season", "episode"),)


class ListingItemRelation(BaseListingItemRelation):
    metadata = models.ForeignKey(
        Metadata, db_index=True, on_delete=models.deletion.CASCADE
    )


THETVDB_LANGAUGE_REPLACEMENT_MAPPING = {
    "da": {"ae": "\xe6", "oe": "\xf8", "aa": "\xe5"}
}


class MetadataResolutionLink(BaseMetadataResolutionLink):
    metadata = models.ForeignKey(
        Metadata,
        db_index=True,
        null=True,
        blank=True,
        on_delete=models.deletion.CASCADE,
    )

    def resolve(self, config):
        logger.debug(f"Resolving using config {config!r}")

        language = config.get("search_language") or "en"

        search_strings = self.build_search_strings(
            THETVDB_LANGAUGE_REPLACEMENT_MAPPING.get(language, {})
        )
        if not search_strings:
            return

        import tvdb_api
        from tvdb_exceptions import tvdb_shownotfound

        tvdb = tvdb_api.Tvdb(apikey=THETVDB_APIKEY, language=language)
        for title, year in search_strings:
            try:
                tv_show = tvdb[title]
            except tvdb_shownotfound:
                continue

            return int(tv_show["id"])
