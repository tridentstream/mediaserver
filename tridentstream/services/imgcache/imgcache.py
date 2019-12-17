import io
import logging
from urllib.parse import quote_plus

import requests
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.signing import Signer
from unplugged import RelatedPluginField, Schema, ServicePlugin

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
        if cache.get(f"imgcache:{self.name}:{url}") == "F":
            return None

        ext = url.split("?")[0].split(".")[-1].lower()
        if ext not in ALLOWED_FILE_EXTENSIONS:
            logger.warning(f"Unknown file-extension: {ext}")
            return None

        filename = f"{hash_string(url)}.{ext}"
        path = f"{self.plugin_name}_{self.name}/{filename}"

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
                cache.set(f"imgcache:{self.name}:{url}", "F", 30 * 60)
                logger.warning(f"Failed to fetch url {url}")
                return None

            logger.debug(f"Saving {url} to {path}")

            default_storage.save(path, io.BytesIO(r.content))

        return default_storage.path(path)

    def get_image_url(self, request, url):
        signer = Signer()
        signed_url = signer.sign(url)
        result_path = f"/{self.config['image_server'].name}/{self.name}?url={quote_plus(signed_url)}"

        return request.build_absolute_uri(result_path)

    def unload(self):
        pass
