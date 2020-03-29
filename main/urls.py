import os

import django.contrib.admin
from django.conf import settings
from django.conf.urls import include, static, url
from django.contrib import admin
from django.urls import path, re_path

from tridentstream.utils import serve

urlpatterns = [
    path("djangoadmin/", admin.site.urls),
    url(r"^api-auth/", include("rest_framework.urls", namespace="rest_framework")),
    url(r"", include(("unplugged.urls", "unplugged"), namespace="unplugged")),
]
