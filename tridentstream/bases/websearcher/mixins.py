import hashlib
import logging
from contextlib import contextmanager
from datetime import timedelta

from asgiref.sync import async_to_sync
from django.utils.timezone import now
from thomas import Item
from unplugged import command

from ...exceptions import PathNotFoundException
from ...plugins import SearcherFilter
from ...utils import urljoin
from .models import AvailableMedia, ListingCache, TorrentFile, WebSession

logger = logging.getLogger(__name__)


class FilterRewriteMixin:  # trident: site mapping
    field_rewrite = {}
    choices_rewrite = {}  # trident-field: {trident-choice: rewrite target}
    order_rewrite = {}

    postprocess_field = {}  # target field, what to do with various stuff

    @staticmethod
    def postprocess_flatten(joiner=","):
        def postprocess(v):
            if isinstance(v, list):
                return joiner.join(v)
            else:
                return v

        return postprocess

    @staticmethod
    def postprocess_pickfirst(items):
        if items:
            return items[0]

    def parse_search_query(self, search_query):
        result = {}

        for k, v in list(search_query.items()) + [("o", search_query.order_by)]:
            if k in self.choices_rewrite:
                if not isinstance(v, list):
                    v = [v]

                target_choices = []
                usable_choices = self.choices_rewrite[k]
                for choice in v:
                    c = usable_choices.get(choice)
                    if not c:
                        continue
                    target_choices.append(c)

                v = target_choices

            f = self.field_rewrite.get(k)
            if not f or not v:
                continue

            do_postprocess = True
            if isinstance(f, dict):
                do_postprocess = False
                for fk, fv in f.items():
                    if fv == "+":
                        f = fk
                        do_postprocess = True
                    else:
                        result[fk] = fv

            if f in self.postprocess_field and do_postprocess:
                v = self.postprocess_field[f](v)

            result[f] = v

        return self.postprocess_search_query(result)

    def postprocess_search_query(self, search_query):
        return search_query

    @property
    def filters(self):
        sf = SearcherFilter(self.field_rewrite.keys())

        for field, choices in self.choices_rewrite.items():
            sf.set_choices(field, choices.keys())

        for field in self.order_rewrite.keys():
            sf.add_order_by(field)

        return sf


class LoginMixin:
    base_url = None

    login_failure_delay = timedelta(hours=2)
    login_path = None
    login_test_path = None
    login_fields = (
        None  # list of fields to take from config, if tuple, use mapped field.
    )

    last_failure = None
    login_checked = False
    last_login_check = None
    login_check_delay = timedelta(hours=2)

    def check_site_usable(self, session):
        logger.info(f"Checking if {self.name} is usable")
        if (
            self.login_checked
            and self.last_failure
            and self.last_failure + self.login_failure_delay > now()
        ):
            raise PathNotFoundException()

        if self.login_checked or self.login_test(session):
            self.login_checked = True
            return

        self.login(session)

    def login(self, session):
        logger.info(f"Clearing session and logging in to {self.name}")
        session.cookies.clear()
        data = {}
        for field in self.login_fields:
            if isinstance(field, (list, tuple)):
                field, form_field = field
                if form_field.startswith("+"):
                    data[form_field[1:]] = self.config[field]
                else:
                    data[field] = form_field
            else:
                data[field] = self.config[field]

        url = urljoin(self.base_url, self.login_path)

        r = session.post(url, data=data, allow_redirects=False)

        if r.status_code not in [200, 302] or not self.login_test(session):
            logger.warning("Failed to login")
            self.last_failure = now()
            self.login_checked = False
            raise PathNotFoundException()

    def login_test(self, session):
        logger.info(f"Testing login at {self.name}")

        if (
            self.last_login_check
            and self.last_login_check + self.login_check_delay > now()
        ):
            return True

        url = urljoin(self.base_url, self.login_test_path)
        r = session.get(url, allow_redirects=False)
        if r.status_code == 200:
            self.last_login_check = now()
            return True
        else:
            self.last_login_check = None
            return False


