from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializer import LoginSerializer
from .serializer import _get_iup_access_payload
from accounts.models_user_profile import UserProfile
from master.models import UserIUPAccess, MineIUP


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    # def get(self, request):
    #     user = request.user

    #     # permissions efektif: direct user perms + group perms (Django built-in)
    #     perms = sorted(list(user.get_all_permissions()))

    #     groups = list(user.groups.values("id", "name"))

    #     return Response({
    #         "user": {
    #             "id": user.id,
    #             "username": user.get_username(),
    #             "role": user.role,
    #             "is_superuser": user.is_superuser,
    #             "is_system": user.is_system,
    #             "is_management": user.is_management,
    #             "is_global_viewer": user.is_global_viewer,
    #             "is_site_user": user.is_site_user,
    #             "groups": groups,
    #             "permissions": perms,
    #         },
            
    #         "iup_access": _get_iup_access_payload(user),
    #     })

    def get(self, request):
        user = request.user

        perms = sorted(list(user.get_all_permissions()))
        groups = list(user.groups.values("id", "name"))

        profile, _ = UserProfile.objects.get_or_create(user=user)

        if not profile.full_name:
            profile.full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.get_username()

        if not profile.language:
            profile.language = "id"

        if not profile.timezone:
            profile.timezone = "Asia/Jakarta"

        profile.save()

        if profile.avatar:
            avatar_url = request.build_absolute_uri(profile.avatar.url)
        elif profile.gender == "female":
            avatar_url = "/avatars/default-female.jpg"
        elif profile.gender == "male":
            avatar_url = "/avatars/default-male.jpg"
        else:
            avatar_url = "/avatars/default-user.jpg"

        return Response({
            "user": {
                "id": user.id,
                "username": user.get_username(),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": profile.full_name,
                "role": user.role,
                "is_superuser": user.is_superuser,
                "is_system": user.is_system,
                "is_management": user.is_management,
                "is_global_viewer": user.is_global_viewer,
                "is_site_user": user.is_site_user,
                "groups": groups,
                "permissions": perms,

                "profile": {
                    "full_name": profile.full_name,
                    "gender": profile.gender,
                    "avatar_url": avatar_url,
                    "language": profile.language,
                    "timezone": profile.timezone,
                },
            },
            "iup_access": _get_iup_access_payload(user),
        })

class SetActiveIUPView(APIView):
    """
    Simpan active/default iup untuk user.
    Karena kamu punya UserIUPAccess.default_iup, kita pakai itu sebagai "active iup".
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        iup_id = request.data.get("iup_id")
        if not iup_id:
            return Response({"detail": "iup_id required"}, status=400)

        iup = MineIUP.objects.filter(id=iup_id).first()
        if not iup:
            return Response({"detail": "IUP not found"}, status=404)

        user = request.user

        # SYSTEM/superuser boleh set apa saja
        if not user.is_system:
            access = UserIUPAccess.objects.filter(user=user).prefetch_related("allowed_iups").first()
            if not access:
                return Response({"detail": "No IUP access configured for this user"}, status=403)

            allowed_ids = set(access.allowed_iups.values_list("id", flat=True))
            if iup.id not in allowed_ids:
                return Response({"detail": "You are not allowed to access this IUP"}, status=403)

        access, _ = UserIUPAccess.objects.get_or_create(user=user)
        access.default_iup = iup
        access.save(update_fields=["default_iup"])

        return Response({"active_iup": {"id": iup.id, "iup_code": iup.iup_code, "iup_name": iup.iup_name}}, status=200)