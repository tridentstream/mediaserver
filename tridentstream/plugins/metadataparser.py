from abc import abstractmethod, abstractproperty

from unplugged import PluginBase

from ..vfs import DatabaseType


class MetadataParserPlugin(PluginBase):  # add context manager
    plugin_type = "metadataparser"

    @abstractproperty
    def pattern(self):
        """
        Regular expression to match against files.
        """
        raise NotImplementedError

    @abstractmethod
    def handle(self, vfs, virtual_path, actual_path):
        """
        Tries to find metadata from a file and set it somewhere.
        """
        raise NotImplementedError

    def set_metadata_parent_path(self, vfs, virtual_path, key, value):
        parent_path = "/".join(virtual_path.split("/")[:-1])
        metadata = {f"metadata:{self.name}:{key}": value}
        vfs.update_metadata(DatabaseType.DIRECTORY, parent_path, metadata)
