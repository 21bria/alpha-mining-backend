from django.contrib.auth.models import Group, Permission
from rest_framework import serializers

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class GroupPermissionsSerializer(serializers.Serializer):
    permissions = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True
    )