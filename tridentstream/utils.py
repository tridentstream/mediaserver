import hashlib
import os
import posixpath
import time
from urllib.parse import urljoin as _urljoin

from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.utils._os import safe_join
from django.utils.six.moves.urllib.parse import unquote
from django.views.static import directory_index, was_modified_since


def urljoin(*args):
    args = list(args)
    url = args.pop(0)
    for arg in args:
        url = _urljoin(url.rstrip("/") + "/", arg.lstrip("/"))

    return url


def serve(request, path, document_root=None, show_indexes=False):
    """
    Note: Modified to use X-Sendfile
    Serve static files below a given point in the directory structure.
    To use, put a URL pattern such as::
        from django.views.static import serve
        url(r'^(?P<path>.*)$', serve, {'document_root': '/path/to/my/files/'})
    in your URLconf. You must provide the ``document_root`` param. You may
    also set ``show_indexes`` to ``True`` if you'd like to serve a basic index
    of the directory.  This index view will use the template hardcoded below,
    but if you'd like to override it, you can create a template called
    ``static/directory_index.html``.
    """
    path = posixpath.normpath(unquote(path)).lstrip("/")
    fullpath = safe_join(document_root, path)
    if os.path.isdir(fullpath):
        if show_indexes:
            return directory_index(path, fullpath)
        raise Http404("Directory indexes are not allowed here.")
    if not os.path.exists(fullpath):
        raise Http404('"%(path)s" does not exist' % {"path": fullpath})
    # Respect the If-Modified-Since header.
    statobj = os.stat(fullpath)
    if not was_modified_since(
        request.META.get("HTTP_IF_MODIFIED_SINCE"), statobj.st_mtime, statobj.st_size
    ):
        return HttpResponseNotModified()
    response = HttpResponse()
    response["X-Sendfile"] = fullpath

    return response


def hash_string(s):
    try:
        return hashlib.sha1(s).hexdigest()
    except (UnicodeEncodeError, TypeError):
        return hashlib.sha1(s.encode("utf-8")).hexdigest()
