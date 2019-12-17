import logging
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils.timezone import now
from unplugged import RelatedPluginField, Schema

from ...plugins import HistoryPlugin, MetadataHandlerPlugin

logger = logging.getLogger(__name__)

HISTORY_WATCH_PERIOD = timedelta(hours=24)


class HistorySchema(Schema):
    history_metadata = RelatedPluginField(
        plugin_type=MetadataHandlerPlugin, traits=["history"]
    )


class HistoryHistoryPlugin(HistoryPlugin):
    plugin_name = "history"
    config_schema = HistorySchema

    __traits__ = ["queryable"]

    def __init__(self, config):
        self.history = config["history_metadata"]

    def log_history(self, config, listingitem, viewstate):
        level_config = config.get("level", {})
        histories = self.history.model.objects.filter(
            user=viewstate.user,
            name=listingitem.name,
            last_watched__gte=now() - HISTORY_WATCH_PERIOD,
        )
        logger.debug(
            f"Trying to log history entry with listingitem:{listingitem!r} to user:{viewstate.user!r}"
        )

        if histories:
            history = histories[0]
            logger.debug(f"Reusing old history entry:{history!r}")
        else:
            history = self.history.model(user=viewstate.user, name=listingitem.name)
            logger.debug("Creating new history entry")

        history.listingitem_app = listingitem.app
        history.listingitem_path = listingitem.path
        history.last_watched = now()
        history.save()

        for metadata_handler in level_config.get("metadata_handlers", []):
            if not metadata_handler.linkable:
                continue

            primary_metadata = "primary_metadata" in metadata_handler.__traits__

            for metadata in listingitem.get_metadata(metadata_handler.plugin_name):
                content_type = ContentType.objects.get_for_model(metadata)

                try:
                    metadata_link = self.history.metadata_link_model.objects.get(
                        history=history,
                        object_id=metadata.pk,
                        content_type=content_type,
                    )
                except self.history.metadata_link_model.DoesNotExist:
                    metadata_link = self.history.metadata_link_model.objects.create(
                        history=history,
                        metadata=metadata,
                        primary_metadata=primary_metadata,
                    )

                self.history.listing_item_relation_model.objects.get_or_create(
                    metadata=metadata_link, listingitem=listingitem, user=viewstate.user
                )

        try:
            viewstate_obj = self.history.viewstate_model.objects.get(
                identifier=viewstate.id, user=viewstate.user
            )
        except self.history.viewstate_model.DoesNotExist:
            viewstate_obj = self.history.viewstate_model(
                identifier=viewstate.id, user=viewstate.user, values={}
            )

        viewstate_obj.history = history
        viewstate_obj.save()

        if viewstate_obj.values:
            logger.debug(
                f"Existing viewstate already there for id {viewstate_obj.identifier}, updating with new values"
            )
            viewstate.update(viewstate_obj.values)

        viewstate.add_change_callback(self.viewstate_updated)

    def viewstate_updated(self, viewstate):
        try:
            viewstate_obj = self.history.viewstate_model.objects.get(
                identifier=viewstate.id, user=viewstate.user
            )
        except self.history.viewstate_model.DoesNotExist:
            logger.warning(
                f"Got update to unknown viewstate {viewstate.id} for user {viewstate.user}"
            )
            return

        viewstate_obj.values.update(viewstate)
        viewstate_obj.save()
        logger.debug(
            f"Updated viewstate {viewstate.id} for user {viewstate.user} with {viewstate_obj.values}"
        )
