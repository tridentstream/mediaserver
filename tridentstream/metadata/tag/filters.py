import rest_framework_filters as filters

from .models import ListingItemRelation


class MetadataFilter(filters.FilterSet):
    tag_name = filters.AllLookupsFilter(
        field_name="metadata__tag_name", name="metadata__tag_name"
    )
    created = filters.AllLookupsFilter(
        field_name="metadata__created", name="metadata__created"
    )

    class Meta:
        model = ListingItemRelation
        fields = []
        include_related = []
        order_by = ["created"]
        user_field = "metadata__user"
