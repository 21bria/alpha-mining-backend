# accounts/api/admin_serializers.py
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

User = get_user_model()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import serializers

User = get_user_model()

class GroupMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]

class AdminUserSerializer(serializers.ModelSerializer):
    # WRITE: terima list of ids
    groups = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Group.objects.all(),
        required=False,
        write_only=True,
    )

    # READ: tampilkan detail group
    groups_detail = GroupMiniSerializer(source="groups", many=True, read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "is_active", "role",
            "default_iup_id", "allowed_iup_ids",
            "groups",          # write_only
            "groups_detail",   # read_only
            "password",
        ]
        extra_kwargs = {"password": {"write_only": True, "required": False}}

    def create(self, validated_data):
        groups = validated_data.pop("groups", [])
        password = validated_data.pop("password", None)

        u = User(**validated_data)
        # u.set_password(password or "Password123!")
        u.set_password(password or "kawi@2025")
        u.save()

        if groups:
            u.groups.set(groups)
        return u

    def update(self, instance, validated_data):
        groups = validated_data.pop("groups", None)
        password = validated_data.pop("password", None)

        for k, v in validated_data.items():
            setattr(instance, k, v)

        if password:
            instance.set_password(password)

        instance.save()

        if groups is not None:
            instance.groups.set(groups)

        return instance