"""
Serializers for the Accounts app.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, StudentProfile, MentorProfile
from apps.careers.serializers import CareerSerializer, RoadmapStageSerializer


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.STUDENT)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'password_confirm',
            'role', 'first_name', 'last_name', 'phone',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        return value

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data, password=password)

        # Create appropriate profile based on role
        if user.role == User.Role.STUDENT:
            StudentProfile.objects.create(user=user)
        elif user.role == User.Role.MENTOR:
            MentorProfile.objects.create(user=user)

        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'), username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid email or password.')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled.')
        else:
            raise serializers.ValidationError('Must include email and password.')

        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile."""

    role_display = serializers.CharField(source='get_role_display', read_only=True)
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'avatar', 'bio', 'timezone', 'role', 'role_display',
            'is_verified', 'created_at', 'updated_at', 'profile',
        ]
        read_only_fields = ['id', 'email', 'role', 'is_verified', 'created_at', 'updated_at']

    def get_profile(self, obj):
        if obj.is_student:
            return StudentProfileSerializer(obj.student_profile).data if hasattr(obj, 'student_profile') else None
        elif obj.is_mentor:
            return MentorProfileSerializer(obj.mentor_profile).data if hasattr(obj, 'mentor_profile') else None
        return None


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'avatar', 'bio', 'timezone']


def get_active_careers():
    from apps.careers.models import Career
    return Career.objects.filter(is_active=True)


def get_active_roadmap_stages():
    from apps.careers.models import RoadmapStage
    return RoadmapStage.objects.filter(is_active=True)


class StudentProfileSerializer(serializers.ModelSerializer):
    """Serializer for student profile."""

    career = CareerSerializer(read_only=True)
    career_id = serializers.PrimaryKeyRelatedField(
        queryset=get_active_careers(),
        source='career',
        write_only=True,
        required=False,
        allow_null=True,
    )
    current_stage = RoadmapStageSerializer(read_only=True)
    current_stage_id = serializers.PrimaryKeyRelatedField(
        queryset=get_active_roadmap_stages(),
        source='current_stage',
        write_only=True,
        required=False,
        allow_null=True,
    )
    progress_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            'id', 'career', 'career_id', 'current_stage', 'current_stage_id',
            'skills_data', 'onboarding_complete', 'preferred_schedule',
            'learning_goals', 'progress_percentage', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'progress_percentage']


class MentorProfileSerializer(serializers.ModelSerializer):
    """Serializer for mentor profile."""

    expertise_careers = CareerSerializer(many=True, read_only=True)
    expertise_career_ids = serializers.PrimaryKeyRelatedField(
        queryset=get_active_careers(),
        source='expertise_careers',
        write_only=True,
        many=True,
        required=False,
    )
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)

    class Meta:
        model = MentorProfile
        fields = [
            'id', 'user_email', 'user_name', 'user_avatar',
            'expertise_careers', 'expertise_career_ids',
            'hourly_rate', 'availability_data', 'rating', 'total_sessions',
            'bio', 'is_verified', 'is_available', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'rating', 'total_sessions', 'is_verified', 'created_at', 'updated_at']


class StudentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for student listings."""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    career = CareerSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            'id', 'user_email', 'user_name', 'user_avatar',
            'career', 'onboarding_complete', 'progress_percentage',
        ]


class MentorListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for mentor listings."""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    expertise_careers = CareerSerializer(many=True, read_only=True)

    class Meta:
        model = MentorProfile
        fields = [
            'id', 'user_email', 'user_name', 'user_avatar',
            'expertise_careers', 'hourly_rate', 'rating', 'total_sessions',
            'bio', 'is_available',
        ]