class WebSessionMixin:
    @contextmanager
    def get_session(self):
        with WebSession.objects.get_session(self.name) as session:
            yield session


class TorrentMixin:
    last_failure = None

    def fetch_torrent_data(self, session, url):
        return session.get(url)

    def fetch_torrent(self, url):
        url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()
        try:
            tf = TorrentFile.objects.get(app=self.name, url_hash=url_hash)
        except TorrentFile.DoesNotExist:
            if url.startswith("magnet"):
                magnet_resolver = self.config.get("magnet_resolver")
                if not magnet_resolver:
                    raise PathNotFoundException()

                torrent_data = magnet_resolver.magnet_to_torrent(url)
                if not torrent_data:
                    raise PathNotFoundException()
            else:
                try:
                    with self.get_session() as session:
                        r = self.fetch_torrent_data(session, url)
                except:
                    logger.exception("Failed to fetch torrent")
                    raise PathNotFoundException()
                if r.status_code != 200:
                    self.last_failure = now()
                    raise PathNotFoundException()
                torrent_data = r.content

            tf = TorrentFile.objects.create(
                app=self.name, url_hash=url_hash, url=url, torrent_data=torrent_data
            )

        return tf

    def stream_torrent(self, client, torrent_file, path=None):
        infohash = torrent_file.get_infohash()

        return client.stream(infohash, torrent_file.torrent_data, path=path)

    def try_decode(self, value):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            logger.debug(f"Failed to decode {value} using UTF-8")

        return value.decode("iso-8859-1")

    def is_legal_path(self, path):
        for p in path:
            if p in [".", ".."] or "/" in p:
                return False
        return True

    def list_torrent(self, item, torrent_file):
        torrent = torrent_file.get_torrent_data()

        availability_metadata = item.get("metadata:availability")

        def get_folder(folders, item, path):
            if not path:
                return item

            if tuple(path) in folders:
                return folders[tuple(path)]

            parent_item = get_folder(folders, item, path[:-1])
            folders[tuple(path)] = folder_item = Item(id=path[-1])
            parent_item.add_item(folder_item)
            return folder_item

        if b"files" in torrent[b"info"]:  # multifile torrent
            folders = {}
            for f in torrent[b"info"][b"files"]:
                logger.trace("Handling torrent file %r" % (f,))
                path = [
                    self.try_decode(x) for x in f[b"path"] if x
                ]  # remove empty fragments
                if not self.is_legal_path(path):
                    logger.warning(f"Dangerous path {path!r} found, skipping")
                    continue

                name = path.pop()
                torrent_item = Item(id=name, attributes={"size": f[b"length"]})
                if availability_metadata:
                    torrent_item["metadata:availability"] = availability_metadata

                folder_item = get_folder(folders, item, path)
                folder_item.add_item(torrent_item)
        else:
            name = self.try_decode(torrent[b"info"][b"name"])
            if self.is_legal_path(name):
                torrent_item = Item(
                    id=name, attributes={"size": torrent[b"info"][b"length"]}
                )
                if availability_metadata:
                    torrent_item["metadata:availability"] = availability_metadata

                item.add_item(torrent_item)

        return item


class CacheSearchMixin:
    search_result_cache_time = timedelta(minutes=15)

    @command(
        name="clear_listing_cache",
        display_name="Clear listing caches",
        description="Removes listing caches for this plugin and forces a rebuild. This can break exisiting nested listings",
    )
    def clear_listing_cache(self):
        ListingCache.objects.filter(app=self.name).delete()

    def get_cache_results(self, search_token, path):
        try:
            listing_cache = ListingCache.objects.get(
                app=self.name, search_token=search_token, path=path
            )
        except ListingCache.DoesNotExist:
            logger.info(f"Unable to find listing for search_token:{search_token}")
            return

        return Item.unserialize(listing_cache.listing)

    def cache_search_result(self, search_token, path, listing):
        ListingCache.objects.filter(
            app=self.name, search_token=search_token, path=path
        ).delete()
        ListingCache(
            app=self.name,
            search_token=search_token,
            path=path,
            listing=listing.serialize(include_routes=True),
        ).save()
