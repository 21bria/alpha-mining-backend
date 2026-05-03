from django.contrib.auth.models import Group, Permission
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from core.permissions import IsSystemAdmin
from accounts.api.pagination import StandardResultsSetPagination
from .serializer import GroupSerializer, GroupPermissionsSerializer


class AdminGroupViewSet(ModelViewSet):
    queryset = Group.objects.all().order_by("name")
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering_fields = ["id", "name"]
    ordering = ["name"]

    @action(detail=True, methods=["get", "put"], url_path="permissions")
    def permissions(self, request, pk=None):
        group = self.get_object()

        # GET → load permission ids
        if request.method.lower() == "get":
            ids = list(group.permissions.values_list("id", flat=True))

            return Response({
                "group": group.name,
                "permissions": ids
            })

        # PUT → save permission ids
        serializer = GroupPermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        perms = Permission.objects.filter(
            id__in=serializer.validated_data["permissions"]
        )

        group.permissions.set(perms)

        return Response({
            "status": "ok",
            "count": group.permissions.count()
        })