# views.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from accounts.models_user_profile import UserProfile
from .serializers import UserProfileSerializer

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, user):
        profile, created = UserProfile.objects.get_or_create(user=user)

        changed = False

        if not profile.full_name:
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            profile.full_name = full_name or user.username
            changed = True

        if not profile.gender:
            profile.gender = 'other'   # default neutral
            changed = True

        if not profile.language:
            profile.language = 'id'
            changed = True

        if not profile.timezone:
            profile.timezone = 'Asia/Jakarta'
            changed = True

        if changed:
            profile.save(update_fields=[
                'full_name',
                'gender',
                'language',
                'timezone',
                'updated_at',
            ])

        return profile

    def get(self, request):
        profile = self.get_object(request.user)
        serializer = UserProfileSerializer(profile, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        profile = self.get_object(request.user)
        serializer = UserProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'detail': 'Profile updated successfully.',
            'profile': serializer.data,
        })