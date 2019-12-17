import logging

from django.db import models

from ...bases.metadata.models import (
    BaseListingItemRelation,
    BaseMetadata,
    BaseMetadataResolutionLink,
)

logger = logging.getLogger(__name__)


class Language(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Country(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Person(models.Model):
    identifier = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Metadata(BaseMetadata):
    rating = models.DecimalField(null=True, decimal_places=2, max_digits=3)
    votes = models.IntegerField(null=True)
    duration = models.IntegerField(null=True)
    year = models.IntegerField(null=True)

    plot = models.TextField(null=True)
    synopsis = models.TextField(null=True)

    actors = models.ManyToManyField(Person, related_name="actors")
    writers = models.ManyToManyField(Person, related_name="writers")
    directors = models.ManyToManyField(Person, related_name="directors")

    genres = models.ManyToManyField(Genre)

    languages = models.ManyToManyField(Language)
    primary_language = models.ForeignKey(
        Language,
        null=True,
        related_name="primary_language",
        on_delete=models.deletion.CASCADE,
    )

    countries = models.ManyToManyField(Country)

    @property
    def metadata_name(self):
        return "imdb"

    def populate(self, config):
        from imdbparser import IMDb

        image_cache = config["image_cache"]

        imdb = IMDb()
        movie = imdb.get_movie(self.identifier)
        movie.fetch()

        self.actors.clear()
        self.writers.clear()
        self.directors.clear()
        self.genres.clear()
        self.languages.clear()
        self.countries.clear()

        AlternativeTitle.objects.filter(metadata=self).delete()

        self.title = movie.title
        self.rating = movie.rating
        self.votes = movie.votes
        self.duration = movie.duration
        self.year = movie.year
        self.plot = movie.plot
        self.synopsis = movie.description

        if movie.cover:
            self.cover = movie.cover
            image_cache.get_image_path(self.cover)

        person_target_map = [
            (movie.actors, self.actors),
            (movie.writers, self.writers),
            (movie.directors, self.directors),
        ]

        for persons, target in person_target_map:
            for p in persons:
                person, _ = Person.objects.get_or_create(
                    identifier=p.imdb_id, defaults={"name": p.name}
                )
                if p.name != person.name:
                    person.name = p.name
                    person.save()

                target.add(person)

        for genre in movie.genres:
            genre, _ = Genre.objects.get_or_create(name=genre)
            self.genres.add(genre)

        primary_language = None
        for language in movie.languages:
            language, _ = Language.objects.get_or_create(name=language)
            if not primary_language:
                primary_language = language
            self.languages.add(language)

        self.primary_language = primary_language

        for country in movie.countries:
            country, _ = Country.objects.get_or_create(name=country)
            self.countries.add(country)

        for alt_title in movie.alternative_titles:
            if alt_title:
                AlternativeTitle.objects.create(title=alt_title, metadata=self)


class AlternativeTitle(models.Model):
    title = models.CharField(max_length=500)
    metadata = models.ForeignKey(Metadata, on_delete=models.deletion.CASCADE)


class ListingItemRelation(BaseListingItemRelation):
    metadata = models.ForeignKey(
        Metadata, db_index=True, on_delete=models.deletion.CASCADE
    )


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

        search_strings = self.build_search_strings({})
        if not search_strings:
            return

        from imdbparser import IMDb

        imdb = IMDb()

        for title, year in set(search_strings):
            logger.debug(f"Resolving using title:{title} year:{year}")

            if self.search_resolve == "tv":
                metadata = imdb.resolve_tv_show(title, year)
            elif self.search_resolve == "movie":
                metadata = imdb.resolve_movie(title, year)
            else:
                logger.warning(f"Unknown search resolve {self.search_resolve}")
                continue

            if not metadata:
                continue

            return metadata.imdb_id
