from django.db import models
from jsonfield import JSONField

from ...plugins import SearchQuery


class SearchQueryCache(models.Model):
    query_hash = models.CharField(max_length=50, unique=True)
    query = JSONField()

    last_used = models.DateTimeField(auto_now=True)

    def get_search_query(self, filters):
        return SearchQuery(filters, self.query)
