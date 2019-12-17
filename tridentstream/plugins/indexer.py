import os
from abc import abstractmethod

from django.conf import settings
from unplugged import PluginBase


class PathIndexer:
    @abstractmethod
    def index(self, path, title):
        """
        Index a path.
        """

    @abstractmethod
    def commit(self):
        """
        Commit the writes.
        """

    @abstractmethod
    def delete(self, path):
        """
        Delete an index for a path
        """


class IndexerPlugin(PluginBase):
    plugin_type = "indexer"

    @abstractmethod
    def clear(self, parent_path):
        """
        Clear the index for a given parent_path.
        """

    @abstractmethod
    def get_writer(self, parent_path):
        """
        Get a writer for parent_path.
        """

    @abstractmethod
    def search(self, path, query):
        """
        Search for query in path.
        """

    def get_database_path(self, path):
        """Turn a relative into an absolute path and make sure it exists"""
        path = path or f"{self.plugin_type}_{self.name}"
        if not os.path.isabs(path):
            path = os.path.join(settings.DATABASE_ROOT, path)

        if not os.path.isdir(path):
            os.makedirs(path)

        return path
