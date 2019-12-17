import os

from django.conf import settings
from unplugged import JSONAPIObject


class Stream:
    def __init__(self, url, playhandler, name=None):
        self.url = url
        self.playhandler = playhandler
        self.name = name

    def to_jsonapi(self, request):
        obj = JSONAPIObject(
            f"stream_{self.playhandler}",
            self.name,
            links={"stream": request.build_absolute_uri(self.url)},
        )
        return obj

    def serialize(self, request):
        retval = {
            "url": request.build_absolute_uri(self.url),
            "playhandler": self.playhandler,
        }
        if self.name:
            retval["name"] = self.name

        return retval

    @classmethod
    def unserialize(cls, data):
        return cls(data["url"], data["playhandler"], data.get("name"))


def create_stream(item, request):
    stream_or_item = item.stream()
    if isinstance(stream_or_item, Stream):
        return stream_or_item
    else:
        url = request.build_absolute_uri(
            settings.THOMAS_HTTP_OUTPUT.serve_item(stream_or_item)
        )
        return Stream(url, "http", stream_or_item.id)
