import rest_framework_filters as filters

from .models import ListingItemRelation


class MetadataFilter(filters.FilterSet):
    id = filters.AllLookupsFilter(
        field_name="metadata__identifier", name="metadata__identifier"
    )
    title = filters.AllLookupsFilter(
        field_name="metadata__title", name="metadata__title"
    )
    genre = filters.AllLookupsFilter(
        field_name="metadata__genres__name", name="metadata__genres__name"
    )  # choices
    rating = filters.AllLookupsFilter(
        field_name="metadata__rating", name="metadata__rating"
    )
    votes = filters.AllLookupsFilter(
        field_name="metadata__votes", name="metadata__votes"
    )
    duration = filters.AllLookupsFilter(
        field_name="metadata__duration", name="metadata__duration"
    )
    episodes = filters.AllLookupsFilter(
        field_name="metadata__episodes", name="metadata__episodes"
    )
    season_year = filters.AllLookupsFilter(
        field_name="metadata__season__year", name="metadata__season__year"
    )  # choices
    season_season = filters.AllLookupsFilter(
        field_name="metadata__season__season", name="metadata__season__season"
    )  # choices
    tv_rating = filters.AllLookupsFilter(
        field_name="metadata__tv_rating__name", name="metadata__tv_rating__name"
    )  # choices
    anime_type = filters.AllLookupsFilter(
        field_name="metadata__anime_type__name", name="metadata__anime_type__name"
    )  # choices

    class Meta:
        model = ListingItemRelation
        fields = []
        include_related = [
            "genre",
            "season_year",
            "season_season",
            "tv_rating",
            "anime_type",
        ]
        order_by = ["title"]
