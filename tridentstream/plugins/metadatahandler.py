from abc import abstractmethod, abstractproperty

from unplugged import PluginBase


class MetadataHandlerPlugin(PluginBase):
    plugin_type = "metadatahandler"

    @abstractproperty
    def linkable(self):
        """
        Should the metadata be linked with other metadata handlers.
        """
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self, request, identifier):
        """
        Returns an instance of matching metadata
        """
        raise NotImplementedError

    @abstractmethod
    def link_metadata_listingitems(self, listing_build, fetch_metadata=True):
        """
        Links metadata and listingitems.
        """
        raise NotImplementedError

    @abstractmethod
    def populate_metadata_jsonapi(self, request, root):
        """
        Adds metadata to a JSONAPI response.
        """
        raise NotImplementedError
