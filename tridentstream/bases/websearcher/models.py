import logging
from contextlib import contextmanager

import requests
import requests.utils
from django.db import models
from jsonfield import JSONField
from picklefield.fields import PickledObjectField

from ...locktracker import LockTracker
from ...utils import hash_string
from .bencode import bdecode, bencode

logger = logging.getLogger(__name__)
websession_locktracker = LockTracker()


class WebSessionManager(models.Manager):
    @contextmanager
    def get_session(self, app):
        logger.debug(f"Getting requests session for {app}")
        with websession_locktracker.get_path(app):
            session = requests.Session()
            try:
                obj = self.model.objects.get(app=app)
                session.cookies = requests.utils.cookiejar_from_dict(
                    obj.requests_cookies
                )
            except self.model.DoesNotExist:
                obj = self.model(app=app)

            yield session
            obj.requests_cookies = requests.utils.dict_from_cookiejar(session.cookies)
            obj.save()


class WebSession(models.Model):
    app = models.CharField(max_length=30, unique=True)
    requests_cookies = PickledObjectField()
    last_modified = models.DateTimeField(auto_now=True)

    objects = WebSessionManager()


class TorrentFile(models.Model):
    app = models.CharField(max_length=30)
    url = models.CharField(max_length=5000)
    url_hash = models.CharField(max_length=50)
    torrent_data = models.BinaryField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("app", "url_hash"),)

    def get_torrent_data(self):
        return bdecode(bytes(self.torrent_data))

    def get_infohash(self):
        return hash_string(bencode(self.get_torrent_data()[b"info"]))


class ListingCache(models.Model):
    app = models.CharField(max_length=30)
    search_token = models.CharField(max_length=50)
    path = models.CharField(max_length=500, default="")
    listing = JSONField()
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("app", "search_token", "path"),)


class AvailableMedia(models.Model):
    app = models.CharField(max_length=30)
    identifier = models.CharField(max_length=500)
    created = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = (("app", "identifier"),)
