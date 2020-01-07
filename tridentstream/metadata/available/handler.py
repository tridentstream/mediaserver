import logging
import uuid

from rest_framework import serializers

from ...bases.metadata.mixins import CoverSerializerMixin, PopulateMetadataJSONAPIMixin
from ...bases.metadata.schema import MetadataSchema
from ...plugins import MetadataHandlerPlugin
from .models import Availability, ListingItemAvailability, ListingItemRelation

logger = logging.getLogger(__name__)


class AvailableSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField("get_metadata_identifier")
    type = serializers.SerializerMethodField("get_metadata_type")

    class Meta:
        model = Availability
        exclude = ("app", "identifier")

    def get_metadata_identifier(self, obj):
        return obj.pk

    def get_metadata_type(self, obj):
        return f"metadata_{obj.metadata_name}"

    def get_populated(self, obj):
        return True


class AvailableMetadataHandlerPlugin(
    PopulateMetadataJSONAPIMixin, MetadataHandlerPlugin
):
    plugin_name = "available"
    __traits__ = ["availability"]
    priority = -10
    config_schema = MetadataSchema
    linkable = False

    model = Availability
    filter = None
    listing_item_relation_model = ListingItemRelation
    select_related = []
    prefetch_related = []
    serializer = AvailableSerializer
    metadata_embed_method = "relate"  # choices: include, relate, embed

    def get_metadata(self, request, identifier):
        """
        Not something this type of metadata can actually handle
        """
        pass

    def link_metadata_listingitems(self, listing_build, fetch_metadata=True):
        item_creation_mapping = listing_build.item_creation_mapping
        listingitem_mapping = listing_build.listingitem_mapping

        ListingItemRelation.objects.filter(
            listingitem__in=listingitem_mapping.values()
        ).delete()  # TODO: optimize
        objs = []
        availability_mapping = {}
        for path, item in item_creation_mapping.items():
            if path not in listingitem_mapping:
                continue

            listingitem = listingitem_mapping[path]
            for availability in item.get("metadata:availability", []):
                objs.append(
                    ListingItemAvailability(
                        app=availability["app"],
                        identifier=availability["identifier"],
                        listingitem=listingitem,
                    )
                )

                availability_mapping.setdefault(availability["app"], {}).setdefault(
                    str(availability["identifier"]), []
                ).append(listingitem)

        ListingItemAvailability.objects.bulk_create(objs)

        objs = []
        for app, identifiers in availability_mapping.items():
            for availability in self.model.objects.filter(
                app=app, identifier__in=identifiers.keys()
            ):
                for listingitem in identifiers[availability.identifier]:
                    objs.append(
                        self.listing_item_relation_model(
                            metadata=availability, listingitem=listingitem
                        )
                    )

        self.listing_item_relation_model.objects.bulk_create(objs)

    # Availability trait
    def mark_available(self, app, identifier):
        """
        Mark this app/identifier as available.
        """
        availability, _ = Availability.objects.get_or_create(
            app=app, identifier=identifier
        )

        objs = []
        for lia in ListingItemAvailability.objects.filter(
            app=app, identifier=identifier
        ):
            objs.append(
                self.listing_item_relation_model(
                    listingitem=lia.listingitem, metadata=availability
                )
            )

        self.listing_item_relation_model.objects.bulk_create(objs)

    def populate_available(self, item):
        """
        Loop through the item and mark items we know are available as available.
        """
        availability_to_item_mapping = {}

        def _expand_item(item):
            for availability in item.get("metadata:availability", []):
                availability_to_item_mapping.setdefault(
                    availability["app"], {}
                ).setdefault(str(availability["identifier"]), []).append(item)

            if item.is_expanded:
                for sub_item in item.list():
                    _expand_item(sub_item)

        _expand_item(item)

        for app, identifiers in availability_to_item_mapping.items():
            for availability in Availability.objects.filter(
                app=app, identifier__in=identifiers.keys()
            ):
                for item in identifiers[availability.identifier]:
                    self.set_available(item)

    def get_recently_made_available(self, app, since):
        """
        Return a list of app, item, datetime dict that contains
        all made available by app since since.
        """
        return [
            {
                "app": available.app,
                "identifier": available.identifier,
                "datetime": available.created,
            }
            for available in Availability.objects.filter(app=app, created__gte=since)
        ]

    def set_available(self, item):
        """Sets the correct metadata key to indicate availability"""
        logger.trace(f"Setting item:{item!r} as available")
        item.setdefault("metadata", {})["available"] = True
