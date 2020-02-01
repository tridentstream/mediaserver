import glob
import logging
import os
import time
from datetime import datetime
from queue import Queue
from urllib.parse import urljoin

import pytz
from django.conf import settings
from thomas import router
from unplugged import RelatedPluginField, Schema, command, fields, threadify
from unplugged.models import Log

from twisted.internet import defer, reactor

from ...exceptions import NotModifiedException, PathNotFoundException
from ...plugins import (
    DatabasePlugin,
    InputPlugin,
    MetadataParserPlugin,
    Notification,
    NotifierPlugin,
)
from ...vfs import FileSystem

COMMIT_COUNTER = 10000

logger = logging.getLogger(__name__)


class PathSchema(Schema):
    path = fields.String(required=True)
    virtual_root = fields.String(default="")


class FilesystemInputSchema(Schema):
    priority = fields.Integer(default=10)
    db = RelatedPluginField(plugin_type=DatabasePlugin, required=True)
    metadata_parsers = fields.List(
        RelatedPluginField(plugin_type=MetadataParserPlugin), many=True, default=list
    )
    paths = fields.Nested(PathSchema, many=True, default=list)
    notifier = RelatedPluginField(plugin_type=NotifierPlugin)


class FilesystemInputPlugin(InputPlugin):
    plugin_name = "filesystem"

    config_schema = FilesystemInputSchema

    is_rescanning = False
    rescan_done = None
    should_die = False

    vfs = None
    route_input_fs_list = None

    simpleadmin_templates = [
        {
            "template": {
                "paths": {"simpleAdminMethod": "userInput"},
                "metadata_parsers": [
                    {
                        "simpleAdminMethod": "lookupPlugin",
                        "plugin_type": "metadataparser",
                        "name": "imdb",
                    },
                    {
                        "simpleAdminMethod": "lookupPlugin",
                        "plugin_type": "metadataparser",
                        "name": "mal",
                    },
                ],
                "db": {
                    "simpleAdminMethod": "createPluginPriority",
                    "pluginPriorities": [
                        {
                            "plugin_type": "database",
                            "plugin_name": "leveldb",
                            "name": "db_automanaged_%(name)s",
                            "config": {"path": "db_automanaged_%(name)s"},
                        },
                        {
                            "plugin_type": "database",
                            "plugin_name": "shelf",
                            "name": "db_automanaged_%(name)s",
                            "config": {"path": "db_automanaged_%(name)s"},
                        },
                    ],
                },
                "notifier": {
                    "simpleAdminMethod": "lookupPlugin",
                    "plugin_type": "notifier",
                    "name": "multinotifier",
                },
            },
            "description": "Get data from local filesystem",
            "id": "default",
            "update_method": "full",
        }
    ]

    def __init__(self, config):
        self.db = config["db"]
        self.priority = config.get("priority", 10)
        self.vfs = FileSystem(self.db)
        self.last_update = datetime.now()
        self.vfs.add_event("new", self._new_item)
        self.vfs.add_event("file_route_needed", self._file_route_needed)
        self.vfs.add_event("list_route_needed", self._list_route_needed)
        self.vfs.add_event("on_item", self._on_item)
        self.metadata_parsers = config.get("metadata_parsers", [])
        self.notifier = config.get("notifier")

        self.paths = []
        for path_template in config.get("paths", []):
            for path in glob.glob(path_template["path"]):
                self.paths.append((path_template.get("virtual_root", ""), path))
                logger.info(
                    f"Added path {path!r} to virtual path {path_template.get('virtual_root', '')!r}"
                )

        self.route_input_fs_list = f"input_fs_list_{self.name}"

        router.register_handler(
            self.route_input_fs_list, self.thomas_list, False, True, False
        )

    @command(
        name="clear_and_rescan",
        display_name="Clear and Rescan",
        description="Clear all the stored metadata and add it anew",
    )
    def command_clear_and_rescan(self):
        logger.info("Clearing database")
        self.rescan(True)

    @command(
        name="rescan",
        display_name="Rescan",
        description="Scan for new data on the disks",
    )
    def command_rescan(self):
        logger.info("External call for rescan")
        self.rescan()

    def unload(self):
        logger.info("Asked to unload FS input handler")
        self.should_die = True
        if self.is_rescanning:
            logger.info("Unloading after rescan is done")
            self.rescan_done.addCallback(lambda x: self.close())
        else:
            logger.info("Unloading now")
            self.close()

        if self.route_input_fs_list:
            router.unregister_handler(self.route_input_fs_list)

    def _file_route_needed(self, item, path):
        item.add_route(
            "file",
            True,
            False,
            False,
            kwargs={"path": item["_actual_path"]},
            priority=self.priority,
        )

    def _list_route_needed(self, item, path):
        item.add_route(
            self.route_input_fs_list,
            False,
            True,
            False,
            kwargs={"path": path},
            priority=self.priority,
        )

    def _on_item(self, item, path):
        if (
            not item.is_listable
            and os.path.splitext(item.id)[1].lstrip(".").lower()
            not in settings.STREAMABLE_EXTENSIONS
        ):
            return

        item.streamable = True
        for streamer_plugin in settings.THOMAS_STREAMER_PLUGINS:
            item.add_route(streamer_plugin, False, False, True, priority=self.priority)

    def _new_item(self, key, db_type, metadata):
        filename = metadata["path"].split("/")[-1]
        # logger.debug('New item %s, trying to match with metadata' % (metadata['path'], ))
        for plugin in self.metadata_parsers:
            if plugin.pattern.match(filename):
                # logger.debug('Sending %s to metadataparser %s' % (metadata['path'], plugin.name))
                try:
                    plugin.handle(self.vfs, metadata["path"], metadata["_actual_path"])
                except:
                    logger.exception(
                        f"Failed to handle {metadata['_actual_path']} with plugin {plugin!r}"
                    )

    def close(self):
        if self.vfs:
            self.vfs.close()

    def list(self, path, depth, modified_since=None):
        last_modified = datetime.fromtimestamp(self.vfs.last_modified(path), pytz.UTC)

        if modified_since and last_modified <= modified_since:
            raise NotModifiedException()

        logger.info(f"Listing path {path!r} with depth {depth}")
        listing = self.vfs.list_dir(path, depth)
        return listing

    def stream(self, path):
        logger.info(f"Trying to stream {path!r}")

        item = self.list(path, -1)
        return item.stream()

    def get_item(self, path):
        try:
            return self.list(path, -1)
        except PathNotFoundException:
            logger.info(f"Getting file at path {path!r}")
            return self.vfs.list_file(path)

    def rescan(self, update_all_metadata=False):
        threadify(self._rescan)(update_all_metadata)
        return "Rescanning"

    def _rescan(self, update_all_metadata=False):
        """
        Rescans filesystem for files
        """
        if self.is_rescanning:
            logger.warning("Already rescanning")
            return None

        notification = Notification(
            f"admin.{self.plugin_name}.{self.name}.rescan",
            "info",
            f"Filesystem {self.name}",
            "Started to rescan",
            permission_type="is_admin",
        )
        notification_start_dt = datetime.now()
        if self.notifier:
            self.notifier.notify(notification)

        with Log.objects.start_chain(self, "INPUT.RESCAN") as log:
            log.log(
                0, f"A rescan is started and update_all_metadata {update_all_metadata}"
            )

            self.is_rescanning = True
            self.rescan_done = defer.Deferred()

            logger.info("Rescanning")
            queue = Queue(20)

            class QueueCommand:
                INSERT = 0
                ENSURE_PREFIXES = 1
                DONE = 2

            def walk_path(queue, prefix, path):
                logger.info(f"Starting to scan {path!r} with prefix {prefix!r}")
                list_queue = []
                queue_size = 0

                for r, dirs, files in os.walk(path, followlinks=True):
                    useful_files = []
                    for f in files:
                        full_path = os.path.join(r, f)
                        if not os.path.exists(full_path):
                            logger.debug(f"We found broken link: {full_path}")
                            continue

                        useful_files.append((f, os.path.getsize(full_path)))

                    list_queue.append((r[len(path) :].strip("/"), dirs, useful_files))
                    queue_size += len(dirs) + len(files)

                    if queue_size >= COMMIT_COUNTER:
                        queue.put((QueueCommand.INSERT, path, prefix, list_queue))
                        list_queue = []
                        queue_size = 0

                    if self.should_die:
                        logger.info(f"Got the death in walker for {path}")
                        return

                if list_queue:
                    queue.put((QueueCommand.INSERT, path, prefix, list_queue))

                queue.put((QueueCommand.DONE, path))

                logger.info(f"Done scanning {path!r}")

            def insert_into_vfs(vfs, queue, path_count):
                with vfs.session(True, always_trigger_new=update_all_metadata):
                    while path_count:
                        job = queue.get(True)
                        cmd = job[0]

                        if cmd == QueueCommand.INSERT:
                            logger.debug("Got insertion job")
                            _, path, prefix, items = job

                            for root, folders, files in items:
                                virtual_path = [prefix] + root.split(os.sep)

                                for item in folders:
                                    vp = "/".join(
                                        [x for x in virtual_path + [item] if x]
                                    )
                                    vfs.add_dir(vp, int(time.time()))

                                for item, size in files:
                                    vp = "/".join(
                                        [x for x in virtual_path + [item] if x]
                                    )
                                    actual_path = os.path.join(path, root, item)

                                    vfs.add_file(
                                        vp,
                                        size,
                                        int(time.time()),
                                        {"_actual_path": actual_path},
                                    )

                        elif cmd == QueueCommand.ENSURE_PREFIXES:
                            _, prefixes = job

                            for prefix in prefixes:
                                path = []
                                for p in prefix.strip("/").split("/"):
                                    path.append(p)
                                    vfs.add_dir("/".join(path), int(time.time()))
                        elif cmd == QueueCommand.DONE:
                            _, path = job
                            logger.info(f"Done inserting {path!r}")
                            path_count -= 1
                        else:
                            logger.error(f"Unknown command {job!r}")

                        if self.should_die:
                            logger.info(f"Got the death in inserter for {path}")
                            break

                self.last_update = datetime.now()
                self.is_rescanning = False
                reactor.callFromThread(self.rescan_done.callback, None)
                self.rescan_done.callback = None

                logger.info("Done scanning all paths.")

            t = threadify(insert_into_vfs, cache_result=True)(
                self.vfs, queue, len(self.paths)
            )

            prefixes = set(p[0] for p in self.paths if p[0])
            if prefixes:
                queue.put((QueueCommand.ENSURE_PREFIXES, prefixes))

            for virtual_path, path in self.paths:
                threadify(walk_path)(queue, virtual_path, path)

            t()

            delta = datetime.now() - notification_start_dt
            if self.notifier:
                notification = notification.copy(
                    body=f"Finished rescanning, it took {delta}"
                )
                self.notifier.notify(notification)

            log.log(100, f"A rescan finished after {delta}")

    def thomas_list(self, item, path, depth=0, modified_since=None):
        return self.list(path, depth, modified_since)
