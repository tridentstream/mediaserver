import logging
import time
from collections import defaultdict
from threading import Event, Lock

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now
from rest_framework import serializers
from unplugged import threadify

from twisted.internet import reactor

from ...plugins import MetadataHandlerPlugin
from .mixins import (
    CoverSerializerMixin,
    GetMetadataStatsMixin,
    ListingItemRelinkingMixin,
    PopulateMetadataJSONAPIMixin,
    ResetFailedMixin,
)
from .schema import MetadataSchema

logger = logging.getLogger(__name__)


class RemoteMetadataHandlerPluginMetaclass(MetadataHandlerPlugin.__class__):
    def __init__(cls, name, bases, dct):
        setattr(cls, "currently_updating_lock", Lock())
        setattr(cls, "event_queue", {})

        super(RemoteMetadataHandlerPluginMetaclass, cls).__init__(name, bases, dct)


class RemoteMetadataHandlerPlugin(
    ListingItemRelinkingMixin,
    PopulateMetadataJSONAPIMixin,
    GetMetadataStatsMixin,
    ResetFailedMixin,
    MetadataHandlerPlugin,
    metaclass=RemoteMetadataHandlerPluginMetaclass,
):
    model = None
    listing_item_relation_model = None
    currently_updating_lock = None
    serializer = None
    filter = None
    fulltext_fields = []
    linkable = True
    prepopulate_metadata = False
    metadata_resolution_link_model = None

    config_schema = MetadataSchema

    _do_unload = False
    _job_schedule = None

    def get_metadata(self, request, identifier):
        do_update = False
        try:
            metadata = self.model.objects.get(identifier=identifier)
            if metadata.last_update_status in ["do-not-fetch", "pending"]:
                metadata.priority = 50
                metadata.last_update_status = "pending"
                metadata.plugin = self._plugin_obj
                metadata.save()
                do_update = True
        except self.model.DoesNotExist:  # probably contains thread problems
            self.model(
                identifier=identifier, priority=50, plugin=self._plugin_obj
            ).save()
            do_update = True

        if do_update:
            self.schedule_update()
            if identifier not in self.event_queue:
                self.event_queue[identifier] = Event()
            e = self.event_queue[identifier]
            logger.info(
                f"Metadata {self.name}/{identifier} not found in database, waiting for it"
            )
            if not e.wait(15):
                return None

            if identifier in self.event_queue:
                del self.event_queue[identifier]

            try:
                metadata = self.model.objects.get(identifier=identifier, populated=True)
            except self.model.DoesNotExist:
                return None

        return self.serializer(
            metadata, context={"request": request, "config": self.config}
        ).data

    def get_identifier(self, item):
        trigger = f"metadata:{self.plugin_name}:id"
        return item.get(trigger)

    def link_metadata_listingitems(self, listing_build, fetch_metadata=True):
        logger.debug("Linking sections with metadata")

        listing_item_root = listing_build.listing_item_root
        item_creation_mapping = listing_build.item_creation_mapping
        listingitem_mapping = listing_build.listingitem_mapping
        index_writer = listing_build.index_writer
        existing_listing_items = listing_build.existing_listing_items
        listing_last_update = listing_build.listing_last_update

        listing_item_model = type(listing_item_root)

        try:
            self.model._meta.get_field("name")
            has_name = True
        except FieldDoesNotExist:
            has_name = False

        logger.debug("Finding all the metadata we need")
        if has_name:
            identifier_name_mapping = {}
        required_metadata = set()
        metadata_mapping = defaultdict(set)
        missing_metadata = []
        for path, item in item_creation_mapping.items():
            listingitem = listingitem_mapping.get(path)
            logger.trace(
                f"Getting identifier from metadata_name:{self.name!r} path:{path!r} item:{item!r} listingitem:{listingitem!r}"
            )
            identifier = self.get_identifier(item)
            if not identifier:
                logger.trace(
                    f"We found no identifier for path:{path!r} item:{item!r} listingitem:{listingitem!r}"
                )
                missing_metadata.append((path, item, listingitem))
                continue

            metadata_mapping[path].add(identifier)
            required_metadata.add(identifier)
            if has_name:
                identifier_name_mapping[identifier] = item.id

        resolution_links_created = False
        search_resolve = self.config.get("search_resolve")
        if missing_metadata and search_resolve and self.metadata_resolution_link_model:
            names = {
                item.id: (path, item, listingitem)
                for path, item, listingitem in missing_metadata
            }
            resolution_links = self.metadata_resolution_link_model.objects.select_related(
                "metadata"
            ).filter(
                search_resolve=search_resolve, name__in=names.keys()
            )

            logger.debug(f"We have {len(resolution_links)} resolution links")
            missing_resolution_links = {}
            for resolution_link in resolution_links:
                if resolution_link.name not in names:
                    logger.warning(
                        f"Name {resolution_link.name} not found in resolution link query"
                    )
                    continue

                path, item, listingitem = names.pop(resolution_link.name)
                if resolution_link.metadata:
                    identifier = resolution_link.metadata.identifier
                    metadata_mapping[path].add(identifier)
                    logger.trace(
                        f"Solving path:{path} to identifier:{identifier} using resolution links"
                    )
                    required_metadata.add(identifier)
                    if has_name:
                        identifier_name_mapping[identifier] = item.id
                elif listingitem:
                    missing_resolution_links[listingitem.path] = resolution_link

            if names or missing_resolution_links:
                logger.info("Missing resolution links, creating")
                resolution_links_create = []
                for name in names.keys():
                    resolution_links_create.append(
                        self.metadata_resolution_link_model(
                            search_resolve=search_resolve,
                            name=name,
                            plugin=self._plugin_obj,
                        )
                    )

                self.metadata_resolution_link_model.objects.bulk_create(
                    resolution_links_create
                )

                resolution_links = self.metadata_resolution_link_model.objects.filter(
                    search_resolve=search_resolve, name__in=names.keys()
                )

                mapping = {}

                for resolution_link in resolution_links:
                    path, item, listingitem = names.pop(resolution_link.name)
                    mapping[path] = resolution_link

                with transaction.atomic():
                    for listingitem in listing_item_model.objects.filter(
                        app=listing_item_root.app,
                        path__in=list(mapping.keys())
                        + list(missing_resolution_links.keys()),
                    ):
                        resolution_link = (
                            listingitem.path in mapping
                            and mapping.pop(listingitem.path)
                            or missing_resolution_links.pop(listingitem.path)
                        )
                        resolution_link.listingitems.add(listingitem)

                resolution_links_created = True

        metadata = self.model.objects.filter(identifier__in=required_metadata)

        if fetch_metadata or self.prepopulate_metadata:
            initial_status = "pending"
            metadata.filter(last_update_status="do-not-fetch").update(
                last_update_status=initial_status
            )
        else:
            initial_status = "do-not-fetch"

        metadata = dict(metadata.values_list("identifier", "pk"))

        missing_metadata = required_metadata - set(metadata.keys())

        if missing_metadata or resolution_links_created:
            if missing_metadata:
                if has_name:
                    self.model.objects.bulk_create(
                        self.model(
                            identifier=identifier,
                            last_update_status=initial_status,
                            plugin=self._plugin_obj,
                            name=identifier_name_mapping[identifier],
                        )
                        for identifier in missing_metadata
                    )
                else:
                    self.model.objects.bulk_create(
                        self.model(
                            identifier=identifier,
                            plugin=self._plugin_obj,
                            last_update_status=initial_status,
                        )
                        for identifier in missing_metadata
                    )

            if self.prepopulate_metadata:
                logger.debug(
                    "This metadata type should be updated before we use it, waiting for update to complete"
                )
                for _ in range(20 * 10):
                    if self.update():
                        break
                    else:
                        time.sleep(0.1)
            else:
                self.schedule_update()

        metadata.update(
            self.model.objects.filter(identifier__in=missing_metadata).values_list(
                "identifier", "pk"
            )
        )

        listingitem_metadata_mapping = defaultdict(set)
        for path, pk in listing_item_model.objects.filter(
            Q(pk=listing_item_root.pk) | Q(parent=listing_item_root)
        ).values_list("path", "pk"):
            for identifier in metadata_mapping[path]:
                listingitem_metadata_mapping[pk].add((metadata[identifier], None))

        self.listingitem_relinking(listing_item_root, listingitem_metadata_mapping)

        if index_writer and self.fulltext_fields:
            logger.debug(f"Creating search index for metadata {self.name}")

            obj_type = f"metadata_{self.plugin_name}__metadata__"
            last_path, used_searchstr = None, set()
            query = listing_item_root.listingitem_set.filter(
                Q(
                    path__in=set(item_creation_mapping.keys())
                    - set(existing_listing_items.keys())
                )
                | Q(
                    path__in=existing_listing_items.keys(),
                    **{obj_type + "last_updated": listing_last_update},
                )
            ).distinct()

            for searchstrs in query.values_list(
                "path", *[(obj_type + x) for x in self.fulltext_fields]
            ).order_by("pk"):
                searchstrs = list(searchstrs)
                path = searchstrs.pop(0)
                if path != last_path:
                    used_searchstr = set()
                    last_path = path

                for searchstr in searchstrs:
                    if searchstr in used_searchstr or not searchstr:
                        continue

                    used_searchstr.add(searchstr)
                    index_writer.index(path, searchstr)

    def ready(self):
        self.schedule_update()

    def schedule_update(self):
        if not self._job_schedule:
            self._job_schedule = settings.SCHEDULER.add_job(
                self.update_request, trigger="interval", minutes=30
            )

        self.update_request()

    def update_request(self, *args):
        threadify(self.update)()

    def update(self):
        """Check for metadata to update"""
        if self.currently_updating_lock.locked():
            logger.info("Updater lock already locked, bailing")
            return False

        logger.debug(f"Trying to update metadata for {self.name}")
        with self.currently_updating_lock:
            if self.metadata_resolution_link_model:
                while not self._do_unload and not reactor._stopped:
                    resolution_links = self.metadata_resolution_link_model.objects.filter(
                        last_update_status="pending", listingitems__isnull=False
                    )
                    if not resolution_links:
                        break
                    resolution_link = resolution_links[0]

                    logger.debug(f"Resolving link {resolution_link!r}")

                    resolution_link.last_update_status = "updating"
                    resolution_link.save()

                    if resolution_link.plugin:
                        p = resolution_link.plugin.get_plugin()
                        config = p.config
                    else:
                        config = self.config

                    resolution_link.populated = True
                    try:
                        identifier = resolution_link.resolve(config)
                    except:
                        logger.exception(f"Failed to resolve link {resolution_link!r}")
                        resolution_link.last_update_status = "failed"
                    else:
                        logger.debug(
                            f"Successfully resolved link {resolution_link!r} to {identifier}"
                        )
                        resolution_link.last_update_status = "success"

                        if identifier:
                            metadata, _ = self.model.objects.get_or_create(
                                identifier=identifier,
                                defaults={"plugin": self._plugin_obj},
                            )
                            logger.debug(
                                f"Got identifier {identifier}, linking all applicable listingitems"
                            )
                            resolution_link.metadata = metadata

                            for listingitem in resolution_link.listingitems.all():
                                self.listing_item_relation_model.objects.create(
                                    listingitem=listingitem, metadata=metadata
                                )

                    resolution_link.last_updated = now()
                    resolution_link.save()

            while not self._do_unload and not reactor._stopped:
                metadatas = self.model.objects.filter(
                    last_update_status="pending"
                ).order_by("-priority")
                if not metadatas:
                    break
                metadata = metadatas[0]

                logger.debug(f"Populating {metadata!r}")

                metadata.last_update_status = "updating"
                metadata.save()

                if metadata.plugin:
                    p = metadata.plugin.get_plugin()
                    config = p.config
                else:
                    config = self.config

                metadata.populated = True
                try:
                    metadata.populate(config)
                    metadata.prefetch_related_denormalized = self.get_prefetch_related_denormalized(
                        metadata
                    )
                except:
                    logger.exception(f"Failed to populate metadata {metadata!r}")
                    metadata.last_update_status = "failed"
                else:
                    logger.debug(f"Successfully populated metadata {metadata!r}")
                    metadata.last_update_status = "success"

                metadata.last_updated = now()
                metadata.save()

                if metadata.identifier in self.event_queue:
                    self.event_queue[metadata.identifier].set()

        return True

    def unload(self):
        self._do_unload = True

        if self._job_schedule:
            self._job_schedule.remove()


class BaseMetadataSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="identifier", read_only=True)

    class Meta:
        model = None
        exclude = (
            "last_updated",
            "created",
            "identifier",
            "priority",
            "plugin",
            "prefetch_related_denormalized",
        )


class MetadataSerializer(CoverSerializerMixin, BaseMetadataSerializer):
    cover = serializers.SerializerMethodField("get_cover_url")
