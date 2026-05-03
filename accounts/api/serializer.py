from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from master.models import UserIUPAccess

def _get_iup_access_payload(user):
    """
    Standard payload IUP access untuk FE.
    - default_iup: {id, iup_code, iup_name} | null
    - allowed_iups: list of {id, iup_code, iup_name}
    """
    access = (
        UserIUPAccess.objects
        .select_related("default_iup")
        .prefetch_related("allowed_iups")
        .filter(user=user)
        .first()
    )

    default_iup = None
    allowed_iups = []

    if access:
        if access.default_iup:
            default_iup = {
                "id": access.default_iup.id,
                "iup_code": access.default_iup.iup_code,
                "iup_name": access.default_iup.iup_name,
            }
        allowed_iups = [
            {"id": i.id, "iup_code": i.iup_code, "iup_name": i.iup_name}
            for i in access.allowed_iups.all()
        ]

    return {"default_iup": default_iup, "allowed_iups": allowed_iups}


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
        # data["user"] = {
        #     "id": user.id,
        #     "username": user.get_username(),
        #     "role": user.role,
        #     "is_superuser": user.is_superuser,
        #     "is_system": user.is_system,
        #     "is_management": user.is_management,
        #     "is_global_viewer": user.is_global_viewer,
        #     "is_site_user": user.is_site_user,
        # }
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
