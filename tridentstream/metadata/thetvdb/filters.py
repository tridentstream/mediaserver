import rest_framework_filters as filters

from .models import ListingItemRelation


class MetadataFilter(filters.FilterSet):
    id = filters.AllLookupsFilter(
        field_name="metadata__identifier", name="metadata__identifier"
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
    year = filters.AllLookupsFilter(field_name="metadata__year", name="metadata__year")
    primary_language = filters.AllLookupsFilter(
        field_name="metadata__primary_language__name",
        name="metadata__primary_language__name",
    )  # choices
    content_rating = filters.AllLookupsFilter(
        field_name="metadata__content_rating__name",
        name="metadata__content_rating__name",
    )  # choices
    status = filters.AllLookupsFilter(
        field_name="metadata__status__name", name="metadata__status__name"
    )  # choices
    network = filters.AllLookupsFilter(
        field_name="metadata__network__name", name="metadata__network__name"
    )  # choices

    class Meta:
        model = ListingItemRelation
        order_by = ["rating", "votes", "duration", "year"]
        fields = []
        include_related = [
            "primary_language",
            "genre",
            "network",
            "content_rating",
            "status",
        ]
