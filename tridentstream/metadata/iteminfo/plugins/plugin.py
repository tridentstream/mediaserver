from abc import abstractmethod

from unplugged import PluginBase


class ItemInfoPlugin(PluginBase):
    plugin_type = "iteminfo"

    @abstractmethod
    def get_info(self, name):
        """
        Returns a dictionary with information about the name
        """
