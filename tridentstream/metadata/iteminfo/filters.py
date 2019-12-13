import rest_framework_filters as filters

from .models import ListingItemRelation


class MetadataFilter(filters.FilterSet):
    id = filters.AllLookupsFilter(
        field_name="metadata__identifier", name="metadata__identifier"
    )
    year = filters.AllLookupsFilter(field_name="metadata__year", name="metadata__year")
    season = filters.AllLookupsFilter(
        field_name="metadata__season", name="metadata__season"
    )
    episode = filters.AllLookupsFilter(
        field_name="metadata__episode", name="metadata__episode"
    )
    fix_type = filters.AllLookupsFilter(
        field_name="metadata__fix_type", name="metadata__fix_type"
    )

    class Meta:
        model = ListingItemRelation
        order_by = ["year", "season", "episode", "fix_type"]
        fields = []
