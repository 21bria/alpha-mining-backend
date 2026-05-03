from rest_framework import serializers
from accounts.models_user_profile import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    avatar_url = serializers.SerializerMethodField()


    class Meta:
        model = UserProfile
        fields = [
            'username',
            'email',
            'full_name',
            'phone',
            'bio',
            'avatar',
            'avatar_url',
            'gender',
            'language',
            'timezone',
            'birth_date',
            'address',
        ]
        read_only_fields = ['username', 'email', 'avatar_url']

    def validate_phone(self, value):
        if value and len(value) < 8:
            raise serializers.ValidationError("Phone number is too short.")
        return value

    def get_avatar_url(self, obj):
        request = self.context.get('request')

        if obj.avatar:
            url = obj.avatar.url
        elif obj.gender == 'male':
            url = '/avatars/default-male.jpg'
        elif obj.gender == 'female':
            url = '/avatars/default-female.jpg'
        else:
            url = '/avatars/default-user.jpg'

        if request:
            return request.build_absolute_uri(url)

        return url