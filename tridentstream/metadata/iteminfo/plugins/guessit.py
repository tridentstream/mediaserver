import logging

from guessit import guessit
from unplugged import Schema

from .plugin import ItemInfoPlugin

logging.getLogger("rebulk.rebulk").setLevel(logging.WARNING)


class GuessItItemInfoPlugin(ItemInfoPlugin):
    plugin_name = "guessit"
    config_schema = Schema

    def get_info(self, name):
        info = dict(guessit(name))

        retval = {}
        for k, v in info.items():
            if k in ["season", "episode"]:
                if isinstance(v, list):
                    v = v[-1]
                retval[k] = v
            elif k == "episode_details":
                retval["episode_type"] = v
            elif k == "format":
                retval["source"] = v
            elif k == "part":
                if isinstance(v, list):
                    v = v[-1]
                retval["episode"] = v
            elif k in ["title", "year"]:
                retval[k] = v

        lower_name = name.lower()
        types = {
            "nfofix": ["nfofix", "nfo.fix", "nfo_fix"],
            "dirfix": ["dirfix", "dir.fix", "dir_fix"],
            "subfix": ["subfix", "sub.fix", "sub_fix"],
            "subpack": ["subpack", "sub.pack", "sub_pack"],
        }
        for k, vs in types.items():
            for v in vs:
                if v in lower_name:
                    retval["fix_type"] = k

        return retval

    def unload(self):
        pass
