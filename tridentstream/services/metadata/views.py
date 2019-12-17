import logging

from django.http import Http404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from unplugged import CascadingPermission, JSONAPIObject, JSONAPIRoot

logger = logging.getLogger(__name__)


class MetadataView(APIView):
    service = None
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, metadata_handler, identifier):
        logger.debug(
            f"Fetching metadata using {metadata_handler} with identifier {identifier}"
        )
        for plugin in self.service._related_plugins:
            if (
                plugin.name == metadata_handler
                and plugin.plugin_type == "metadatahandler"
            ):
                break
        else:
            logger.warning(f"Did not find metadata_handler {metadata_handler}")
            raise Http404

        metadata = plugin.get_metadata(request, identifier)
        if not metadata:
            raise Http404

        root = JSONAPIRoot()

        identifier = f"{plugin.plugin_name}:{identifier}"
        obj_type = plugin.get_jsonapi_type()
        obj = JSONAPIObject(obj_type, identifier)
        obj.update(metadata)
        root.append(obj)

        return Response(root.serialize(request))
