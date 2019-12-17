import logging

from django.conf.urls import url
from unplugged import Schema, ServicePlugin

from .views import ImageCacheView

logger = logging.getLogger(__name__)


class ImageCacheServicePlugin(ServicePlugin):
    plugin_name = "imgcache"
    config_schema = Schema

    __traits__ = ["image_cache"]

    def get_urls(self):
        return [
            url("^(?P<imgcache_name>[-\w]+)/?$", ImageCacheView.as_view(service=self))
        ]
