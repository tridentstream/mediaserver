import os
import shutil
import tempfile
import unittest

from django.test import TestCase

from ...plugins import DatabaseCacheLayer
from .handler import ShelfDatabasePlugin


class ShelfDatabaseTest(TestCase):
    def setUp(self):
        self.temp_path = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_path, "db")
        try:
            self.db = self.open_database()
        except ImportError:
            raise unittest.SkipTest("Database not installed")

    def tearDown(self):
        shutil.rmtree(self.temp_path)

    def open_database(self):
        return ShelfDatabasePlugin({"path": self.db_path})

    def reOpen(self):
        self.db.sync()
        self.db.close()
        self.db = self.open_database()

    def test_set_get_keys(self):
        self.db["\x01\x03"] = "\x01\x03"
        self.db["test"] = "test"

        self.db.sync()

        self.assertEqual(self.db["\x01\x03"], "\x01\x03")
        self.assertEqual(self.db["test"], "test")
        self.assertEqual(len(self.db), 2)

    def test_delete_keys(self):
        self.test_set_get_keys()

        del self.db["test"]
        self.db.sync()

        self.assertEqual(len(self.db), 1)
        self.assertNotIn("test", self.db)
        self.assertIn("\x01\x03", self.db)

    def test_reopen_database(self):
        self.db["\x01\x03"] = "\x01\x03"
        self.db["test"] = "test"

        self.reOpen()

        self.assertEqual(self.db["test"], "test")
        self.assertEqual(len(self.db), 2)
        self.assertEqual(self.db["\x01\x03"], "\x01\x03")
        self.db["test2"] = "abc"

        del self.db["test"]

        self.reOpen()

        self.assertEqual(len(self.db), 2)
        self.assertNotIn("test", self.db)
        self.assertIn("\x01\x03", self.db)
        self.assertIn("test2", self.db)

    def test_complex_types(self):
        self.db["set"] = set([1, 2, 3])
        self.assertEqual(self.db["set"], set([1, 2, 3]))

        self.db["dict"] = dict(a=1, b=2)
        self.assertEqual(self.db["dict"], dict(a=1, b=2))


class ShelfDatabaseCacheTest(ShelfDatabaseTest):
    def open_database(self):
        return DatabaseCacheLayer(super(ShelfDatabaseCacheTest, self).open_database())
