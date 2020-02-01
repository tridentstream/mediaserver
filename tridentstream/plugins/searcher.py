import json
import logging
import time
from abc import abstractmethod, abstractproperty

from unplugged import PluginBase, threadify

from twisted.internet import reactor

from ..utils import hash_string

logger = logging.getLogger(__name__)


class SearchQuery(dict):
    def __init__(self, searcher_filter, query):
        self.order_by = []

        for k, v in query.items():
            if k == "o":
                if isinstance(v, list):
                    self.order_by.extend(v)
                else:
                    self.order_by.append(v)
            else:
                if k not in searcher_filter.fields:
                    continue

                if k in searcher_filter.choices:
                    if not isinstance(v, list):
                        v = [v]

                    self.setdefault(k, [])
                    for val in v:
                        if val not in searcher_filter.choices[k]:
                            continue

                        self[k].append(val)
                else:
                    self[k] = v

    def get_hash(self):
        hash_string(json.dumps(sorted(self.items())))


class SearcherFilter:
    def __init__(self, fields):
        self.fields = fields
        self.choices = {}
        self.order_by = []

    def set_choices(self, field, choices):
        if field not in self.fields:
            logger.warning(f"Trying to set choices for unknown field {field}")

        self.choices[field] = choices

    def add_order_by(self, field):
        self.order_by.append(field)

    def serialize(self):
        if "o" in self.fields:
            logger.warning(
                'field "o" is added as search field. As it is used as order field, it will cause conflict.'
            )

        return {
            "fields": self.fields,
            "choices": self.choices,
            "order_by": self.order_by,
        }

    @classmethod
    def unserialize(cls, data):
        obj = cls(data["fields"])
        obj.choices = data["choices"]
        obj.order_by = data["order_by"]
        return obj

    def merge(self, searcher_filter):
        fields = list(set(self.fields + searcher_filter.fields))
        sf = SearcherFilter(fields)

        for key in set(searcher_filter.choices.keys() + self.choices.keys()):
            choices = list(
                set(searcher_filter.choices.get(key, []) + self.choices.get(key, []))
            )
            sf.set_choices(key, choices)

        for order_by in set(searcher_filter.order_by) & set(self.order_by):
            sf.add_order_by(order_by)

        return sf


class SearcherPlugin(PluginBase):
    plugin_type = "searcher"

    @abstractmethod
    def get_item(query_hash, search_query):
        """
        Return an item for this search query
        """
        raise NotImplementedError

    @abstractproperty
    def filters(self):
        """
        Returns instance of SearcherFilter.
        """
        raise NotImplementedError


class SearcherPluginManager:
    @staticmethod
    def get_item_multiple(
        plugins, query_hash, search_query
    ):  # get an item for all paths and merge into one
        item = None
        for plugin in plugins:
            plugin_item = plugin.get_item(query_hash, search_query)
            if item:
                item.merge(plugin_item)
            else:
                item = plugin_item

        item["modified"] = int(time.time())
        return item

    @staticmethod
    def get_item(plugin, query_hash, search_query):
        return SearcherPluginManager.get_item_multiple(
            [plugin], query_hash, search_query
        )

    @staticmethod
    def filters_multiple(plugins):
        threads = []
        for plugin in plugins:

            def get_filters(plugin):
                return plugin.filters

            threads.append((plugin, threadify(get_filters, cache_result=True)(plugin)))

        retval = None
        for plugin, thread in threads:
            filters = thread()
            if not filters:
                continue

            if retval is None:
                retval = filters
            else:
                retval.merge(filters)

        return retval
