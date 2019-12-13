from ..shelve.tests import ShelfDatabaseTest
from .handler import LevelDBDatabasePlugin


class LevelDBDatabaseTest(ShelfDatabaseTest):
    def open_database(self):
        return LevelDBDatabasePlugin({"path": self.db_path})
