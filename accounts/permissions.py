from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied


class IsReadOnlyGlobalViewer(BasePermission):
    """
    GLOBAL_VIEWER: hanya boleh read (GET/HEAD/OPTIONS).
    Role lain: diizinkan (cek detail bisa ditambah permission lain).
    """
    message = "Read-only access."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_global_viewer", False):
            return request.method in SAFE_METHODS

        return True


class TenantIUPPermission(BasePermission):
    """
    Permission untuk data model yang punya field `iup`
    atau serializer/view yang memaksa iup.

    Aturan:
    - SYSTEM (atau is_superuser): boleh semua
    - MANAGEMENT: boleh akses data untuk iup di allowed_iups
    - GLOBAL_VIEWER: boleh read-only untuk iup di allowed_iups
    - SITE_USER: hanya iup default_iup (atau allowed_iups jika kamu pakai itu)
    """

    message = "You don't have permission to access this IUP."

    def _user_allowed_iup_ids(self, user):
        # kalau kamu pakai allowed_iups
        if hasattr(user, "allowed_iups"):
            return set(user.allowed_iups.values_list("id", flat=True))
        return set()

    def _get_obj_iup_id(self, obj):
        # obj bisa punya iup langsung
        if hasattr(obj, "iup_id") and obj.iup_id:
            return obj.iup_id

        # atau iup lewat relasi (misalnya detail -> header)
        # kalau view set attribute iup_lookup_path = "hm_unit__iup_id"
        return None

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # SYSTEM / superuser: bebas
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return True

        # GLOBAL_VIEWER: hanya read
        if getattr(user, "is_global_viewer", False) and request.method not in SAFE_METHODS:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        user = request.user

        # SYSTEM / superuser: bebas
        if getattr(user, "is_system", False) or getattr(user, "is_superuser", False):
            return True

        # GLOBAL_VIEWER: hanya read
        if getattr(user, "is_global_viewer", False) and request.method not in SAFE_METHODS:
            return False

        allowed_iups = self._user_allowed_iup_ids(user)

        # SITE_USER: pakai default_iup sebagai scope utama
        if getattr(user, "is_site_user", False):
            if user.default_iup_id is None:
                return False
            return self._get_obj_iup_id(obj) == user.default_iup_id

        # MANAGEMENT / GLOBAL_VIEWER: boleh untuk allowed_iups
        if getattr(user, "is_management", False) or getattr(user, "is_global_viewer", False):
            obj_iup_id = self._get_obj_iup_id(obj)
            if obj_iup_id is None:
                # kalau obj tidak punya iup langsung, fallback: izinkan view handle filtering
                return True
            return obj_iup_id in allowed_iups

        return False


class RequireIUPForWrite(BasePermission):
    """
    Pastikan saat POST/PUT/PATCH, iup tidak bisa di-set sembarangan lewat payload.
    Idealnya iup di-set dari user (default_iup / active_iup) di perform_create.
    """
    message = "IUP must be set by server."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        # cegah user set iup via payload
        if "iup" in request.data or "iup_id" in request.data:
            raise PermissionDenied("Do not send iup/iup_id in payload. It is set by server.")

        return True