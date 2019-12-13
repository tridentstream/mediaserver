import logging

from django.apps import AppConfig as DjangoAppConfig

logger = logging.getLogger(__name__)


class AppConfig(DjangoAppConfig):
    name = "tridentstream.services.imgcache"
    verbose_name = "ImgCache Service"
    label = "services_imgcache"

    def ready(self):
        try:
            from .handler import ImageCacheServicePlugin  # NOQA
            from .imgcache import ImgCachePlugin  # NOQA
        except ImportError:
            logger.exception("Unable to load image cache plugin, please install pillow")
