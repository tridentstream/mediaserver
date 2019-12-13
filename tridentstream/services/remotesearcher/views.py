import json
import logging

from django.http import Http404

from rest_framework.views import APIView
from rest_framework.response import Response

from thomas import Item

from unplugged import CascadingPermission

from ...plugins import SearchQuery
from ...utils import hash_string

from .models import ListingCache

logger = logging.getLogger(__name__)


class RemoteSearcherFiltersView(APIView):
    service = None

    permission_classes = (CascadingPermission,)

    def get(self, request):
        return Response(
            [
                {
                    "name": searcher["searcher"].name,
                    "filters": searcher["searcher"].filters.serialize(),
                }
                for searcher in self.service.config["searchers"]
            ]
        )


class RemoteSearcherView(APIView):
    service = None

    permission_classes = (CascadingPermission,)

    def get_item(self, searcher_name, search_token, path, sub_path):
        try:
            listing_cache = ListingCache.objects.get(
                app=self.service.name,
                searcher_name=searcher_name,
                search_token=search_token,
                path=path,
            )
        except ListingCache.DoesNotExist:
            logger.warning("Unable to find cache for search_token:%s path:%s")
            raise Http404

        return Item.unserialize(listing_cache.listing).get_item_from_path(sub_path)

    def get_searcher(self, searcher_name):
        for searcher in self.service.config["searchers"]:
            searcher = searcher["searcher"]
            if searcher.name == searcher_name:
                return searcher
        else:
            logger.warning("Unknown searcher:%s" % (searcher_name,))
            raise Http404

    def get(self, request, searcher_name, search_token="", path=""):
        searcher = self.get_searcher(searcher_name)

        path = path.strip("/")
        sub_path = ""

        if search_token:
            sub_path = request.GET.get("sub_path").strip("/")
            item = self.get_item(searcher_name, search_token, path, sub_path)
            if not item:
                logger.warning(
                    "Unknown item search_token:%s path:%s sub_path:%s"
                    % (search_token, path, sub_path)
                )
                raise Http404
        else:
            query = dict(request.GET)
            search_token = hash_string(json.dumps(sorted(query.items())))
            search_query = SearchQuery(searcher.filters, query)

            logger.info(
                "Got request to search for search_token:%s query:%r"
                % (search_token, query)
            )
            item = searcher.get_item(search_token, search_query)

        full_path = ("%s/%s" % (path, sub_path)).strip("/")
        logger.debug(
            "Listing search_token:%s path:%s item:%r" % (search_token, full_path, item)
        )
        item.list()
        ListingCache.objects.update_or_create(
            app=self.service.name,
            searcher_name=searcher_name,
            search_token=search_token,
            path=full_path,
            defaults={"listing": item.serialize(include_routes=True)},
        )

        availability_plugin = self.service.config.get("availability")
        if availability_plugin:
            logger.info("Found availability plugin, populating item.")
            availability_plugin.populate_available(item)

        return Response(
            {
                "item": item.serialize(),
                "path": full_path,
                "search_token": search_token,
                "searcher_name": searcher_name,
            }
        )

    def post(self, request, searcher_name, search_token="", path=""):
        path = path.strip("/")
        sub_path = request.GET.get("sub_path").strip("/")
        if not search_token:
            logger.warning("Search token missing from stream attempt")
            raise Http404

        item = self.get_item(searcher_name, search_token, path, sub_path)
        stream = item.stream()
        if not stream:
            logger.warning("Failed to return a stream")
            raise Http404

        return Response(stream.serialize(request))
