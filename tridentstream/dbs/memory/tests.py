from ..shelve.tests import ShelfDatabaseTest
from .handler import MemoryDatabasePlugin


class MemoryDatabaseTest(ShelfDatabaseTest):
    def open_database(self):
        return MemoryDatabasePlugin({})

    def test_reopen_database(self):
        pass
