import logging
import time
import uuid

import rest_framework_filters as filters
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import Http404, HttpResponse
from django_filters.constants import EMPTY_VALUES
from rest_framework import serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from unplugged import (
    CommandBaseMeta,
    CommandViewMixin,
    JSONAPIObject,
    JSONAPIRoot,
    JSONSchema,
    Schema,
    command,
    fields,
)
from unplugged.models import Log

from ...stream import create_stream
from .models import ListingItem

logger = logging.getLogger(__name__)


class ViewState(dict):
    """
    Information about someone consuming something,
    e.g. current subtitle or timestamp.
    """

    def __init__(self, user, id):
        if not id:
            id = str(uuid.uuid4())

        self.id = id
        self.user = user

        self.callbacks = []
        self.player_connected = False

    def add_change_callback(self, fn):
        """
        Add plugin to inform about view state changes.
        """
        self.callbacks.append(fn)

    def do_callback(self):
        logger.debug("Doing viewstate callbacks")
        if self.player_connected:
            for fn in self.callbacks:
                fn(self)

    def update(self, values):
        super(ViewState, self).update(values)
        self.do_callback()

    def __setitem__(self, key, value):
        super(ViewState, self).__setitem__(key, value)
        self.do_callback()

    def __delitem__(self, key):
        super(ViewState, self).__delitem__(key)
        self.do_callback()

    def serialize(self):
        retval = {}
        retval.update(self)
        retval["id"] = self.id
        return retval


class LimitablePageNumberPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "limit"
    max_page_size = 1000


class CommandSerializer(serializers.Serializer):
    command = serializers.CharField()
    kwargs = serializers.DictField(required=False)


class TagSchema(Schema):
    handler = fields.String(required=True)
    tag_name = fields.String(required=True)


class DefaultFilterSet(filters.FilterSet):
    def __init__(self, data=None, *args, **kwargs):
        if data is not None and "defaults" in kwargs:
            defaults = kwargs.pop("defaults")
            # get a mutable copy of the QueryDict
            data = data.copy()

            for name, f in self.base_filters.items():
                default = defaults.get(name)

                # filter param is either missing or empty, use default
                if not data.get(name) and default:
                    data[name] = default

        super(DefaultFilterSet, self).__init__(data, *args, **kwargs)


