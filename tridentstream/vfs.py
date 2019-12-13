import time
from collections import defaultdict

from thomas import Item, router

from .exceptions import PathNotFoundException
from .plugins import DatabaseCacheLayer
from .utils import hash_string

COMMIT_COUNTER = 10000  # listing entries before adding to work queue
BUCKET_SIZE = 1  # bytes,
GC_DELETED_FILES = 60 * 60 * 24 * 30  # seconds


class AlreadyInSessionException(Exception):
    """There's a session already in progress, only one session at a time"""


class NotInSessionException(Exception):
    """Must always be in session when modifying the database"""


class DatabaseType:
    FILE = "\x00"
    DIRECTORY = "\x01"
    BUCKET = "\x02"
    FILELIST = "\x03"
    NEW_BUCKET = "\x04"
    DELETED_BUCKET = "\x05"

    _mapping = {"\x00": "file", "\x01": "folder"}

    @staticmethod
    def to_str(database_type):
        return DatabaseType._mapping[database_type]


def cleanup_path(path):
    if type(path) is list:
        return [cleanup_path(p) for p in path]
    else:
        return path.strip("/")


def keyify(key_type, path):
    return "%s%s" % (key_type, hash_string(cleanup_path(path)))


def merge_set_dicts(result, merge_with):
    for k, v in merge_with.items():
        result[k] |= v


def generate_buckets(bucket_depth=BUCKET_SIZE):
    for i in [chr(x) for x in range(256)]:
        if bucket_depth > 1:
            for j in generate_buckets(bucket_depth - 1):
                yield i + j
        else:
            yield i


def compare_dicts(src, dst):
    """Checks if all keys in src matches the values in dst"""
    for k, v in src.items():
        if k not in dst or v != dst[k]:
            return False

    return True


