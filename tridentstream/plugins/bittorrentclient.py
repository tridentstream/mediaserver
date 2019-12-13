from abc import abstractmethod

from unplugged import PluginBase


class BittorrentClientPlugin(PluginBase):
    plugin_type = "bittorrentclient"

    @abstractmethod
    def stream(self, info_hash, torrent_filelike_data, path=None):
        """
        Return a stream object to the file with given infohash,
        said torrent data and given file_path inside torrent.

        torrent_filelike_data must be a filelike object.
        empty file_path makes the client decide what to stream (most likely the biggest file).
        """
