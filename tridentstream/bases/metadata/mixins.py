import logging
from collections import defaultdict

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Count, Field, Q
from unplugged import JSONAPIObject, command

from .models import BaseMetadataResolutionLink, BaseUpdatable

logger = logging.getLogger(__name__)


class ListingItemRelinkingMixin:
    """
    Mixin to link Metadata and ListingItems according to the metadata_mapping.

    Tries to do it intelligently.
    """

    listing_item_relation_model = None

    def listingitem_relinking(self, listing_item_root, metadata_mapping):
        logger.debug("Figuring out what we can delete or just update")
        existing_listingitem_relations = defaultdict(set)
        actual_existing_listingitem_relations = {}
        for (
            pk,
            listingitem_id,
            metadata_id,
            user_id,
        ) in self.listing_item_relation_model.objects.filter(
            Q(listingitem__parent=listing_item_root) | Q(listingitem=listing_item_root)
        ).values_list(
            "pk", "listingitem_id", "metadata_id", "user_id"
        ):
            existing_listingitem_relations[listingitem_id].add((metadata_id, user_id))
            actual_existing_listingitem_relations[
                (listingitem_id, metadata_id, user_id)
            ] = pk
        logger.debug(
            "Found %i listingitems with existing relations"
            % (len(existing_listingitem_relations),)
        )

        remove_relations = []
        create_relations = []

        listing_item_model = type(listing_item_root)
        listingitems = listing_item_model.objects.filter(
            Q(pk=listing_item_root.pk) | Q(parent=listing_item_root)
        )
        for listingitem_id in listingitems.values_list("pk", flat=True):
            metadata_ids = metadata_mapping.get(listingitem_id, set())
            existing_metadata_ids = existing_listingitem_relations.get(
                listingitem_id, set()
            )

            logger.trace(
                f"Comparing existing:{existing_metadata_ids!r} and expected:{metadata_ids!r}"
            )
            for metadata_id, user_id in existing_metadata_ids - metadata_ids:
                logger.trace(
                    f"Removing relation between listingitem_id:{listingitem_id} and metadata_id:{metadata_id} and user_id:{user_id}"
                )
                relation = actual_existing_listingitem_relations[
                    (listingitem_id, metadata_id, user_id)
                ]
                remove_relations.append(relation)

            for metadata_id, user_id in metadata_ids - existing_metadata_ids:
                logger.trace(
                    f"Creating relation between listingitem_id:{listingitem_id} and metadata_id:{metadata_id} and user_id:{user_id}"
                )
                create_relations.append(
                    self.listing_item_relation_model(
                        listingitem_id=listingitem_id,
                        metadata_id=metadata_id,
                        user_id=user_id,
                    )
                )

        logger.info(f"Creating {len(create_relations)} relations")
        self.listing_item_relation_model.objects.bulk_create(create_relations)

        logger.info(f"Deleting {len(remove_relations)} relations")
        self.listing_item_relation_model.objects.filter(
            pk__in=remove_relations
        ).delete()


class UnknownEmbedMethodException(Exception):
    pass


class StrDictProxy(dict):
    def __str__(self):
        return self.get("__str__")


class PrefetchProxy:
    def __init__(self, obj, prefetch_fields):
        self._obj = obj
        self._prefetch_fields = set(prefetch_fields)
        self._prefetch_related_denormalized = getattr(
            obj, "prefetch_related_denormalized", {}
        )

    def __setattr__(self, key, value):
        if key.startswith("_") and not key.startswith("__"):
            return super(PrefetchProxy, self).__setattr__(key, value)
        else:
            return self._obj.__setattr__(key, value)

    def __getattr__(self, key):
        if (
            self._prefetch_fields
            and key in self._prefetch_fields
            and self._prefetch_related_denormalized
            and key in self._prefetch_related_denormalized
        ):
            value = self._prefetch_related_denormalized[key]
            if isinstance(value, dict):
                return StrDictProxy(value)
            elif isinstance(value, list):
                return [StrDictProxy(v) for v in value]
            else:
                return value
        else:
            return getattr(self._obj, key)