class FileSystem:
    _in_session = False
    _delete_missing_items = False
    _always_trigger_new = False
    _current_time = None

    def __init__(self, db):
        self.db = DatabaseCacheLayer(db)
        self.events = {
            "new": [],
            "deleted": [],
            "db_closed": [],
            "file_route_needed": [],
            "list_route_needed": [],
            "on_item": [],
        }

        self.initialize_database()
        self.reset_session()

    def add_event(self, event, f):
        self.events[event].append(f)

    def _trigger_event(self, event_name, *args, **kwargs):
        for event in self.events.get(event_name, []):
            event(*args, **kwargs)

    def close(self):
        self._trigger_event("db_closed")

    def initialize_database(self):
        for bucket in generate_buckets():
            key = "%s%s" % (DatabaseType.BUCKET, bucket)
            if key not in self.db:
                self.db[key] = set()

            key = "%s%s" % (DatabaseType.DELETED_BUCKET, bucket)
            if key not in self.db:
                self.db[key] = set()

            key = "%s%s" % (DatabaseType.NEW_BUCKET, bucket)
            self.db[key] = set()

        key = keyify(DatabaseType.DIRECTORY, "")
        if key not in self.db:
            self.db[key] = {"path": "", "date": 0}

            filelist_key = keyify(DatabaseType.FILELIST, "")
            self.db[filelist_key] = set()

    def reset_session(self):
        """
        Resets buckets to allow deleting files missing from the new session.

        This can be used to update a listing with new stuff and remove things not there anymore.
        """

        self.reset_buckets()
        self.reset_keys()

    def commit_session(self):
        """
        After a scan is done, this commits the new bucket session as the current bucket session.
        """

        self.commit_buckets()
        self.commit_keys()
        self.db.sync()

    def session(self, complete=False, always_trigger_new=False, current_time=None):
        self._delete_missing_items = complete
        self._always_trigger_new = always_trigger_new
        self._current_time = current_time
        return self

    def __enter__(self):
        """This should only be used"""
        if self._in_session:
            raise AlreadyInSessionException()

        self._current_time = (
            isinstance(self._current_time, int)
            and self._current_time
            or int(time.time())
        )
        self._in_session = True
        self.reset_session()

    def __exit__(self, type, value, traceback):
        self.commit_session()
        self.finish_buckets()
        self._delete_missing_items = False
        self._always_trigger_new = False
        self._current_time = None
        self._in_session = False

    def finish_buckets(self):
        deleted_paths = []
        for bucket in generate_buckets():
            new_key = "%s%s" % (DatabaseType.NEW_BUCKET, bucket)
            cur_key = "%s%s" % (DatabaseType.BUCKET, bucket)
            zombie_key = "%s%s" % (DatabaseType.DELETED_BUCKET, bucket)
            new_hashes = self.db[new_key]
            cur_hashes = self.db[cur_key] if not self._always_trigger_new else set()
            zombie_hashes = self.db[zombie_key]

            for key in new_hashes - cur_hashes:
                m = self.db[key]
                self._trigger_event(
                    "new", key=key, db_type=DatabaseType.to_str(key[0]), metadata=m
                )
                self.db[key] = m

            if self._delete_missing_items:
                deleted_hashes = cur_hashes - new_hashes

                for key in deleted_hashes:
                    m = self.db[key]
                    m["deleted"] = self._current_time
                    self._trigger_event(
                        "deleted",
                        key=key,
                        db_type=DatabaseType.to_str(key[0]),
                        metadata=m,
                    )
                    self.db[key] = m
                    deleted_paths.append(m["path"])

                self.db[cur_key] = new_hashes

                zombie_remove_keys = set()
                for key in zombie_hashes:
                    m = self.db[key]
                    if (
                        "deleted" in m
                        and m["deleted"] < self._current_time - GC_DELETED_FILES
                    ):
                        self._remove_key(key, m)
                        zombie_remove_keys.add(key)
                zombie_hashes -= zombie_remove_keys

                self.db[zombie_key] = (cur_hashes - new_hashes) | (
                    zombie_hashes - new_hashes
                )
            else:
                self.db[cur_key] = new_hashes | cur_hashes

            self.db[new_key] = set()

        last_touched_path = None
        for path in sorted(deleted_paths):
            if last_touched_path is not None and path.startswith(last_touched_path):
                continue

            self.add_parent_path_touched(path, self._current_time)
            last_touched_path = path

        if last_touched_path is not None:
            self.commit_keys()

        self.db.sync()

    def _remove_key(self, key, metadata):
        del self.db[key]
        if key[0] == DatabaseType.DIRECTORY:
            filelist_key = DatabaseType.FILELIST + key[1:]
            del self.db[filelist_key]

        p = "/".join(metadata["path"].split("/")[:-1])
        parent_filelist_key = keyify(DatabaseType.FILELIST, p)

        if parent_filelist_key in self.db:
            self.db[parent_filelist_key].remove(key)
            self.db[parent_filelist_key] = self.db[parent_filelist_key]

    def reset_keys(self):
        self._touched_keys = defaultdict(int)
        self._filelists = defaultdict(set)

    def reset_buckets(self):
        self._buckets = defaultdict(set)
        self._uncommitted_changes = 0

    def commit_keys(self):
        for key, modified in self._touched_keys.items():
            m = self.db[key]
            if m.get("modified", 0) < modified:
                m["modified"] = modified
                self.db[key] = m

        for key, hashes in self._filelists.items():
            self.db[key] |= hashes

    def commit_buckets(self):
        for bucket, hashes in self._buckets.items():
            key = "%s%s" % (DatabaseType.NEW_BUCKET, bucket)
            self.db[key] = self.db[key] | hashes

        self.reset_buckets()

    def add_hash_to_bucket(self, h):
        if not self._in_session:
            raise NotInSessionException()

        bucket = h[1 : 1 + BUCKET_SIZE]

        self._buckets[bucket].add(h)
        self._uncommitted_changes += 1

    def add_parent_path_touched(self, path, modified_time):
        split_path = [x for x in path.split("/") if x]
        if len(split_path) <= 1:
            return

        split_path.pop()
        while True:
            key = keyify(DatabaseType.DIRECTORY, "/".join(split_path))
            self._touched_keys[key] = max(self._touched_keys[key], modified_time)
            if not split_path:
                break
            split_path.pop()

    def add_hash_to_parent_dir(self, path, h):
        split_path = [x for x in path.split("/") if x]
        split_path.pop()

        parent_key = keyify(DatabaseType.FILELIST, "/".join(split_path))
        self._filelists[parent_key].add(h)

    def check_for_commit(self):
        if self._uncommitted_changes >= COMMIT_COUNTER:
            self.commit_session()
            self.reset_session()

    def _add_item(self, key_type, path, add_time, metadata=None):
        key = keyify(key_type, path)
        is_modified = False

        m = self.db.get(key)
        if not m:
            m = {"path": path, "date": add_time, "modified": add_time}
            is_modified = True

            if key_type == DatabaseType.DIRECTORY:
                filelist_key = keyify(DatabaseType.FILELIST, path)
                self.db[filelist_key] = set()

        if metadata and not compare_dicts(metadata, m):
            m.update(metadata)
            is_modified = True

        if "deleted" in m:
            del m["deleted"]
            is_modified = True

        if is_modified:
            self.add_parent_path_touched(path, add_time)
            m["modified"] = add_time

            self.add_hash_to_parent_dir(path, key)

            self.db[key] = m

        self.add_hash_to_bucket(key)

        self.check_for_commit()

    def add_file(self, path, size, add_time, metadata=None):
        assert self._in_session, "Not in session"

        metadata = metadata or {}
        metadata["size"] = size
        self._add_item(DatabaseType.FILE, path, add_time, metadata)

    def add_dir(self, path, add_time, metadata=None):
        assert self._in_session, "Not in session"

        metadata = metadata or {}
        self._add_item(DatabaseType.DIRECTORY, path, add_time, metadata)

    def last_modified(self, path):
        path = cleanup_path(path)

        key = keyify(DatabaseType.DIRECTORY, path)
        if key not in self.db:
            key = keyify(DatabaseType.FILE, path)
            if key not in self.db:
                raise PathNotFoundException()
        metadata = self.db[key]

        return metadata["modified"] if "modified" in metadata else metadata["date"]

    def update_metadata(self, db_type, path, metadata):
        assert self._in_session, "Not in session"

        key = keyify(db_type, path)
        m = self.db.get(key, None)
        if m is None:
            raise PathNotFoundException()

        modified = False
        for k, v in metadata.items():
            if m.get(k) != v:
                modified = True

        if modified:
            m.update(metadata)
            self.db[key] = m

            if "modified" not in metadata:
                self.add_parent_path_touched(path, self._current_time)

    def get_metadata(self, db_type, path):
        m = self.db.get(keyify(db_type, path), None)
        if m is None:
            raise PathNotFoundException()
        return m

    def _list_dir(self, parent_folder, path, depth, show_deleted):
        filelist_key = keyify(DatabaseType.FILELIST, path)

        for key in self.db[filelist_key]:
            item_type = key[0]
            metadata = self.db[key].copy()

            if not show_deleted and metadata.get("deleted", False):
                continue

            item_path = metadata["path"]
            item = Item(id=item_path.split("/")[-1], attributes=metadata, router=router)
            parent_folder.add_item(item)

            if item_type == DatabaseType.DIRECTORY:
                if depth:
                    item.initiate_nested_items()
                    self._list_dir(item, item_path, depth - 1, show_deleted)
                else:
                    item.expandable = True
                    self._trigger_event("list_route_needed", item=item, path=item_path)
            elif item_type == DatabaseType.FILE:
                item.readable = True
                self._trigger_event("file_route_needed", item=item, path=item_path)

            self._trigger_event("on_item", item=item, path=item_path)

        parent_folder.nested_items.sort(key=lambda x: x.id)

    def list_dir(self, path, depth=0, show_deleted=False):
        path = cleanup_path(path)

        key = keyify(DatabaseType.DIRECTORY, path)
        if key not in self.db:
            raise PathNotFoundException()
        metadata = self.db[key].copy()

        item_path = metadata["path"]
        item = Item(id=metadata["path"].split("/")[-1], attributes=metadata)

        if depth >= 0:
            item.initiate_nested_items()
            self._list_dir(item, path, depth, show_deleted)
        else:
            item.expandable = True
            self._trigger_event("list_route_needed", item=item, path=item_path)

        self._trigger_event("on_item", item=item, path=item_path)

        return item

    def list_file(self, path):
        path = cleanup_path(path)

        key = keyify(DatabaseType.FILE, path)
        if key not in self.db:
            raise PathNotFoundException()
        metadata = self.db[key].copy()

        item_path = metadata["path"]
        item = Item(id=metadata["path"].split("/")[-1], attributes=metadata)

        item.readable = True
        self._trigger_event("file_route_needed", item=item, path=item_path)
        self._trigger_event("on_item", item=item, path=item_path)

        return item
