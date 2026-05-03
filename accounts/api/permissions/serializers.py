from rest_framework import serializers


class PermissionItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    code = serializers.CharField()
    name = serializers.CharField()
    codename = serializers.CharField()


class PermissionModelSerializer(serializers.Serializer):
    model = serializers.CharField()
    perms = PermissionItemSerializer(many=True)


class PermissionAppSerializer(serializers.Serializer):
    app = serializers.CharField()
    models = PermissionModelSerializer(many=True)