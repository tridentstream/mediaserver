import logging

from django.db import models

from ...bases.metadata.models import BaseListingItemRelation, BaseMetadata

logger = logging.getLogger(__name__)


class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)
    identifier = models.IntegerField(unique=True)

    def __str__(self):
        return self.name


class Season(models.Model):
    SEASON_SUMMER = "summer"
    SEASON_WINTER = "winter"
    SEASON_SPRING = "spring"
    SEASON_FALL = "fall"
    SEASON_CHOICES = (
        (SEASON_SUMMER, "Summer"),
        (SEASON_WINTER, "Winter"),
        (SEASON_SPRING, "Spring"),
        (SEASON_FALL, "Fall"),
    )

    year = models.IntegerField()
    season = models.CharField(max_length=20, choices=SEASON_CHOICES)

    class Meta:
        unique_together = (("year", "season"),)


class TVRating(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Type(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Metadata(BaseMetadata):
    genres = models.ManyToManyField(Genre)

    rating = models.DecimalField(null=True, decimal_places=2, max_digits=3)
    votes = models.IntegerField(null=True)
    duration = models.IntegerField(null=True)
    episodes = models.IntegerField(null=True)

    season = models.ForeignKey(Season, null=True, on_delete=models.deletion.CASCADE)
    tv_rating = models.ForeignKey(
        TVRating, null=True, on_delete=models.deletion.CASCADE
    )
    anime_type = models.ForeignKey(Type, null=True, on_delete=models.deletion.CASCADE)

    aired_start = models.DateField(null=True)
    aired_end = models.DateField(null=True)

    plot = models.TextField(null=True)

    @property
    def metadata_name(self):
        return "mal"

    def populate(self, config):
        from malparser import MAL
        from malparser.anime import Anime

        image_cache = config["image_cache"]

        mal = MAL()
        anime = mal.get_anime(self.identifier)
        anime.fetch()

        # cleanup if it is an update
        self.genres.clear()
        AlternativeTitle.objects.filter(metadata=self).delete()
        Related.objects.filter(from_metadata=self).delete()

        # populate
        self.title = anime.title
        self.rating = anime.statistics["Score"]
        self.votes = anime.statistics["Votes"]
        self.duration = anime.info["Duration"]
        self.episodes = anime.info["Episodes"]
        self.aired_start = anime.aired.get("Aired_start", None)
        self.aired_end = anime.aired.get("Aired_end", None)
        self.plot = anime.synopsis

        season = anime.aired.get("Season", None)
        if season:
            season, created = Season.objects.get_or_create(
                season=season[0].lower(), year=season[1]
            )
        self.season = season

        tv_rating, created = TVRating.objects.get_or_create(name=anime.info["Rating"])
        self.tv_rating = tv_rating

        anime_type, created = Type.objects.get_or_create(name=anime.info["Type"])
        self.anime_type = anime_type

        for g in anime.info["Genres"]:
            genre, created = Genre.objects.get_or_create(
                identifier=g["id"], defaults={"name": g["name"]}
            )
            if not created and genre.name != g["name"]:
                genre.name = g["name"]
                genre.save()
            self.genres.add(genre)

        self.cover = anime.cover
        image_cache.get_image_path(self.cover)

        for language, titles in anime.alternative_titles.items():
            for title in titles:
                AlternativeTitle.objects.create(
                    title=title, language=language, metadata=self
                )

        for relation_type, related in anime.related.items():
            for item in related:
                if not isinstance(item, Anime):
                    continue

                try:
                    to_metadata = Metadata.objects.get(identifier=item.mal_id)
                except Metadata.DoesNotExist:
                    to_metadata = None

                Related.objects.create(
                    from_metadata=self,
                    relation_type=relation_type,
                    to_metadata=to_metadata,
                    to_metadata_identifier=item.mal_id,
                )


class AlternativeTitle(models.Model):
    title = models.CharField(max_length=500)
    language = models.CharField(max_length=100)
    metadata = models.ForeignKey(Metadata, on_delete=models.deletion.CASCADE)


class Related(models.Model):
    from_metadata = models.ForeignKey(
        Metadata, related_name="related", on_delete=models.deletion.CASCADE
    )
    relation_type = models.CharField(max_length=50)
    to_metadata = models.ForeignKey(
        Metadata,
        null=True,
        related_name="reverse_related",
        on_delete=models.deletion.CASCADE,
    )
    to_metadata_identifier = models.CharField(max_length=100)


class ListingItemRelation(BaseListingItemRelation):
    metadata = models.ForeignKey(
        Metadata, db_index=True, on_delete=models.deletion.CASCADE
    )
