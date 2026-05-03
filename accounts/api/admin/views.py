# accounts/api/admin/views.py
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import filters
from django.contrib.auth import get_user_model
from .serializer import AdminUserSerializer
from core.permissions import IsSystemAdmin
from accounts.api.pagination import StandardResultsSetPagination 

User = get_user_model()

class AdminUserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["username"]
    ordering_fields = ["id", "username"]
    ordering = ["username"]

    @action(detail=True, methods=["put"], url_path="groups")
    def set_groups(self, request, pk=None):
        u = self.get_object()
        group_ids = request.data.get("groups", [])
        u.groups.set(group_ids)
        return Response({"status": "ok", "groups": list(u.groups.values_list("id", flat=True))})

    @action(detail=True, methods=["get"], url_path="effective")
    def effective(self, request, pk=None):
        u = self.get_object()
        perms = sorted(list(u.get_all_permissions()))
        groups = list(u.groups.values("id", "name"))
        return Response({
            "id": u.id,
            "role": u.role,
            "default_iup_id": u.default_iup_id,
            "allowed_iup_ids": u.allowed_iup_ids,
            "groups": groups,
            "permissions": perms,
        })