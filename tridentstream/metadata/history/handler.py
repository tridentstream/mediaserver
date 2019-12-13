import logging
from collections import defaultdict

from rest_framework import serializers

from ...bases.metadata.linkingmetadata import LinkingMetadataHandlerPlugin
from .models import History, HistoryMetadata, ListingItemRelation, ViewState

logger = logging.getLogger(__name__)


class ViewStateSerializer(serializers.ModelSerializer):
    state = serializers.DictField(source="values")

    class Meta:
        model = ViewState
        fields = ("identifier", "state", "last_update", "created")


class HistorySerializer(serializers.ModelSerializer):
    viewstates = ViewStateSerializer(source="viewstate_set", many=True, read_only=True)

    class Meta:
        model = History
        fields = ("name", "viewstates", "last_watched", "created")


class HistoryMetadataHandlerPlugin(LinkingMetadataHandlerPlugin):
    plugin_name = "history"
    priority = -10

    serializer = HistorySerializer
    model = History
    listing_item_relation_model = ListingItemRelation
    metadata_link_model = HistoryMetadata
    user_field = "history__user_id"
    viewstate_model = ViewState
    metadata_embed_method = "relate"

    __traits__ = ["history"]

    def get_metadata(self, request, identifier):
        histories = self.model.objects.filter(user=request.user, name=identifier)
        if not histories:
            return None
        history = histories[0]

        return self.serializer(history, context={"request": request}).data

    def get_relations(self, user, listingitem_ids):
        relations = (
            self.listing_item_relation_model.objects.filter(
                listingitem__in=listingitem_ids
            )
            .filter(user=user)
            .select_related("metadata__history")
        )
        retval = defaultdict(list)
        for relation in relations:
            retval[relation.listingitem_id].append(relation.metadata.history)

        return retval

    def schedule_update(self):
        pass
