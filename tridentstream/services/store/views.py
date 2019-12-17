import json
import logging

from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from unplugged import CascadingPermission, JSONAPIObject, JSONAPIRoot

from ...bases.listing.views import BaseListingView
from ...utils import hash_string
from .models import SearchQueryCache

logger = logging.getLogger(__name__)


class StoreListView(BaseListingView):
    permission_classes = (CascadingPermission,)

    def get_config_view(self, request):
        root = JSONAPIRoot()
        logger.debug(
            f"Plugin {self.service!r}/{self.service.name} with full sections config {self.service.config['sections']!r}"
        )
        for section in self.service.config["sections"]:
            logger.debug(
                f"Making config view {section['name']} with settings {section!r}"
            )

            links = {
                "self": request.build_absolute_uri(
                    f"/{self.service.name}/{section['name']}"
                )
            }
            obj = JSONAPIObject(
                "folder", f"{self.service.name}/{section['name']}", links=links
            )
            obj["name"] = section["name"]
            if section.get("display_name"):
                obj["display_name"] = section["display_name"]

            search_filter_obj = self.get_search_filter(obj["name"], section)
            if search_filter_obj:
                obj.add_relationship(
                    "metadata_searchfilter", search_filter_obj, local=True
                )

            root.append(obj)

        return root.serialize(request)

    def get_path(self, request, path):
        if "/" in path:
            return path

        query = dict(request.GET)  # TODO: use search filter to filter?
        skip_query_keys = ["limit", "page"]
        for skip_query_key in skip_query_keys:
            if skip_query_key in query:
                del query[skip_query_key]

        query_hash = hash_string(json.dumps(sorted(query.items())))
        search_query_cache, created = SearchQueryCache.objects.get_or_create(
            query_hash=query_hash, defaults={"query": query}
        )
        search_query_cache.save()

        return f"{path}/{query_hash}"

    def get_search_filter(self, name, level_config):
        obj = JSONAPIObject("metadata_searchfilter", name)

        filters = self.service.get_filters(level_config)

        if filters:
            obj["filter"] = filters.serialize()

        return obj

    def add_additional_parent_relationships(
        self, parent, request, config, listing_item_root
    ):
        path = listing_item_root.path.split("/")
        root_path, query_hash = path[:2]
        trailing_path = "/".join(path[2:])
        if (
            trailing_path
        ):  # Should not be added to nested listings, only actual searches
            return

        search_filter_obj = self.get_search_filter(root_path, config)
        parent.add_relationship("metadata_searchfilter", search_filter_obj)
