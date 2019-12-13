from abc import abstractmethod

from unplugged import PluginBase


class ImageCachePlugin(PluginBase):
    plugin_type = "imagecache"

    @abstractmethod
    def get_image_path(self, url):
        """
        Return the path to the file stored locally.
        Should probably try to download it if it is not found locally
        """
        raise NotImplementedError

    @abstractmethod
    def get_image_url(self, request, url):
        """
        Create an url where the image can be reached
        """
        raise NotImplementedError