class PopulateMetadataJSONAPIMixin:
    model = None
    listing_item_relation_model = None
    select_related = []
    prefetch_related = []
    serializer = None
    metadata_embed_method = "include"  # choices: include, relate, embed, skip
    prefetch_related_denormalized_fields = [
        "AutoField",
        "BooleanField",
        "CharField",
        "DecimalField",
        "IntegerField",
        "SmallIntegerField",
        "TextField",
    ]

    def has_prefetch_related_denormalized(self):
        return hasattr(self.model, "prefetch_related_denormalized")

    def get_relations(self, user, listingitem_ids):
        prefetch_related = ["metadata"]
        if not self.has_prefetch_related_denormalized():
            prefetch_related += [f"metadata__{x}" for x in self.prefetch_related]
        select_related = [f"metadata__{x}" for x in self.select_related]
        relations = (
            self.listing_item_relation_model.objects.filter(
                listingitem__in=listingitem_ids
            )
            .filter(Q(user__isnull=True) | Q(user=user))
            .select_related(*select_related)
            .prefetch_related(*prefetch_related)
        )

        retval = defaultdict(list)
        for relation in relations:
            retval[relation.listingitem_id].append(relation.metadata)

        return retval

    def get_jsonapi_type(self):
        return "metadata_%s" % self.plugin_name

    def populate_metadata_jsonapi(self, request, root):
        if self.metadata_embed_method == "skip":
            return

        logger.info("Populating JSONAPI root with metadata")

        obj_type = self.get_jsonapi_type()

        items = {
            obj._original_object.id: obj
            for obj in (root.data + list(root.included.values()))
            if obj._original_object and hasattr(obj._original_object, "id")
        }

        relations = self.get_relations(request.user, items.keys())

        jsonapi_obj_mapping = {}  # maps listitem to metadata jsonapi objects
        logger.info(f"Seems like we should embed the serialized metadata {self.name}")

        has_prefetch_related_denormalized = self.has_prefetch_related_denormalized()
        metadatas = [
            (
                has_prefetch_related_denormalized
                and PrefetchProxy(m, self.prefetch_related)
                or m
            )
            for m in set(v for vs in relations.values() for v in vs)
        ]

        try:
            self.model._meta.get_field("last_update_status")
            has_update_status = True
        except FieldDoesNotExist:
            has_update_status = False
        # else:
        #     metadatas = metadatas.filter(last_update_status__in=['success', 'do-not-fetch'])

        usable_metadata = []
        empty_metadata = []
        for metadata in metadatas:
            if not has_update_status or metadata.last_update_status == "success":
                usable_metadata.append(metadata)
                logger.trace(
                    f"Serializing a populated metadata entry for {metadata.identifier} / {metadata!r}"
                )
            else:
                empty_metadata.append(metadata)
                logger.trace(
                    f"Serializing an unpopulated metadata entry for {metadata.identifier} / {metadata!r} / {getattr(metadata, 'last_update_status', 'no-status')}"
                )

        all_serialized = self.serializer(
            usable_metadata,
            context={"request": request, "config": self.config},
            many=True,
        ).data + [
            {"id": metadata.identifier, "populated": False}
            for metadata in empty_metadata
        ]

        for metadata, serialized in zip(
            usable_metadata + empty_metadata, all_serialized
        ):
            identifier = f"{self.plugin_name}:{metadata.identifier}"

            if self.metadata_embed_method in ["include", "relate"]:
                metadata.__config__ = self.config
                obj = JSONAPIObject(obj_type, identifier, metadata)
                obj.update(serialized)
            elif self.metadata_embed_method == "embed":
                obj = {"metadata:%s" % self.plugin_name: serialized}
            else:
                raise UnknownEmbedMethodException(
                    f"Unknown embed method: {self.metadata_embed_method!r}"
                )

            jsonapi_obj_mapping[identifier] = obj
            logger.trace(f"Created metadata object {identifier} with metadata")

        for listingitem_id, metadatas in relations.items():
            for metadata in metadatas:
                identifier = "%s:%s" % (self.plugin_name, metadata.identifier)
                if self.metadata_embed_method == "embed":
                    m = jsonapi_obj_mapping.get(identifier, {})
                    items[listingitem_id].update(m)
                elif self.metadata_embed_method in ["include", "relate"]:
                    if identifier not in jsonapi_obj_mapping:
                        metadata.__config__ = self.config
                        obj = JSONAPIObject(
                            obj_type, identifier, metadata, populated=False
                        )
                        jsonapi_obj_mapping[identifier] = obj
                        logger.trace(
                            f"Created metadata object {identifier} without metadata"
                        )

                    local = self.metadata_embed_method == "relate"
                    logger.trace(
                        f"Added relationship between listingitem_id:{listingitem_id} metadata_identifier:{identifier}"
                    )
                    items[listingitem_id].add_relationship(
                        obj_type, jsonapi_obj_mapping[identifier], local=local
                    )
                else:
                    raise UnknownEmbedMethodException(
                        f"Unknown embed method: {self.metadata_embed_method!r}"
                    )

    def get_prefetch_related_denormalized(self, metadata):
        def serialize_obj(obj):
            result = {"__str__": obj.__str__()}
            for field in obj._meta.get_fields(False):
                if not isinstance(field, Field):
                    continue

                if (
                    field.get_internal_type()
                    not in self.prefetch_related_denormalized_fields
                ):
                    continue

                field_name = field.name
                result[field_name] = getattr(obj, field_name)

            return result

        result = {}
        for field_name in self.prefetch_related:
            result[field_name] = []
            for obj in getattr(metadata, field_name).all():
                result[field_name].append(serialize_obj(obj))

        return result

    @command(
        "refresh_denormalized_cache",
        display_name="Refresh Denormalized Cache",
        description="Clear and rebuild cache used to speed up metadata serialization",
    )
    def refresh_all_prefetch_related_denormalized(self):
        for metadata in self.model.objects.filter(last_update_status="success"):
            metadata.prefetch_related_denormalized = self.get_prefetch_related_denormalized(
                metadata
            )
            metadata.save()
            logger.trace(
                f"Updated Prefetch Related Denormalized Cache for {metadata!r}"
            )


