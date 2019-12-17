import logging

from django.http import Http404
from rest_framework import status
from rest_framework.response import Response
from unplugged import CascadingPermission, JSONAPIObject, JSONAPIRoot

from ...bases.listing.views import BaseListingView

logger = logging.getLogger(__name__)


class SectionsListView(BaseListingView):
    permission_classes = (CascadingPermission,)

    def get_config_view(self, request):
        root = JSONAPIRoot()
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

            first_level_config = sorted(section["levels"], key=lambda x: x["depth"])[0]
            filter_info_obj = self.get_level_filter_info(
                obj["name"], first_level_config
            )
            obj.add_relationship("metadata_filterinfo", filter_info_obj, local=True)

            root.append(obj)

        return root.serialize(request)

    def add_additional_parent_relationships(
        self, parent, request, config, listing_item_root
    ):
        parent_filter_info_obj = self.get_level_filter_info(
            listing_item_root.path, config["level"]
        )
        parent.add_relationship("metadata_filterinfo", parent_filter_info_obj)