class AggregatedOrderingFilter(filters.OrderingFilter):
    def __init__(self, *args, **kwargs):
        """
        ``field_aggregation`` Tuple of how to aggregate this field
        """
        self.field_aggregation = kwargs.pop("field_aggregation", {})
        super(AggregatedOrderingFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs

        ordering = []
        for param in value:
            descending = param.startswith("-")
            param = param[1:] if descending else param
            field_name = self.param_map.get(param, param)

            if field_name in self.field_aggregation:
                agg_name = "_agg_%s" % (field_name,)
                m = self.field_aggregation[field_name][descending]
                qs = qs.annotate(**{agg_name: m(field_name)})
                field_name = agg_name

            ordering.append("-%s" % field_name if descending else field_name)

        return qs.order_by(*ordering)


class BaseListingView(
    APIView, PermissionRequiredMixin, CommandViewMixin, metaclass=CommandBaseMeta
):
    """
    Builds a listing view and returns it. The view also handles streaming of files.
    """

    pagination_class = LimitablePageNumberPagination
    service = None
    listing_builder = None

    def get(self, request, path):
        """
        List a folder or item
        """
        path = path.strip("/")
        if path == "":
            logger.info("Root path, should just get listing configuration")
            return Response(self.get_config_view(request))

        path = self.get_path(request, path)

        config = self.service.get_path_config(path)
        logger.debug(f"Using config {config!r}")

        if config is None or "level" not in config:
            listingitem = self.listing_builder.get_item(path)
            if not listingitem:
                raise Http404

            if not listingitem.is_root:
                config, parent_path = self.service.get_nearest_config(path)
                if config["level"].get("sub_content_type"):
                    config["level"]["content_type"] = config["level"][
                        "sub_content_type"
                    ]
                config["parent_level_config"] = config["level"]
                listing = self.serialize_listing(
                    request, config, None, [listingitem], {}, {}
                )
                return Response(listing)

        do_not_rebuild = False
        current_page = request.GET.get(self.pagination_class.page_query_param, "1")
        logger.debug(
            f"Rebuild automatically status rebuild_automatically:{config.get('rebuild_automatically')} current_level:{config.get('current_level')} page:{current_page}"
        )
        if (
            current_page != "1"
            and config.get("rebuild_automatically")
            and config.get("current_level") == 0
        ):
            do_not_rebuild = True

        listing_item_root = self.listing_builder.get_listing(
            config, path, use_background_recheck=True, do_not_rebuild=do_not_rebuild
        )
        if not listing_item_root:
            raise Http404

        listingitems, links, meta = self.filter_and_paginate_listing(
            request, config, listing_item_root
        )
        listing = self.serialize_listing(
            request, config, listing_item_root, listingitems, links, meta
        )

        return Response(listing)

    def get_path(self, request, path):
        """
        Allows for internal path rewrite.
        """
        return path

    def serialize_listing(
        self, request, config, listing_item_root, listingitems, links, meta
    ):
        """
        Serializes listingitems related to root.
        """
        root = JSONAPIRoot()
        root.links.update(links)
        root.meta.update(meta)

        root.meta["content_type"] = config["level"].get("content_type", "")

        tag_info_objs = self.get_tag_info(config["level"])
        commands_obj = self.get_jsonapi_commands()

        def add_commands(obj, commands):
            for command_obj in commands:
                if command_obj._original_object.metadata.get("usable", "all") in [
                    "all",
                    obj.type,
                ]:
                    obj.add_relationship("metadata_commands", command_obj)

        if listing_item_root:
            parent = JSONAPIObject(
                listing_item_root.item_type,
                listing_item_root.get_full_path(),
                listing_item_root,
            )
            parent.update(listing_item_root.attributes)

            root.meta["parent"] = {"type": parent.type, "id": parent.id}

            root.add_included(parent)

            if config["parent_level_config"]:
                for metadata_handler in config["parent_level_config"][
                    "metadata_handlers"
                ]:
                    logger.debug(
                        f"Finding metadata from metadata handler {metadata_handler.name} for parent"
                    )
                    metadata_handler.populate_metadata_jsonapi(request, root)
                    logger.debug(
                        f"Finished metadata from metadata handler {metadata_handler.name}"
                    )

            add_commands(parent, commands_obj)

            self.add_additional_parent_relationships(
                parent, request, config, listing_item_root
            )

            for tag_info_obj in tag_info_objs:
                parent.add_relationship("metadata_tag", tag_info_obj)
        else:
            parent = None

        if config["edge_type"] == "folder":
            next_level_config = config["levels"][config["current_level"] + 1]
            tag_info_objs = self.get_tag_info(next_level_config)
        else:
            tag_info_objs = None

        for listingitem in listingitems:
            obj = JSONAPIObject(
                listingitem.item_type, listingitem.get_full_path(), listingitem
            )
            attributes = listingitem.attributes

            obj.update(attributes)
            obj["datetime"] = listingitem.datetime
            root.append(obj)

            if parent:
                obj.add_relationship("parent", parent)
            add_commands(obj, commands_obj)

            if tag_info_objs:
                for tag_info_obj in tag_info_objs:
                    obj.add_relationship("metadata_tag", tag_info_obj)

        for metadata_handler in config["level"]["metadata_handlers"]:
            logger.debug(
                f"Finding metadata from metadata handler {metadata_handler.name}"
            )
            start_time = time.time()
            metadata_handler.populate_metadata_jsonapi(request, root)
            logger.debug(
                f"Finished metadata from metadata handler {metadata_handler.name} it took {time.time() - start_time}"
            )

        if "parent" not in root.meta and root.data:
            obj = root.data[0]
            root.meta["parent"] = {"type": obj.type, "id": obj.id}

        return root.serialize(request)

    def add_additional_parent_relationships(
        self, parent, request, config, listing_item_root
    ):
        """
        If more relations needs to be added to the parent object
        """

    def serialize_filter(self, filter_, has_indexer=False):
        """
        Serializes a filter so it can be added to a JSONAPI response for the client to understand and use.
        """

        def expand_filter(filter_, choices, order_by, prefix=None):
            keys = []
            for base_name, field in filter_.base_filters.items():
                if "__" in base_name:
                    continue

                if prefix:
                    name = f"{prefix}__{base_name}"
                else:
                    name = base_name

                if isinstance(field, filters.RelatedFilter):
                    keys += expand_filter(field.filterset, choices, order_by, name)
                elif isinstance(field, filters.OrderingFilter):
                    if prefix is None:
                        order_by.extend([x[0] for x in field.extra["choices"]])
                else:
                    keys.append(name)

                if (
                    hasattr(filter_.Meta, "include_related")
                    and base_name in filter_.Meta.include_related
                ):
                    field = filter_.base_filters[base_name].field_name
                    choices[name] = [
                        x
                        for x in filter_.Meta.model.objects.distinct()
                        .values_list(field, flat=True)
                        .order_by(field)
                        if x
                    ]

            return keys

        choices = {}
        order_by = []
        fields = expand_filter(filter_, choices, order_by)
        if has_indexer:
            fields.append("q")

        return {
            "fields": fields,
            "order_by": [o for o in order_by if o],
            "choices": choices,
        }

    def get_tag_info(self, level_config):
        """
        Create tag to be added as relation to reply. Makes it possible to tag metadata.
        """
        tags = []
        for tag in level_config.get("tags", []):
            obj = JSONAPIObject("metadata_tag", tag.name)
            obj["plugin_name"] = tag.plugin_name

            tags.append(obj)

        return tags

    def get_level_filter_info(self, name, level_config):
        """
        Create filterinfo to be added as relation to reply. Makes it possible to create
        a rich search interface.
        """
        obj = JSONAPIObject("metadata_filterinfo", name)

        metadata_handlers = level_config.get("metadata_handlers", [])
        obj["metadata_handlers"] = [
            f"metadata_{mh.plugin_name}" for mh in metadata_handlers
        ]

        filter_ = self.create_filter(metadata_handlers)
        obj["filter"] = self.serialize_filter(
            filter_, has_indexer=bool(level_config.get("indexer"))
        )

        content_type = level_config.get("content_type")
        if content_type:
            obj["content_type"] = content_type

        return obj

    def get_config_view(self, request):
        """
        Returns the configuration for this listingview. Can be used by clients to setup the correct
        sections etc.
        """
        raise NotImplementedError()

    def create_filter(self, metadata_handlers):
        """
        Creates the filter that can be used to filter the queryset.
        """
        f = {}
        order_by_mapping = {"path": "path", "datetime": "datetime"}
        order_by_aggregate = {}
        user_fields = []
        for metadata_handler in metadata_handlers:
            logger.debug("Checking %s for filter" % metadata_handler.name)
            if hasattr(metadata_handler, "filter") and metadata_handler.filter:
                name = f"metadata_{metadata_handler.plugin_name}"
                filter_name = f"metadata_{metadata_handler.plugin_name}"
                logger.debug(f"Adding {name} to filter")
                f[name] = filters.RelatedFilter(
                    metadata_handler.filter,
                    queryset=metadata_handler.listing_item_relation_model.objects.all(),
                )

                filter_order_by_aggregate = getattr(
                    metadata_handler.filter.Meta, "order_by_aggregate", {}
                )
                if hasattr(metadata_handler.filter.Meta, "order_by"):
                    for key in metadata_handler.filter.Meta.order_by or []:
                        logger.debug(f"Found ordering key {key}")
                        field = metadata_handler.filter.base_filters[key]
                        aggregators = filter_order_by_aggregate.get(key)

                        key = "%s__%s" % (name, key)
                        target = "%s__%s" % (filter_name, field.field_name)
                        order_by_mapping[target] = key
                        if aggregators:
                            order_by_aggregate[target] = aggregators

                if hasattr(metadata_handler.filter.Meta, "user_field"):
                    user_fields.append(
                        (
                            "%s__" % (name,),
                            "%s__%s" % (name, metadata_handler.filter.Meta.user_field),
                        )
                    )

        logger.info(f"SectionsFilter built with {len(f)} keys")

        f["o"] = AggregatedOrderingFilter(
            fields=order_by_mapping.items(), field_aggregation=order_by_aggregate
        )

        class Meta:
            model = ListingItem
            fields = ["path", "datetime"]

        Meta.user_fields = user_fields
        f["Meta"] = Meta

        filter_ = type("MetadataFilter", (DefaultFilterSet,), f)

        return filter_

    def filter_and_paginate_listing(self, request, config, listing_item_root):
        qs = listing_item_root.listingitem_set.all().distinct()

        indexer = config["level"].get("indexer")
        if indexer and "q" in request.GET:
            paths = indexer.search(listing_item_root.path, request.GET["q"])
            qs = qs.filter(path__in=paths)

        filter_ = self.create_filter(config["level"]["metadata_handlers"])
        ordering = request.GET.get("o") or config["level"].get("default_ordering", "")
        listingitems = filter_(request.GET, queryset=qs, defaults={"o": ordering}).qs
        for k in list(request.GET.keys()) + ordering.split(","):
            for prefix, field in filter_.Meta.user_fields:
                if k.startswith(prefix):
                    listingitems = listingitems.filter(**{field: request.user})
        page, listingitems = self.paginate_queryset(listingitems)

        seen = set()
        seen_add = seen.add
        listingitems = [x for x in listingitems if not (x in seen or seen_add(x))]

        page_links = {}
        next_page = page.get_next_link()
        if next_page:
            logger.debug("Found next page")
            page_links["next"] = next_page

        prev_page = page.get_previous_link()
        if prev_page:
            logger.debug("Found previous page")
            page_links["prev"] = prev_page

        meta = {
            "count": page.page.paginator.count,
            "num_pages": page.page.paginator.num_pages,
            "page": page.page.number,
            "limit": page.page.paginator.per_page,
        }

        return listingitems, page_links, meta

    @command("stream", metadata={"usable": "file"}, display_name="Stream")
    def stream(self, request, config, listingitem):
        item = listingitem.get_original_item()

        streamresult = create_stream(item, request)

        # UserActionLog.objects.log_plugin(self.service, request.user, 'Stream started by %s' % (request.user, ),
        #                                  'Stream for %s started by %s' % (item.path, request.user))
        with Log.objects.start_chain(
            self.service, "USER.STREAM_START", user=request.user
        ) as log:
            log.log(0, f"Trying to stream {item.path}")

            viewstate = ViewState(request.user, request.GET.get("viewstate"))
            root = JSONAPIRoot()

            for history_plugin in config.get("histories", []):
                logger.debug(f"Logging history to {history_plugin.name}")
                history_plugin.log_history(config, listingitem, viewstate)

            viewstate_obj = JSONAPIObject("viewstate", viewstate.id)
            viewstate_obj.update(viewstate)
            root.append(viewstate_obj)

            player_service = self.service.config.get("player_service")
            player_id = self.request.GET.get("target")
            if player_id and player_service:
                payload = streamresult.serialize(request)
                player_service.play(payload, viewstate, player_id)

            root.append(streamresult.to_jsonapi(request))

            return Response(root.serialize(request))

    def get_tag_plugin(self, config, handler):
        tag_handlers = [x for x in config["level"].get("tags", []) if x.name == handler]
        if not tag_handlers:
            return None

        return tag_handlers[0]

    @command(schema=TagSchema)
    def command_tag(self, request, config, listingitem, handler, tag_name):
        tag_plugin = self.get_tag_plugin(config, handler)
        if not tag_plugin:
            jsonapi_root = JSONAPIRoot.error_status(
                id_="invalid_tag", detail=f"Tag {handler!r} is not a known tag"
            )
            return Response(
                jsonapi_root.serialize(request), status=status.HTTP_400_BAD_REQUEST
            )

        tag_plugin.tag_listingitem(config, request.user, listingitem, tag_name)
        return Response(
            JSONAPIRoot.success_status("Item tagged successfully").serialize(request)
        )

    @command(schema=TagSchema)
    def command_untag(self, request, config, listingitem, handler, tag_name):
        tag_plugin = self.get_tag_plugin(config, handler)
        if not tag_plugin:
            jsonapi_root = JSONAPIRoot.error_status(
                id_="invalid_tag", detail=f"Tag {handler!r} is not a known tag"
            )
            return Response(
                jsonapi_root.serialize(request), status=status.HTTP_400_BAD_REQUEST
            )

        tag_plugin.untag_listingitem(config, request.user, listingitem, tag_name)
        return Response(
            JSONAPIRoot.success_status("Item untagged successfully").serialize(request)
        )

    def post(self, request, path):
        """
        Do stuff to an item.
        """
        path = path.strip("/")
        path = self.get_path(request, path)

        config, parent_path = self.service.get_nearest_config(path)

        logger.info(f"Trying to get listingitem for path {path!r}")

        if config is None:
            raise Http404

        try:
            listingitem = ListingItem.objects.get(app=self.service.name, path=path)
        except ListingItem.DoesNotExist:
            raise Http404

        kwargs = {"request": request, "config": config, "listingitem": listingitem}

        return self.call_command(request, self, kwargs)

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, "_paginator"):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None
        return (
            self.paginator,
            self.paginator.paginate_queryset(queryset, self.request, view=self),
        )
