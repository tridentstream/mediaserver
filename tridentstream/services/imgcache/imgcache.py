import io
import logging

import requests

from urllib.parse import quote_plus

from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.signing import Signer

from unplugged import RelatedPluginField, ServicePlugin, Schema
from ...plugins import ImageCachePlugin
from ...utils import hash_string

logger = logging.getLogger(__name__)

ALLOWED_FILE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


class ImgCachePluginSchema(Schema):
    image_server = RelatedPluginField(plugin_type=ServicePlugin, traits=["image_cache"])


class ImgCachePlugin(ImageCachePlugin):
    plugin_name = "imgcache"

    config_schema = ImgCachePluginSchema

    def get_image_path(self, url):
        if cache.get("imgcache:%s:%s" % (self.name, url)) == "F":
            return None

        ext = url.split("?")[0].split(".")[-1].lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            logger.warning("Unknown file-extension: %s" % (ext,))
            return None

        filename = "%s.%s" % (hash_string(url), ext)
        path = "%s_%s/%s" % (self.plugin_name, self.name, filename)

        if not default_storage.exists(path):
            request_failed = False
            try:
                r = requests.get(url, verify=False, timeout=8)
            except requests.exceptions.RequestException:
                logger.warning("Requests errored out")
                request_failed = True
            else:
                if r.status_code != 200:
                    request_failed = True

            if request_failed:
                cache.set("imgcache:%s:%s" % (self.name, url), "F", 30 * 60)
                logger.warning("Failed to fetch url %s" % (url,))
                return None

            logger.debug("Saving %s to %s" % (url, path))

            default_storage.save(path, io.BytesIO(r.content))

        return default_storage.path(path)

    def get_image_url(self, request, url):
        signer = Signer()
        signed_url = signer.sign(url)
        result_path = "/%s/%s?url=%s" % (
            self.config["image_server"].name,
            self.name,
            quote_plus(signed_url),
        )

        return request.build_absolute_uri(result_path)

    def unload(self):
        pass
