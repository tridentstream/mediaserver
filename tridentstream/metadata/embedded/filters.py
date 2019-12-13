import rest_framework_filters as filters

from .models import ListingItemRelation


class EmbeddedInfoFilter(filters.FilterSet):
    index = filters.DateTimeFilter(field_name="metadata__index", name="metadata__index")
    season = filters.AllLookupsFilter(
        field_name="metadata__episodeinfo_season", name="metadata__episodeinfo_season"
    )
    episode = filters.AllLookupsFilter(
        field_name="metadata__episodeinfo_episode", name="metadata__episodeinfo_episode"
    )

    class Meta:
        model = ListingItemRelation
        order_by = ["index", "season", "episode"]
        fields = []
