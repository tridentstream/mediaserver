import logging

from unplugged import Schema, fields
from whoosh import analysis, index
from whoosh.fields import ID, TEXT, SchemaClass
from whoosh.qparser import QueryParser
from whoosh.query import Term
from whoosh.writing import AsyncWriter

from ...plugins import IndexerPlugin, PathIndexer

logger = logging.getLogger(__name__)


class WhooshSchema(SchemaClass):
    parent_path = ID()
    path = ID(stored=True)
    title = TEXT(
        spelling=False, analyzer=analysis.StandardAnalyzer(minsize=1, stoplist=[])
    )


class WhooshIndexerSchema(Schema):
    path = fields.String()


class WhooshPathIndexer(PathIndexer):
    def __init__(self, writer, parent_path):
        self.writer = writer
        self.parent_path = parent_path

    def index(self, path, title):
        logger.trace(
            f"Indexing parent_path:{self.parent_path}, path:{path}, title:{title}"
        )

        self.writer.add_document(parent_path=self.parent_path, path=path, title=title)

    def delete(self, path):
        logger.trace(f"Deleting all indexes for path {path}")
        self.writer.delete_by_query(Term("path", path))

    def commit(self):
        logger.debug(f"Committing {self.parent_path}")
        self.writer.commit()


class WhooshIndexerPlugin(IndexerPlugin):
    plugin_name = "whoosh"
    config_schema = WhooshIndexerSchema

    def __init__(self, config):
        path = self.get_database_path(config.get("path"))

        try:
            self.ix = index.open_dir(path)
        except index.EmptyIndexError:
            self.ix = index.create_in(path, WhooshSchema())

    def clear(self, parent_path):
        logger.debug(f"Clearing index for {self.name}")
        self.ix.delete_by_query(Term("parent_path", parent_path))

    def get_writer(self, parent_path):
        logger.debug(f"Getting index writer for path:{parent_path}")
        return WhooshPathIndexer(AsyncWriter(self.ix), parent_path)

    def search(self, parent_path, query):
        qp = QueryParser("title", schema=self.ix.schema)
        q = qp.parse(query) & Term("parent_path", parent_path)

        with self.ix.searcher() as s:
            results, seen = [], set()
            for path in [x["path"] for x in s.search(q, limit=120)]:
                if path in seen:
                    continue

                seen.add(path)
                results.append(path)

        logger.debug(f"Searched for {query!r} found {len(results)} results")
        return results

    def unload(self):
        logger.debug(f"Unloading index {self.name}")
        self.ix.close()
