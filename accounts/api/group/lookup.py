from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from accounts.api.pagination import StandardResultsSetPagination 
from django.contrib.auth.models import Group, Permission
from core.permissions import IsSystemAdmin
from rest_framework import serializers
from django.contrib.auth.models import Group

class GroupLookupSerializer(serializers.ModelSerializer):
    value = serializers.CharField(source="id")
    label = serializers.CharField(source="name")

    class Meta:
        model = Group
        fields = ["value", "label"]


class GroupLookupViewSet(ReadOnlyModelViewSet):
    serializer_class = GroupLookupSerializer
    queryset = Group.objects.all().order_by("name")

    permission_classes = [IsAuthenticated, IsSystemAdmin]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    search_fields = ["name"]
    ordering_fields = ["name"]
    ordering = ["name"]