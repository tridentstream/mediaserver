import logging
from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.db import transaction
from django.utils.timezone import now
from thomas import Item, router

from ...exceptions import NotModifiedException, PathNotFoundException
from ...locktracker import LockTracker
from .models import ListingItem

logger = logging.getLogger(__name__)


class ListingBuild:
    config = None
    index_writer = None
    listing_item_root = None
    existing_listing_items = None
    item_creation_mapping = None
    listingitem_mapping = None
    linkable_metadata = None
    listing_last_update = None


class ListingBuilder:
    def __init__(self, service):
        self.service = service
        self.locktracker = LockTracker()

    def get_item(self, path):
        """
        Returns item at a given path if it exists.
        Cannot try to build
        """
        try:
            return ListingItem.objects.get(app=self.service.name, path=path)
        except ListingItem.DoesNotExist:
            return None

    def get_listing(
        self, config, path, use_background_recheck=True, do_not_rebuild=False
    ):
        """
        Returns listing if it is good and available
        """
        path = path.strip("/")

        last_modified = None
        try:
            listing_item_root = ListingItem.objects.get(
                app=self.service.name, path=path
            )
            if listing_item_root.is_root:
                last_modified = listing_item_root.last_updated

                if settings.DEBUG_CLEAR_CACHE:
                    logger.debug("Clear cache enabled, removing old listing")
                    last_modified = None
                    ListingItem.objects.filter(parent=listing_item_root).delete()
                    listing_item_root.delete()
                    listing_item_root = None
        except ListingItem.DoesNotExist:
            listing_item_root = None

        if (
            config["level"].get("background_recheck")
            and use_background_recheck
            and listing_item_root
            and listing_item_root.last_checked
            and listing_item_root.last_checked
            > now() - timedelta(minutes=self.service.automatic_rebuild_timer)
        ):
            logger.info(
                "We run updates to this listing in the background and it is sufficiently recent to be used"
            )
            if not do_not_rebuild:
                self.service.rebuild_listing(config, path, delay=True)
            return listing_item_root

        if listing_item_root:
            item = Item.unserialize(listing_item_root.config["original_item"])
        else:
            item = self.service.get_item(config, path)

        try:
            if not item:
                raise PathNotFoundException()

            item.list(depth=config["level"]["listing_depth"])
            if last_modified and item.modified and item.modified <= last_modified:
                raise NotModifiedException()
        except NotModifiedException:
            logger.info("Our current listing is up-to-date, no need to do anything")
            listing_item_root.last_checked = now()
            listing_item_root.save()
            return listing_item_root
        except PathNotFoundException:
            logger.info(
                "We got an all paths not found, just returning empty for now and hope it will be better next time"
            )
            return None

        if not item.is_listable:
            if last_modified is None:
                logger.info(
                    "Empty listing and no last_modified, this is an unknown path"
                )
                return None
            else:
                logger.info(
                    "Empty listing and last_modified, returning already built root"
                )
                return listing_item_root

        lock_path = "%s/%s" % (self.service.name, path)
        with self.locktracker.get_path(lock_path) as lt:
            if lt.waited:
                logger.info(
                    "Seems like someome built this view just before us, no need to build"
                )
                try:
                    listing_item_root = ListingItem.objects.get(
                        app=self.service.name, path=path
                    )
                except ListingItem.DoesNotExist:
                    listing_item_root = None
            else:
                logger.info("Got lock, building listview")
                listing_item_root = self.build_listing(item, config, path)

        return listing_item_root

    def build_listing(self, listing, config, path):
        """
        Builds a listing view using given specifications.

        :param path: Root of listing view.
        """
        listing_build = ListingBuild()
        listing_build.config = config

        try:
            listing_item_root = ListingItem.objects.get(
                app=self.service.name, path=path
            )
        except:
            listing_item_root = ListingItem(app=self.service.name, path=path)

        listing_build.listing_item_root = listing_item_root
        listing_build.listing_last_update = listing_item_root.last_updated

        # figure out the actual config for this depth
        item_creation_mapping = {}

        def do_list(listing, depth):
            for item in listing.list():
                if depth == 0:
                    yield item
                elif item.is_listable:
                    for sub_item in do_list(item, depth=depth - 1):
                        yield sub_item

        for item in do_list(listing, config["level"]["listing_depth"]):
            if not item.is_listable and config["edge_type"] == "folder":
                continue

            if config["edge_type"] == "file" and not item.is_streamable:
                continue

            item_path = item.path[len(listing.id) :]
            item_path = "%s/%s" % (path.strip("/"), item_path.strip("/"))
            item_creation_mapping[item_path] = item

        listing_build.item_creation_mapping = item_creation_mapping

        # find already existing entries
        existing_listing_items = {}
        for listingitem in ListingItem.objects.filter(
            app=self.service.name, path__in=item_creation_mapping.keys()
        ):
            existing_listing_items[listingitem.path] = listingitem

        logger.info("Found %i existing listingitems" % len(existing_listing_items))
        listing_build.existing_listing_items = existing_listing_items

        indexer_delete_paths = []
        is_update = False
        # delete items that no longer exist at source
        with transaction.atomic():
            if listing_item_root.is_root:
                logger.info("This is an update, looking for old cruft to delete.")
                is_update = True
                for listingitem in ListingItem.objects.filter(
                    app=self.service.name, parent=listing_item_root
                ):
                    if listingitem.path not in existing_listing_items:
                        indexer_delete_paths.append(listingitem.path)
                        listingitem.delete()

            listing_item_root.datetime = listing_item_root.datetime or now()
            listing_item_root.is_root = True
            listing_item_root.last_checked = now()
            listing_item_root.save()

            item_creation_mapping[listing_item_root.path] = listing
            existing_listing_items[listing_item_root.path] = listing_item_root

        # prepare the text search indexer
        indexer = config["level"].get("indexer")
        if indexer:
            if not is_update:
                indexer.clear(path)
            index_writer = indexer.get_writer(path)
            listing_build.index_writer = index_writer

            for indexer_delete_path in indexer_delete_paths:
                index_writer.delete(indexer_delete_path)
        else:
            index_writer = None

        del indexer_delete_paths

        # find listingitems to create and modify existing
        listingitem_children_purges = []
        listingitems = []
        for item_path, item in item_creation_mapping.items():
            if item_path in existing_listing_items:
                listingitem = existing_listing_items[item_path]
                should_create = False
            else:
                listingitem = ListingItem(app=self.service.name, path=item_path)
                listingitem.name = listingitem.get_name()
                should_create = True

            if listingitem != listing_item_root:
                listingitem.parent = listing_item_root

            if (
                listingitem.datetime != item.modified
                and listingitem.is_root
                and listing_item_root != listingitem
            ):
                listingitem.is_root = False
                listingitem_children_purges.append(listingitem)

            listingitem.datetime = item.modified

            listingitem.last_updated = item.modified
            if listingitem.is_root:
                listingitem.item_type = "folder"
            else:
                listingitem.item_type = config["edge_type"]

                # write item name to index if index exists
                if index_writer:
                    normalized_name = (
                        item.id.replace("_", " ").replace(".", " ").replace("-", " ")
                    )
                    index_writer.index(item_path, normalized_name)

            listingitem.attributes = {"name": item.id}
            listingitem.config = {
                "original_item": item.serialize(
                    include_routes=True, include_nested=False
                )
            }

            if "metadata" in item:
                listingitem.attributes["metadata"] = item["metadata"]

            if "size" in item:
                listingitem.attributes["size"] = item["size"]

            if should_create:
                listingitems.append(listingitem)

            logger.trace(
                "Creating:%s listingitem with path:%s and parent path:%s"
                % (should_create, listingitem.path, listing_item_root.path)
            )

        # save the newly created listingitems
        with transaction.atomic():
            for listingitem in existing_listing_items.values():
                listingitem.save()

            for listingitem in listingitem_children_purges:
                ListingItem.objects.filter(
                    app=self.service.name, parent=listingitem
                ).delete()

        ListingItem.objects.bulk_create(listingitems)

        logger.info("Done creating listingitems, linking with metadata")

        self.link_with_metadata(listing_build)

        if index_writer:
            index_writer.commit()

        return listing_item_root

    def link_with_metadata(self, listing_build):
        """
        Link listingitems with metadata
        """
        logger.debug(
            f"Linking listingitems with metadata from root:{listing_build.listing_item_root.path}"
        )

        listing_build.listingitem_mapping = {
            li.path: li
            for li in ListingItem.objects.filter(
                app=self.service.name, parent=listing_build.listing_item_root
            )
        }
        metadata_handlers = sorted(
            listing_build.config["level"]["metadata_handlers"],
            key=lambda x: getattr(x, "priority", 0),
            reverse=True,
        )
        listing_build.linkable_metadata = [
            mh for mh in metadata_handlers if mh.linkable
        ]
        for metadata_handler in metadata_handlers:
            logger.debug(
                f"Linking items from root {listing_build.listing_item_root.path} with metadata handler {metadata_handler.name}"
            )
            metadata_handler.link_metadata_listingitems(
                listing_build, listing_build.config.get("fetch_metadata", True)
            )
