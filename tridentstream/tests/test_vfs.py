import time
import unittest

from freezegun import freeze_time

from ..testutils import debugdict
from ..vfs import GC_DELETED_FILES, DatabaseType, FileSystem


class VirtualFileSystemTestCase(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.fs = FileSystem(debugdict())

        self.events_called = {"new": [], "deleted": [], "db_closed": []}

        def new_file(key, db_type, metadata):
            self.events_called["new"].append((key, db_type, metadata))

        def delete_file(key, db_type, metadata):
            self.events_called["deleted"].append((key, db_type, metadata))

        def db_closed():
            self.events_called["db_closed"].append(None)

        self.fs.add_event("new", new_file)
        self.fs.add_event("deleted", delete_file)
        self.fs.add_event("db_closed", db_closed)

    def test_add_files(self):
        with self.fs.session(current_time=500):
            self.fs.add_file(
                "important.txt", 20, 10, metadata={"metadata:some": "useful"}
            )
            self.fs.add_dir("important stuff", 20)
            self.fs.add_file("important stuff/somefile1.txt", 20, 30)

        listing = self.fs.list_dir("", depth=1).serialize()
        expected_listing = {
            "id": "",
            "attributes": {"date": 0, "path": "", "modified": 30},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "important stuff",
                    "attributes": {
                        "modified": 30,
                        "date": 20,
                        "path": "important stuff",
                    },
                    "readable": False,
                    "streamable": False,
                    "expandable": False,
                    "nested_items": [
                        {
                            "id": "somefile1.txt",
                            "attributes": {
                                "modified": 30,
                                "date": 30,
                                "size": 20,
                                "path": "important stuff/somefile1.txt",
                            },
                            "readable": True,
                            "streamable": False,
                            "expandable": False,
                            "nested_items": None,
                        }
                    ],
                },
                {
                    "id": "important.txt",
                    "attributes": {
                        "modified": 10,
                        "date": 10,
                        "size": 20,
                        "path": "important.txt",
                        "metadata:some": "useful",
                    },
                    "readable": True,
                    "expandable": False,
                    "streamable": False,
                    "nested_items": None,
                },
            ],
        }
        self.assertEqual(listing, expected_listing)

        with self.fs.session(True, current_time=500):
            self.fs.add_dir("important snuff", 20)
            self.fs.add_dir("important stuff", 20)

        listing = self.fs.list_dir("", depth=1).serialize()
        expected_listing = {
            "id": "",
            "attributes": {"date": 0, "path": "", "modified": 500},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "important snuff",
                    "attributes": {
                        "modified": 20,
                        "date": 20,
                        "path": "important snuff",
                    },
                    "readable": False,
                    "expandable": False,
                    "streamable": False,
                    "nested_items": [],
                },
                {
                    "id": "important stuff",
                    "attributes": {
                        "modified": 500,
                        "date": 20,
                        "path": "important stuff",
                    },
                    "readable": False,
                    "expandable": False,
                    "streamable": False,
                    "nested_items": [],
                },
            ],
        }
        self.assertEqual(listing, expected_listing)

    def test_nested_modified(self):
        with self.fs:
            self.fs.add_dir("important stuff", 10)
            self.fs.add_file("important stuff/somefile1.txt", 20, 20)
            self.fs.add_dir("important stuff/more stuff", 30)

        listing = self.fs.list_dir("", depth=0).serialize()
        expected_listing = {
            "id": "",
            "attributes": {"date": 0, "path": "", "modified": 30},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "important stuff",
                    "attributes": {
                        "modified": 30,
                        "date": 10,
                        "path": "important stuff",
                    },
                    "readable": False,
                    "streamable": False,
                    "expandable": True,
                    "nested_items": None,
                }
            ],
        }
        self.assertEqual(listing, expected_listing)

        with self.fs:
            self.fs.add_dir("important stuff/more stuff/even mores tuff", 40)

        listing = self.fs.list_dir("", depth=0).serialize()
        expected_listing = {
            "id": "",
            "attributes": {"date": 0, "path": "", "modified": 40},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "important stuff",
                    "attributes": {
                        "modified": 40,
                        "date": 10,
                        "path": "important stuff",
                    },
                    "readable": False,
                    "streamable": False,
                    "expandable": True,
                    "nested_items": None,
                }
            ],
        }
        self.assertEqual(listing, expected_listing)

        with self.fs:
            self.fs.add_file(
                "important stuff/more stuff/even mores tuff/somefile1.txt", 20, 50
            )

        listing = self.fs.list_dir("", depth=0).serialize()
        expected_listing = {
            "id": "",
            "attributes": {"date": 0, "path": "", "modified": 50},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "important stuff",
                    "attributes": {
                        "modified": 50,
                        "date": 10,
                        "path": "important stuff",
                    },
                    "readable": False,
                    "streamable": False,
                    "expandable": True,
                    "nested_items": None,
                }
            ],
        }
        self.assertEqual(listing, expected_listing)
        self.assertEqual(
            self.fs.last_modified(
                "important stuff/more stuff/even mores tuff/somefile1.txt"
            ),
            50,
        )
        self.assertEqual(
            self.fs.last_modified("important stuff/more stuff/even mores tuff"), 50
        )
        self.assertEqual(self.fs.last_modified("important stuff/more stuff"), 50)
        self.assertEqual(self.fs.last_modified("important stuff"), 50)
        self.assertEqual(self.fs.last_modified(""), 50)

        with self.fs:
            self.fs.add_file(
                "important stuff/more stuff/even mores tuff/somefile1.txt",
                20,
                60,
                {"a": "b"},
            )

        listing = self.fs.list_dir("", depth=0).serialize()
        expected_listing = {
            "id": "",
            "attributes": {"date": 0, "path": "", "modified": 60},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "important stuff",
                    "attributes": {
                        "modified": 60,
                        "date": 10,
                        "path": "important stuff",
                    },
                    "readable": False,
                    "streamable": False,
                    "expandable": True,
                    "nested_items": None,
                }
            ],
        }
        self.assertEqual(listing, expected_listing)
        self.assertEqual(
            self.fs.last_modified(
                "important stuff/more stuff/even mores tuff/somefile1.txt"
            ),
            60,
        )
        self.assertEqual(
            self.fs.last_modified("important stuff/more stuff/even mores tuff"), 60
        )
        self.assertEqual(self.fs.last_modified("important stuff/more stuff"), 60)
        self.assertEqual(self.fs.last_modified("important stuff"), 60)
        self.assertEqual(self.fs.last_modified(""), 60)

    def test_update_metadata(self):
        with self.fs:
            self.fs.add_dir(
                "metadata folder", 10, {"test": "metadata", "1": 2, "list": [1, 2, 3]}
            )
            self.fs.add_file(
                "metadata folder/metadata file.txt",
                20,
                20,
                {"test2": "metadata2", "3": 4, "list2": [3, 2, 1]},
            )

        listing = self.fs.list_dir("metadata folder", depth=0).serialize()
        expected_listing = {
            "id": "metadata folder",
            "attributes": {
                "date": 10,
                "path": "metadata folder",
                "1": 2,
                "list": [1, 2, 3],
                "modified": 20,
                "test": "metadata",
            },
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "metadata file.txt",
                    "attributes": {
                        "3": 4,
                        "date": 20,
                        "path": "metadata folder/metadata file.txt",
                        "list2": [3, 2, 1],
                        "modified": 20,
                        "size": 20,
                        "test2": "metadata2",
                    },
                    "readable": True,
                    "streamable": False,
                    "expandable": False,
                    "nested_items": None,
                }
            ],
        }
        self.assertEqual(listing, expected_listing)

        with self.fs:
            self.fs.add_dir(
                "metadata folder",
                10,
                {"test": "metadata2", "1": 3, "list": [1, 2, 4], "new": "value"},
            )
            self.fs.add_file(
                "metadata folder/metadata file.txt",
                20,
                20,
                {"test2": "metadata3", "3": 5, "list2": [3, 2, 3], "new": "value"},
            )

        listing = self.fs.list_dir("metadata folder", depth=0).serialize()
        expected_listing = [
            {
                "1": 3,
                "date": 10,
                "id": "metadata folder",
                "list": [1, 2, 4],
                "modified": 20,
                "name": "metadata folder",
                "test": "metadata2",
                "type": "folder",
                "new": "value",
            },
            {
                "3": 5,
                "date": 20,
                "id": "metadata folder/metadata file.txt",
                "list2": [3, 2, 3],
                "modified": 20,
                "name": "metadata file.txt",
                "size": 20,
                "test2": "metadata3",
                "type": "file",
                "new": "value",
            },
        ]
        expected_listing = {
            "id": "metadata folder",
            "attributes": {
                "1": 3,
                "date": 10,
                "list": [1, 2, 4],
                "modified": 20,
                "path": "metadata folder",
                "test": "metadata2",
                "new": "value",
            },
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "metadata file.txt",
                    "attributes": {
                        "3": 5,
                        "date": 20,
                        "list2": [3, 2, 3],
                        "modified": 20,
                        "size": 20,
                        "test2": "metadata3",
                        "new": "value",
                        "path": "metadata folder/metadata file.txt",
                    },
                    "readable": True,
                    "expandable": False,
                    "streamable": False,
                    "nested_items": None,
                }
            ],
        }
        self.assertEqual(listing, expected_listing)

        with self.fs:
            self.fs.update_metadata(
                DatabaseType.DIRECTORY,
                "metadata folder",
                {"new": "value2", "horse": "ride"},
            )

        metadata = self.fs.get_metadata(DatabaseType.DIRECTORY, "metadata folder")
        expected_metadata = {
            "1": 3,
            "date": 10,
            "horse": "ride",
            "list": [1, 2, 4],
            "modified": 20,
            "new": "value2",
            "path": "metadata folder",
            "test": "metadata2",
        }
        self.assertEqual(metadata, expected_metadata)

    def test_delete_resurrect_removed(self):
        with self.fs.session(current_time=500):
            self.fs.add_dir("folder", 10)
            self.fs.add_file("folder/file", 20, 20)

        listing = self.fs.list_dir("folder", depth=0).serialize()
        expected_listing = {
            "id": "folder",
            "attributes": {"modified": 20, "date": 10, "path": "folder"},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "file",
                    "attributes": {
                        "modified": 20,
                        "date": 20,
                        "size": 20,
                        "path": "folder/file",
                    },
                    "readable": True,
                    "streamable": False,
                    "expandable": False,
                    "nested_items": None,
                }
            ],
        }
        self.assertEqual(listing, expected_listing)

        with self.fs.session(True, current_time=500):
            self.fs.add_dir("folder", 10)
            self.fs.add_file("folder/file", 20, 20)

        listing = self.fs.list_dir("folder", depth=0).serialize()
        self.assertEqual(listing, expected_listing)

        with self.fs.session(True, current_time=500):
            self.fs.add_dir("folder", 10)

        listing = self.fs.list_dir("folder", depth=0).serialize()
        expected_listing = {
            "id": "folder",
            "attributes": {"modified": 500, "date": 10, "path": "folder"},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [],
        }
        self.assertEqual(listing, expected_listing)

        listing = self.fs.list_dir("folder", depth=0, show_deleted=True).serialize()
        expected_listing = {
            "id": "folder",
            "attributes": {"modified": 500, "date": 10, "path": "folder"},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "file",
                    "attributes": {
                        "modified": 20,
                        "date": 20,
                        "size": 20,
                        "path": "folder/file",
                        "deleted": 500,
                    },
                    "readable": True,
                    "streamable": False,
                    "expandable": False,
                    "nested_items": None,
                }
            ],
        }
        self.assertEqual(listing, expected_listing)

        with self.fs.session(True, current_time=600):
            self.fs.add_dir("folder", 600)
            self.fs.add_file("folder/file", 20, 600)

        listing = self.fs.list_dir("folder", depth=0).serialize()
        expected_listing = {
            "id": "folder",
            "attributes": {"modified": 600, "date": 10, "path": "folder"},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "file",
                    "attributes": {
                        "modified": 600,
                        "date": 20,
                        "size": 20,
                        "path": "folder/file",
                    },
                    "readable": True,
                    "expandable": False,
                    "streamable": False,
                    "nested_items": None,
                }
            ],
        }
        self.assertEqual(listing, expected_listing)

        with self.fs.session(True, current_time=500):
            self.fs.add_dir("folder", 10)

        with self.fs.session(True, current_time=500 + GC_DELETED_FILES - 100):
            self.fs.add_dir("folder", 10)

        listing = self.fs.list_dir("folder", depth=0, show_deleted=True).serialize()
        expected_listing = {
            "id": "folder",
            "attributes": {"modified": 600, "date": 10, "path": "folder"},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "file",
                    "attributes": {
                        "modified": 600,
                        "date": 20,
                        "size": 20,
                        "path": "folder/file",
                        "deleted": 500,
                    },
                    "readable": True,
                    "expandable": False,
                    "streamable": False,
                    "nested_items": None,
                }
            ],
        }
        self.assertEqual(listing, expected_listing)

        with self.fs.session(True, current_time=500 + GC_DELETED_FILES + 100):
            self.fs.add_dir("folder", 10)

        listing = self.fs.list_dir("folder", depth=0, show_deleted=True).serialize()
        expected_listing = {
            "id": "folder",
            "attributes": {"modified": 600, "date": 10, "path": "folder"},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [],
        }
        self.assertEqual(listing, expected_listing)

    def test_last_modified(self):
        with self.fs.session(True, current_time=500):
            self.fs.add_dir("folder", 10)
            self.fs.add_file("folder/file", 20, 20)

        assert self.fs.last_modified("folder") == 20
        assert self.fs.last_modified("folder/file") == 20

        with self.fs.session(current_time=500):
            self.fs.add_file("folder/file", 30, 30)

        assert self.fs.last_modified("folder") == 30
        assert self.fs.last_modified("folder/file") == 30

        with self.fs.session(True, current_time=500):
            self.fs.add_dir("folder", 30)

        assert self.fs.last_modified("folder") == 500

    def test_events(self):
        with self.fs.session(True, current_time=500):
            self.fs.add_dir("folder", 10)
            self.fs.add_file("folder/file", 20, 20)

        events = sorted(
            [m for (_, _, m) in self.events_called["new"]], key=lambda x: x["path"]
        )
        expected_events = [
            {"date": 10, "modified": 20, "path": "folder"},
            {"date": 20, "modified": 20, "path": "folder/file", "size": 20},
        ]
        self.assertEqual(events, expected_events)
        self.assertEqual(len(self.events_called["deleted"]), 0)
        self.events_called["new"] = []

        with self.fs.session(True, current_time=500):
            self.fs.add_dir("folder", 10)
            self.fs.add_file("folder/file", 20, 20)

        self.assertEqual(len(self.events_called["new"]), 0)
        self.assertEqual(len(self.events_called["deleted"]), 0)

        with self.fs.session(True, current_time=500):
            self.fs.add_dir("folder", 10)

        events = sorted(
            [m for (_, _, m) in self.events_called["deleted"]], key=lambda x: x["path"]
        )
        expected_events = [
            {
                "date": 20,
                "modified": 20,
                "path": "folder/file",
                "size": 20,
                "deleted": 500,
            }
        ]
        self.assertEqual(events, expected_events)
        self.assertEqual(len(self.events_called["new"]), 0)
        self.events_called["deleted"] = []

        with self.fs.session(True, current_time=500):
            self.fs.add_dir("folder", 10)
            self.fs.add_file("folder/file", 20, 20)

        events = sorted(
            [m for (_, _, m) in self.events_called["new"]], key=lambda x: x["path"]
        )
        expected_events = [
            {"date": 20, "modified": 20, "path": "folder/file", "size": 20}
        ]
        self.assertEqual(events, expected_events)
        self.assertEqual(len(self.events_called["deleted"]), 0)
        self.events_called["new"] = []

        with self.fs.session(True, current_time=500):
            self.fs.add_dir("folder", 10)
        self.events_called["deleted"] = []

        with self.fs.session(True, current_time=500 + GC_DELETED_FILES + 100):
            self.fs.add_dir("folder", 10)

        self.assertEqual(len(self.events_called["new"]), 0)
        self.assertEqual(len(self.events_called["deleted"]), 0)

    def test_add_routes(self):
        def add_file_route(item, path):
            item.add_route("file", True, False, False, kwargs={"item_id": item.id})

        def add_list_route(item, path):
            item.add_route("list", False, True, False, kwargs={"item_id": item.id})

        self.fs.add_event("file_route_needed", add_file_route)
        self.fs.add_event("list_route_needed", add_list_route)

        with self.fs.session(current_time=500):
            self.fs.add_file("a_file", 0, 0)
            self.fs.add_dir("a_folder", 0)

        listing = self.fs.list_dir("", depth=0).serialize(include_routes=True)
        expected_listing = {
            "id": "",
            "attributes": {"date": 0, "path": ""},
            "readable": False,
            "streamable": False,
            "expandable": False,
            "nested_items": [
                {
                    "id": "a_file",
                    "attributes": {
                        "modified": 0,
                        "date": 0,
                        "path": "a_file",
                        "size": 0,
                    },
                    "readable": True,
                    "expandable": False,
                    "streamable": False,
                    "nested_items": None,
                    "routes": [
                        {
                            "handler": "file",
                            "can_open": True,
                            "can_stream": False,
                            "can_list": False,
                            "priority": 0,
                            "kwargs": {"item_id": "a_file"},
                        }
                    ],
                },
                {
                    "id": "a_folder",
                    "attributes": {"modified": 0, "date": 0, "path": "a_folder"},
                    "readable": False,
                    "streamable": False,
                    "expandable": True,
                    "nested_items": None,
                    "routes": [
                        {
                            "handler": "list",
                            "can_open": False,
                            "can_stream": False,
                            "can_list": True,
                            "priority": 0,
                            "kwargs": {"item_id": "a_folder"},
                        }
                    ],
                },
            ],
            "routes": [],
        }

        self.assertEqual(listing, expected_listing)

    def test_no_depth_list_on_item(self):
        def add_list_route(item, path):
            item.expandable = True
            item.add_route("list", False, True, False, kwargs={"item_id": item.id})

        self.fs.add_event("on_item", add_list_route)

        with self.fs.session(current_time=500):
            self.fs.add_file("a_file", 0, 0)
            self.fs.add_dir("a_folder", 0)

        listing = self.fs.list_dir("a_folder", depth=-1).serialize(include_routes=True)

        expected_listing = {
            "id": "a_folder",
            "attributes": {"modified": 0, "date": 0, "path": "a_folder"},
            "readable": False,
            "streamable": False,
            "expandable": True,
            "nested_items": None,
            "routes": [
                {
                    "handler": "list",
                    "can_open": False,
                    "can_stream": False,
                    "can_list": True,
                    "priority": 0,
                    "kwargs": {"item_id": "a_folder"},
                }
            ],
        }

        self.assertEqual(listing, expected_listing)

    def test_event_update_metadata(self):
        def new_file(key, db_type, metadata):
            parent_path = "/".join(metadata["path"].split("/")[:-1])
            self.fs.update_metadata(
                DatabaseType.DIRECTORY, parent_path, {"this": "works"}
            )

        self.fs.add_event("new", new_file)

        with self.fs.session(True, current_time=500):
            self.fs.add_dir("folder", 10)
            self.fs.add_file("folder/file", 20, 20)

        metadata = self.fs.get_metadata(DatabaseType.DIRECTORY, "folder")
        self.assertEqual(metadata.get("this"), "works")
