from django.db import models
from jsonfield import JSONField


class ListingCache(models.Model):
    app = models.CharField(max_length=30)
    searcher_name = models.CharField(max_length=50)
    search_token = models.CharField(max_length=50)
    path = models.CharField(max_length=500, default="")
    listing = JSONField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("app", "searcher_name", "search_token", "path"),)
