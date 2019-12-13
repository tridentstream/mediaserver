import logging

from django.http import Http404
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from unplugged import JSONAPIObject, JSONAPIRoot, JSONSchema

logger = logging.getLogger(__name__)


class ConfigView(APIView):
    service = None
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        root = JSONAPIRoot()

        namespace = request.GET.get("namespace")
        key = request.GET.get("key")
        if not key or not namespace:
            raise Http404

        identifier = "%s/%s" % (namespace, key)

        obj = JSONAPIObject("setting", identifier)
        obj["namespace"] = namespace
        obj["key"] = key
        if request.GET.get("default"):
            obj["value"] = self.service.config.get_default_config(namespace, key)
        else:
            obj["value"] = self.service.config.get_user_config(
                request.user, namespace, key
            )

        root.append(obj)

        schema = self.service.config.get_config_schema(namespace, key)
        if schema:
            schema_obj = JSONAPIObject("schema", identifier)
            schema_obj["namespace"] = namespace
            schema_obj["key"] = key

            json_schema = JSONSchema()
            schema = schema()
            schema_obj["schema"] = json_schema.dump(schema)
            obj.add_relationship("schema", schema_obj)

        return Response(root.serialize(request))

    def delete(self, request):
        namespace = request.GET.get("namespace")
        key = request.GET.get("key")

        if request.GET.get("set_default") and request.user.is_superuser:
            self.service.config.set_default_config("configured", namespace, key, None)
        else:
            self.service.config.set_user_config(request.user, namespace, key, None)

        return Response({})

    def post(self, request):
        namespace = request.GET.get("namespace")
        key = request.GET.get("key")

        if request.GET.get("default") and request.user.is_superuser:
            self.service.config.set_default_config(
                "configured", namespace, key, request.data
            )
        else:
            self.service.config.set_user_config(
                request.user, namespace, key, request.data
            )

        return self.get(request)
