from abc import abstractmethod

from unplugged import PluginBase


class TagPlugin(PluginBase):
    plugin_type = "tag"

    @abstractmethod
    def tag_listingitem(self, config, user, listingitem, tag_name):
        """
        Tag a listingitem and its linkable metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def untag_listingitem(self, config, user, listingitem, tag_name):
        """
        Untag a listingitem and its linkable metadata.
        """
        raise NotImplementedError
