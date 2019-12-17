import logging
from datetime import datetime

import pytz
from django.http import Http404, HttpResponseNotModified
from django.utils.http import parse_http_date_safe
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from thomas import Item
from unplugged import CascadingPermission

from ...exceptions import NotModifiedException
from ...plugins import InputPluginManager
from ...stream import create_stream

logger = logging.getLogger(__name__)


class RemoteFilesystemView(APIView):
    service = None

    permission_classes = (CascadingPermission,)

    def get_plugin_path(self, path):
        path += "/"
        input_name, path = path.split("/", 1)

        for input_config in self.service.config["inputs"]:
            if input_config["input"].name != input_name:
                continue

            return input_config["input"], path.strip("/")

        return None, None

    def get(self, request, path):
        path = path.strip("/")
        if path == "":
            listing = Item(id="")
            for input_config in self.service.config.get("inputs", []):
                if not input_config or not input_config["input"]:
                    continue
                plugin = input_config["input"]

                item = plugin.get_item("")
                item.id = plugin.name
                listing.add_item(item)

            return Response(listing.serialize())
        else:
            if_modified_since = request.META.get("HTTP_IF_MODIFIED_SINCE")
            if if_modified_since:
                if_modified_since = parse_http_date_safe(if_modified_since)
            if if_modified_since:
                if_modified_since = datetime.fromtimestamp(if_modified_since, pytz.UTC)

            depth = int(request.GET.get("depth", 0))

            plugin, plugin_path = self.get_plugin_path(path)

            if not plugin:
                raise Http404

            item = InputPluginManager.get_item(plugin, plugin_path)

            logger.info(
                f"Trying to create listing for {plugin!r} - path:{plugin_path} - last_modified:{if_modified_since}"
            )
            item.list(depth=depth)

            if not item.is_readable and not item.is_listable:
                raise Http404

            if if_modified_since and item.modified <= if_modified_since:
                return HttpResponseNotModified()

            return Response(item.serialize())

    def post(self, request, path):
        plugin, plugin_path = self.get_plugin_path(path)
        if not plugin:
            raise Http404

        item = InputPluginManager.get_item(plugin, plugin_path)

        try:
            streamresult = create_stream(item, request)
            return Response(streamresult.serialize(request))
        except:
            logger.exception(f"Failed to stream path:{path!r} from {plugin.name}")

        return Response(
            {"status": "failed", "message": "Unable to properly stream "},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