class GetMetadataStatsMixin:
    model = None
    metadata_resolution_link_model = None

    def get_stats(self):
        stats = []

        if self.model and issubclass(self.model, BaseUpdatable):
            for result in self.model.objects.values("last_update_status").annotate(
                Count("last_update_status")
            ):
                k = f"Model update status: {result['last_update_status']}"
                stats.append({"title": k, "value": result["last_update_status__count"]})

        if self.metadata_resolution_link_model and issubclass(
            self.metadata_resolution_link_model, BaseUpdatable
        ):
            for result in self.metadata_resolution_link_model.objects.values(
                "last_update_status"
            ).annotate(Count("last_update_status")):
                k = f"Resolution update status: {result['last_update_status']}"
                stats.append({"title": k, "value": result["last_update_status__count"]})

            m = self.metadata_resolution_link_model.objects.filter(
                last_update_status="success"
            )
            stats.append(
                {
                    "title": "Resolution resolved",
                    "value": m.filter(metadata__isnull=False).count(),
                }
            )
            stats.append(
                {
                    "title": "Resolution failed",
                    "value": m.filter(metadata__isnull=True).count(),
                }
            )

        return stats


class ResetFailedMixin:
    model = None
    metadata_resolution_link_model = None

    @command(
        display_name="Reset failed fetches",
        description="Retry fetching metadata for previously failed fetches",
    )
    def command_reset_failed_fetches(self):
        if not self.model or not issubclass(self.model, BaseUpdatable):
            return

        logger.debug(f"Requeuing failed for plugin {self.plugin_name}/{self.name}")
        self.model.objects.filter(
            last_update_status=BaseUpdatable.UPDATE_STATUS_FAILED
        ).update(last_update_status=BaseUpdatable.UPDATE_STATUS_PENDING)

        if hasattr(self, "schedule_update"):
            self.schedule_update()

    @command(
        display_name="Clear failed searches",
        description="Remove failed searches so the system can try searching for them again",
    )
    def command_clear_failed_searches(self):
        if not self.metadata_resolution_link_model or not issubclass(
            self.metadata_resolution_link_model, BaseMetadataResolutionLink
        ):
            return

        search_resolve = self.config.get("search_resolve")
        if not search_resolve:
            return

        logger.debug(
            f"Wiping all failed search resolves for resolver {search_resolve} plugin {self.plugin_name}/{self.name}"
        )
        self.metadata_resolution_link_model.objects.filter(
            search_resolve=search_resolve, metadata__isnull=True
        ).exclude(last_update_status=BaseUpdatable.UPDATE_STATUS_PENDING).delete()

        if hasattr(self, "schedule_update"):
            self.schedule_update()


class CoverSerializerMixin:
    def get_cover_url(self, obj):
        if obj.cover:
            request = self.context["request"]
            image_cache = self.context["config"]["image_cache"]
            return image_cache.get_image_url(request, obj.cover)
