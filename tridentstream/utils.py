import hashlib
from urllib.parse import urljoin as _urljoin


def urljoin(*args):
    args = list(args)
    url = args.pop(0)
    for arg in args:
        url = _urljoin(url.rstrip("/") + "/", arg.lstrip("/"))

    return url


def hash_string(s):
    try:
        return hashlib.sha1(s).hexdigest()
    except (UnicodeEncodeError, TypeError):
        return hashlib.sha1(s.encode("utf-8")).hexdigest()
