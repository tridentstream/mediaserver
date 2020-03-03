from abc import abstractmethod

from unplugged import PluginBase


class MagnetResolverPlugin(PluginBase):
    plugin_type = "magnetresolver"

    @abstractmethod
    def magnet_to_torrent(self, magnet_link):
        """
        Turn a magnet link into the binary torrent data.
        """
