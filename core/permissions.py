from __future__ import annotations
from typing import Optional, Set
from rest_framework.permissions import BasePermission, SAFE_METHODS

def user_allowed_iup_ids(user) -> Set[int]:
    ids = set(getattr(user, "allowed_iup_ids", None) or [])
    did = getattr(user, "default_iup_id", None)
    if did:
        try:
            ids.add(int(did))
        except Exception:
            pass
    clean = set()
    for x in ids:
        try:
            clean.add(int(x))
        except Exception:
            continue
    return clean


def get_obj_iup_id(obj) -> Optional[int]:
    if hasattr(obj, "iup_id") and obj.iup_id is not None:
        try:
            return int(obj.iup_id)
        except Exception:
            return None
    iup = getattr(obj, "iup", None)
    if iup is not None and hasattr(iup, "id"):
        try:
            return int(iup.id)
        except Exception:
            return None
    return None


class RoleReadOnlyForViewer(BasePermission):
    """
    GLOBAL_VIEWER hanya boleh read (GET/HEAD/OPTIONS).
    Role lain boleh lanjut (dibatasi oleh queryset+serializer).
    """
    def has_permission(self, request, view):
        u = request.user
        if not u or not u.is_authenticated:
            return False

        if getattr(u, "is_system", False) or getattr(u, "is_superuser", False):
            return True

        if getattr(u, "is_global_viewer", False):
            return request.method in SAFE_METHODS

        return True


class IUPObjectPermission(BasePermission):
    """
    Cegah akses object lintas IUP via URL ID.
    """
    def has_object_permission(self, request, view, obj):
        u = request.user
        if not u or not u.is_authenticated:
            return False

        if getattr(u, "is_system", False) or getattr(u, "is_superuser", False):
            return True

        allowed = user_allowed_iup_ids(u)
        oid = get_obj_iup_id(obj)
        return (oid is not None) and (oid in allowed)

class GlobalMasterPermission(BasePermission):
    """
    Permission untuk master data global (material, vendor, dll)
    """

    def has_permission(self, request, view):
        u = request.user

        if not u or not u.is_authenticated:
            return False

        # SYSTEM / SUPERUSER / MANAGEMENT bebas
        if u.is_system or u.is_superuser or u.is_management:
            return True

        # GLOBAL VIEWER hanya read
        if u.is_global_viewer:
            return request.method in SAFE_METHODS

        # ambil model permission otomatis
        model = getattr(view.queryset.model, "_meta", None)
        if not model:
            return False

        app = model.app_label
        name = model.model_name

        if request.method in SAFE_METHODS:
            return u.has_perm(f"{app}.view_{name}")

        if request.method == "POST":
            return u.has_perm(f"{app}.add_{name}")

        if request.method in ["PUT", "PATCH"]:
            return u.has_perm(f"{app}.change_{name}")

        if request.method == "DELETE":
            return u.has_perm(f"{app}.delete_{name}")

        return False
    
class IsSystemAdmin(BasePermission):
    """
    Hanya SYSTEM role yang boleh akses endpoint admin
    (users, groups, permissions).
    """

    message = "Only system administrators can access this endpoint."

    def has_permission(self, request, view):
        u = request.user

        if not u or not u.is_authenticated:
            return False

        # superuser tetap boleh
        if getattr(u, "is_superuser", False):
            return True

        # hanya SYSTEM
        return getattr(u, "role", None) == "SYSTEM"