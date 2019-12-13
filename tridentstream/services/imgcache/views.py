import mimetypes
import os

from django.core.signing import BadSignature, Signer
from django.http import Http404, HttpResponse
from PIL import Image as PImage
from rest_framework import permissions
from rest_framework.views import APIView

mimetypes.init()


class ImageCacheView(APIView):
    service = None

    permission_classes = (permissions.AllowAny,)

    def get(self, request, imgcache_name):
        url = request.GET.get("url")
        if not url:
            raise Http404

        signer = Signer()
        try:
            url = signer.unsign(url)
        except BadSignature:
            raise Http404

        for image_cache in self.service._related_plugins:
            if image_cache.name == imgcache_name:
                break
        else:
            raise Http404

        path = image_cache.get_image_path(url)
        if not path:
            raise Http404

        if "resize" in request.GET:
            resized_path = path.split(".")
            resized_path[-2] = resized_path[-2] + "_resized"
            resized_path = ".".join(resized_path)

            if not os.path.isfile(resized_path):
                i = PImage.open(path)

                if i.size[0] > 640 or i.size[1] > 640 * 2:
                    i.thumbnail((640, 640 * 2), PImage.ANTIALIAS)
                    i.save(resized_path, i.format)
                else:
                    os.link(path, resized_path)

            path = resized_path

        content_type, _ = mimetypes.guess_type(path)
        response = HttpResponse(content_type=content_type)
        response["X-Sendfile"] = path

        return response
