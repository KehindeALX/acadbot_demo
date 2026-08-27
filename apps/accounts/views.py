"""
Views for the Accounts app.
"""
from rest_framework import status, viewsets, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

from .models import User, StudentProfile, MentorProfile
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserSerializer,
    UserUpdateSerializer,
    StudentProfileSerializer,
    MentorProfileSerializer,
    MentorListSerializer,
)
from apps.core.permissions import IsOwnerOrReadOnly, IsStudent, IsMentor, IsMentorOrAdmin


@ensure_csrf_cookie
@api_view(['GET'])
@permission_classes([AllowAny])
def csrf_token_view(request):
    """Get CSRF token for session authentication."""
    return Response({'csrfToken': get_token(request)})


class AuthViewSet(viewsets.GenericViewSet):
    """ViewSet for authentication endpoints."""

    permission_classes = [AllowAny]

    def get_permissions(self):
        """
        register/login are public; me/update_me/logout require authentication.

        NOTE: these actions are wired directly via AuthViewSet.as_view({...})
        in urls.py rather than through a DRF router. The per-action
        `permission_classes` kwarg on @action only gets applied when a
        router merges it into initkwargs before calling .as_view() -- it is
        silently ignored for a manually-constructed .as_view() call like the
        one used here. Enforcing it explicitly in get_permissions() avoids
        relying on that mechanism.
        """
        if self.action in ('me', 'update_me', 'logout'):
            return [IsAuthenticated()]
        return [AllowAny()]

    @action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        """Register a new user (student or mentor)."""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'success': True,
                'message': 'Registration successful',
                'data': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        """Log in a user with session authentication."""
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return Response(
            {
                'success': True,
                'message': 'Login successful',
                'data': UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'], url_path='logout', permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Log out the current user."""
        logout(request)
        return Response(
            {'success': True, 'message': 'Logout successful'},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='me', permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get current user profile."""
        serializer = UserSerializer(request.user)
        return Response(
            {'success': True, 'data': serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['patch'], url_path='me', permission_classes=[IsAuthenticated])
    def update_me(self, request):
        """Update current user profile."""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'success': True, 'message': 'Profile updated', 'data': UserSerializer(request.user).data},
            status=status.HTTP_200_OK,
        )


class StudentProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for student profiles."""

    serializer_class = StudentProfileSerializer
    permission_classes = [IsAuthenticated, IsStudent, IsOwnerOrReadOnly]

    def get_queryset(self):
        return StudentProfile.objects.select_related('user', 'career', 'current_stage').filter(user=self.request.user)

    def get_object(self):
        return self.request.user.student_profile


class MentorProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for mentor profiles."""

    queryset = MentorProfile.objects.select_related('user').prefetch_related('expertise_careers')
    permission_classes = [IsAuthenticated, IsMentor, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.action == 'list':
            return MentorListSerializer
        return MentorProfileSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by career if provided
        career_id = self.request.query_params.get('career')
        if career_id:
            queryset = queryset.filter(expertise_careers__id=career_id)
        # Filter by availability
        if self.request.query_params.get('available') == 'true':
            queryset = queryset.filter(is_available=True)
        return queryset

    def get_object(self):
        if self.request.user.is_mentor:
            return self.request.user.mentor_profile
        return super().get_object()

    @action(detail=False, methods=['get'], url_path='me', permission_classes=[IsAuthenticated, IsMentor])
    def me(self, request):
        """Get current mentor's profile."""
        profile = request.user.mentor_profile
        serializer = self.get_serializer(profile)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['patch'], url_path='me', permission_classes=[IsAuthenticated, IsMentor])
    def update_me(self, request):
        """Update current mentor's profile."""
        profile = request.user.mentor_profile
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'success': True, 'message': 'Profile updated', 'data': serializer.data},
            status=status.HTTP_200_OK,
        )


class MentorPublicViewSet(viewsets.ReadOnlyModelViewSet):
    """Public read-only viewset for mentor listings."""

    queryset = MentorProfile.objects.select_related('user').prefetch_related('expertise_careers').filter(is_available=True, is_verified=True)
    serializer_class = MentorListSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['expertise_careers']
    search_fields = ['user__first_name', 'user__last_name', 'bio']
    ordering_fields = ['rating', 'total_sessions', 'hourly_rate']
    ordering = ['-rating', '-total_sessions']