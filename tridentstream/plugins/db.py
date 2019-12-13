import os
from abc import abstractmethod
from collections import MutableMapping

from django.conf import settings
from unplugged import PluginBase


class DatabasePlugin(PluginBase, MutableMapping):
    plugin_type = "database"

    @abstractmethod
    def sync(self):
        """
        Flush the changes to non-volatile storage.
        """

    @abstractmethod
    def close(self):
        """
        Close the database
        """

    def get_database_path(self, path):
        """Turn a relative into an absolute path and make sure it exists"""
        if not os.path.isabs(path):
            path = os.path.join(settings.DATABASE_ROOT, path)

        if not os.path.isdir(path):
            os.makedirs(path)

        return path


class DatabaseCacheLayer(MutableMapping):
    """Caches the communication with the actual database plugin"""

    def __init__(self, db):
        self._db = db
        self._clear()

    def _clear(self):
        self._cache_tainted = set()
        self._cache = {}
        self._cache_delete = set()

    def __getitem__(self, key):
        if key in self._cache_delete:
            raise KeyError(key)

        if key not in self._cache:
            self._cache[key] = self._db[key]

        return self._cache[key]

    def __setitem__(self, key, value):
        self._cache_delete.discard(key)
        self._cache_tainted.add(key)
        self._cache[key] = value

    def __delitem__(self, key):
        if key in self._cache:
            del self._cache[key]

        self._cache_tainted.discard(key)
        self._cache_delete.add(key)

    def __iter__(self):
        return self._db.__iter__()

    def keys(self):
        keys = self._db.keys()
        keys += [k for k in self._cache.keys() if k not in set(keys)]
        return keys

    def __len__(self):
        return self._db.__len__()

    def __contains__(self, key):
        return key not in self._cache_delete and (
            key in self._cache or self._db.__contains__(key)
        )

    def _flush_cache(self):
        for k in self._cache_tainted:
            self._db[k] = self._cache[k]

        for k in self._cache_delete:
            del self._db[k]

        self._clear()

    def sync(self):
        self._flush_cache()
        return self._db.sync()

    def close(self):
        self._flush_cache()
        return self._db.close()
