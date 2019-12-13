from ..shelve.tests import ShelfDatabaseTest
from .handler import LMDBDatabasePlugin


class LMDBDatabaseTest(ShelfDatabaseTest):
    def open_database(self):
        return LMDBDatabasePlugin({"path": self.db_path})
