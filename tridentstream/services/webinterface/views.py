import logging
import os

from django.http import HttpResponse
from django.views import View
from rest_framework import permissions

logger = logging.getLogger(__name__)


class IndexView(View):
    service = None
    permission_classes = (permissions.AllowAny,)

    def get(self, request, *args, **kwargs):
        index_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "static", "index.html"
        )
        if not os.path.isfile(index_file):
            return HttpResponse(
                "No webinterface bundled with this installation, sorry",
                content_type="text/plain",
            )

        with open(index_file, "r") as f:
            index_data = f.read()

        index_data = index_data.replace(
            '<base href="/">', f'<base href="/{self.service.name}/">'
        )

        return HttpResponse(index_data, content_type="text/html")
