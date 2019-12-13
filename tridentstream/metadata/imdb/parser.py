import re

from unplugged import Schema

from ...plugins import MetadataParserPlugin


class IMDBMetadataParserPlugin(MetadataParserPlugin):
    plugin_name = "imdb"
    pattern = re.compile(r"(?i).+\.nfo$")
    config_schema = Schema

    def handle(self, vfs, virtual_path, actual_path):
        with open(actual_path, "rb") as fn:
            d = fn.read().decode("utf-8", "ignore")

        ids = re.findall(
            r"(?:(?:imdb\.com[^ ]+?(?:tt|\?|))|(?:IMDB ID: ))([0-9]{7})",
            d,
            re.IGNORECASE,
        )
        if ids:
            self.set_metadata_parent_path(vfs, virtual_path, "id", ids[0])

    def unload(self):
        pass
