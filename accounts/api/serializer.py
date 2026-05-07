from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import json
from master.models import MineIUP

# def _get_iup_access_payload(user):
#     """
#     Standard payload IUP access untuk FE.
#     - default_iup: {id, iup_code, iup_name} | null
#     - allowed_iups: list of {id, iup_code, iup_name}
#     """
#     access = (
#         UserIUPAccess.objects
#         .select_related("default_iup")
#         .prefetch_related("allowed_iups")
#         .filter(user=user)
#         .first()
#     )

#     default_iup = None
#     allowed_iups = []

#     if access:
#         if access.default_iup:
#             default_iup = {
#                 "id": access.default_iup.id,
#                 "iup_code": access.default_iup.iup_code,
#                 "iup_name": access.default_iup.iup_name,
#             }
#         allowed_iups = [
#             {"id": i.id, "iup_code": i.iup_code, "iup_name": i.iup_name}
#             for i in access.allowed_iups.all()
#         ]

#     return {"default_iup": default_iup, "allowed_iups": allowed_iups}

def _get_iup_access_payload(user):

    default_iup = None
    allowed_iups = []

    #
    # DEFAULT IUP
    #
    default_iup_id = getattr(user, "default_iup_id", None)

    if default_iup_id:
        iup = MineIUP.objects.filter(id=default_iup_id).first()

        if iup:
            default_iup = {
                "id": iup.id,
                "iup_code": iup.iup_code,
                "iup_name": iup.iup_name,
            }

    # ALLOWED IUPS
    raw_allowed = getattr(user, "allowed_iup_ids", None) or []

    if isinstance(raw_allowed, str):
        try:
            raw_allowed = json.loads(raw_allowed)
        except Exception:
            raw_allowed = []

    iups = MineIUP.objects.filter(id__in=raw_allowed)

    allowed_iups = [
        {
            "id": i.id,
            "iup_code": i.iup_code,
            "iup_name": i.iup_name,
        }
        for i in iups
    ]

    # fallback
    if default_iup and not allowed_iups:
        allowed_iups.append(default_iup)

    return {
        "default_iup": default_iup,
        "allowed_iups": allowed_iups,
    }


class LoginSerializer(TokenObtainPairSerializer):
    """
    Login pakai username/password bawaan AbstractUser.
    Bisa kamu ubah kalau mau login via email.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Optional: taruh claim role biar FE gampang baca (tidak wajib)
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        # Extra info buat FE
        data["user"] = {
            "id": user.id,
            "username": user.get_username(),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": f"{user.first_name} {user.last_name}".strip() or user.get_username(),
            "role": user.role,
            "is_superuser": user.is_superuser,
            "is_system": user.is_system,
            "is_management": user.is_management,
            "is_global_viewer": user.is_global_viewer,
            "is_site_user": user.is_site_user,
        }
        data["iup_access"] = _get_iup_access_payload(user)

        return data
