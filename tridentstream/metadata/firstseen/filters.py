import rest_framework_filters as filters
from django.db.models import Max, Min

from .models import ListingItemRelation


class MetadataFilter(filters.FilterSet):
    # metadata = filters.DateTimeFilter(name='firstseen__metadata')
    datetime = filters.DateTimeFilter(
        field_name="metadata__datetime", name="metadata__datetime"
    )

    class Meta:
        model = ListingItemRelation
        order_by = ["datetime"]
        order_by_aggregate = {"datetime": (Max, Min)}
        fields = []
