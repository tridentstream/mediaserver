from timeoutthreadpoolexecutor import TimeoutThreadPoolExecutor  # isort:skip
from concurrent.futures import thread  # isort:skip

thread.ThreadPoolExecutor = TimeoutThreadPoolExecutor  # isort:skip

import asyncio
import logging
import logging.handlers
import os
import sys
import time

import daphne.server
import django
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from channels.routing import get_default_application
from txasgiresource import ASGIResource
from zope.interface import implementer

from twisted.application import service
from twisted.application.service import IServiceMaker
from twisted.internet import endpoints, reactor
from twisted.plugin import IPlugin
from twisted.python import log, usage
from twisted.web import resource, server, static

os.environ["DJANGO_SETTINGS_MODULE"] = "main.settings"

logger = logging.getLogger(__name__)


class Options(usage.Options):
    optFlags = [
        ["trace", "t", "Enable trace logging"],
        ["debug", "d", "Enable debug logging"],
        ["stdout", "s", "Log to stdout"],
        ["djangodebug", "j", "Enable django debug"],
        ["clearcache", "c", "Clear caching on every action"],
    ]

    optParameters = [
        [
            "description",
            "e",
            "tcp:45477:interface=0.0.0.0",
            "Twisted server description",
        ],
        [
            "reverseproxy",
            "r",
            "smart",
            "Set reverse proxy mode (uses x-forwarded headers), values are on, off and smart",
        ],
    ]


class Root(resource.Resource):
    def __init__(self, asgi_resource):
        resource.Resource.__init__(self)
        self.asgi_resource = asgi_resource

    def getChild(self, path, request):
        path0 = request.prepath.pop(0)
        request.postpath.insert(0, path0)
        return self.asgi_resource


class ASGIService(service.Service):
    def __init__(self, site, resource, description):
        self.site = site
        self.resource = resource
        self.description = description

    def startService(self):
        self.endpoint = endpoints.serverFromString(reactor, self.description)
        self.endpoint.listen(self.site)

    def stopService(self):
        self.resource.stop()


class SchedulerService(service.Service):
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def startService(self):
        self.scheduler.start()

    def stopService(self):
        self.scheduler.shutdown()


class File(static.File):
    def directoryListing(self):
        return self.forbidden


@implementer(IServiceMaker, IPlugin)
class ServiceMaker(object):
    tapname = "tridentstream"
    description = "Tridentstream media server"
    options = Options

    def makeService(self, options):
        TRACE_LEVEL_NUM = 5
        logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")

        def trace(self, message, *args, **kws):
            self._log(TRACE_LEVEL_NUM, message, args, **kws)

        logging.Logger.trace = trace

        import urllib3  # TODO: remove this code again, not sure why it doesn't just fix it by itself.

        urllib3.disable_warnings()

        if options["djangodebug"]:
            os.environ["DJANGO_DEBUG"] = "1"

        logging.getLogger("rebulk.rules").setLevel(logging.WARNING)
        logging.getLogger("rebulk.rebulk").setLevel(logging.WARNING)
        logging.getLogger("chardet.charsetprober").setLevel(logging.WARNING)

        if options["trace"]:
            log_level = TRACE_LEVEL_NUM
            asyncio.set_event_loop(reactor._asyncioEventloop)
            asyncio.get_event_loop().set_debug(True)
        elif options["debug"]:
            log_level = logging.DEBUG
        else:
            log_level = logging.WARNING

        if options["stdout"]:
            handler = logging.StreamHandler(sys.stdout)
        else:
            handler = logging.handlers.RotatingFileHandler(
                "tridentstream.log", maxBytes=50 * 1024 * 1024, backupCount=5
            )

        handler.setLevel(log_level)
        formatter = logging.Formatter(
            "%(asctime)-15s:%(levelname)s:%(name)s:%(lineno)d:%(message)s"
        )
        handler.setFormatter(formatter)
        root = logging.getLogger()
        root.setLevel(log_level)
        root.addHandler(handler)

        observer = log.PythonLoggingObserver()
        observer.start()

        from django.conf import settings

        settings.TWISTD_PIDFILE = options.parent['pidfile']

        if options["clearcache"]:
            settings.DEBUG_CLEAR_CACHE = True
            from django.core.cache import cache

            cache.clear()

        multi = service.MultiService()

        django.setup()
        application = get_default_application()

        if options["reverseproxy"] == "on":
            asgiresource = ASGIResource(
                application, use_proxy_headers=True, use_x_sendfile=True
            )
        elif options["reverseproxy"] == "off":
            asgiresource = ASGIResource(
                application, use_proxy_proto_header=True, use_x_sendfile=True
            )
        else:
            asgiresource = ASGIResource(
                application, automatic_proxy_header_handling=True, use_x_sendfile=True
            )
        r = Root(asgiresource)

        from thomas import OutputBase

        http_output_cls = OutputBase.find_plugin("http")
        http_output = http_output_cls(url_prefix="stream")
        http_output.start()
        r.putChild(b"stream", http_output.resource)

        settings.THOMAS_HTTP_OUTPUT = http_output

        from django.contrib import admin

        r.putChild(
            settings.STATIC_URL.strip("/").encode("utf-8"),
            File(
                os.path.join(os.path.dirname(django.contrib.admin.__file__), "static")
            ),
        )

        # Gluing it all together
        site = server.Site(r)

        multi.addService(ASGIService(site, asgiresource, options["description"]))

        scheduler_service = SchedulerService()
        multi.addService(scheduler_service)
        settings.SCHEDULER = scheduler_service.scheduler

        def initialize():
            def _initialize():
                from unplugged.bootstrap import bootstrap_all

                bootstrap_all()

            loop = asyncio.get_running_loop()
            asyncio.ensure_future(loop.run_in_executor(None, _initialize))

        reactor.callLater(0, initialize)

        # Django doesn't seem to want to kill connections
        def cleanup_database_connections():
            def cleanup_thread():
                from django.db import close_old_connections

                close_old_connections()

            settings.SCHEDULER.add_job(cleanup_thread, "interval", minutes=15)

        reactor.callLater(0, cleanup_database_connections)

        return multi


tridentstream = ServiceMaker()
