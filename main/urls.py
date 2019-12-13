import os

import django.contrib.admin

from django.conf.urls import include, static, url
from django.conf import settings
from django.contrib import admin
from django.urls import path, re_path

from tridentstream.utils import serve

urlpatterns = [
    path("djangoadmin/", admin.site.urls),
    url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    re_path(
        r"^%s(?P<path>.*)$" % (settings.STATIC_URL.lstrip("/"),),
        serve,
        {
            "document_root": os.path.join(
                os.path.dirname(django.contrib.admin.__file__), "static"
            )
        },
    ),
    url(r"", include(("unplugged.urls", "unplugged"), namespace="unplugged")),
]
