"""
Views for the Matching app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import MatchRequest, Match, MentorMatch
from .serializers import (
    MatchRequestSerializer,
    MatchRequestCreateSerializer,
    MentorMatchSerializer,
    MatchSerializer,
    MatchActionSerializer,
)
from .services import create_match_suggestions, auto_match, find_best_mentors
from apps.core.permissions import IsStudent, IsMentor, IsOwnerOrMentorOrAdmin


class MatchRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for match requests."""

    permission_classes = [IsAuthenticated, IsStudent]

    def get_serializer_class(self):
        if self.action == 'create':
            return MatchRequestCreateSerializer
        return MatchRequestSerializer

    def get_queryset(self):
        return MatchRequest.objects.select_related('student').prefetch_related('preferred_careers').filter(student=self.request.user)

    def perform_create(self, serializer):
        match_request = serializer.save(student=self.request.user)
        # Create mentor suggestions
        create_match_suggestions(match_request)

    @action(detail=True, methods=['get'], url_path='suggestions')
    def suggestions(self, request, pk=None):
        """Get mentor suggestions for this match request."""
        match_request = self.get_object()
        suggestions = match_request.suggested_mentors.select_related('mentor__user', 'mentor__user__mentor_profile').prefetch_related('mentor__user__mentor_profile__expertise_careers').all()
        serializer = MentorMatchSerializer(suggestions, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=True, methods=['post'], url_path='auto-match')
    def auto_match(self, request, pk=None):
        """Automatically find and create the best match."""
        match_request = self.get_object()

        if match_request.status != MatchRequest.Status.PENDING:
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'Match request is not in pending status.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        match = auto_match(match_request)

        if not match:
            return Response(
                {'success': False, 'error': {'code': 404, 'message': 'No suitable mentors found.'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = MatchSerializer(match)
        return Response(
            {'success': True, 'message': 'Match created successfully', 'data': serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='refresh-suggestions')
    def refresh_suggestions(self, request, pk=None):
        """Refresh mentor suggestions for this match request."""
        match_request = self.get_object()
        create_match_suggestions(match_request)
        suggestions = match_request.suggested_mentors.select_related('mentor__user', 'mentor__user__mentor_profile').prefetch_related('mentor__user__mentor_profile__expertise_careers').all()
        serializer = MentorMatchSerializer(suggestions, many=True)
        return Response({'success': True, 'data': serializer.data})


class MatchViewSet(viewsets.ModelViewSet):
    """ViewSet for matches."""

    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrMentorOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_student:
            return Match.objects.select_related(
                'student', 'mentor', 'match_request'
            ).prefetch_related(
                'match_request__preferred_careers'
            ).filter(student=user)
        elif user.is_mentor:
            return Match.objects.select_related(
                'student', 'mentor', 'match_request'
            ).prefetch_related(
                'match_request__preferred_careers'
            ).filter(mentor=user)
        return Match.objects.select_related(
            'student', 'mentor', 'match_request'
        ).prefetch_related(
            'match_request__preferred_careers'
        ).all()

    @action(detail=True, methods=['post'], url_path='accept', permission_classes=[IsAuthenticated, IsMentor])
    def accept(self, request, pk=None):
        """Accept a match (mentor only)."""
        match = self.get_object()

        if match.mentor != request.user:
            return Response(
                {'success': False, 'error': {'code': 403, 'message': 'Only the mentor can accept this match.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        if match.status != Match.Status.PENDING:
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'Match is not in pending status.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        match.accept()

        serializer = self.get_serializer(match)
        return Response(
            {'success': True, 'message': 'Match accepted', 'data': serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='decline', permission_classes=[IsAuthenticated, IsMentor])
    def decline(self, request, pk=None):
        """Decline a match (mentor only)."""
        match = self.get_object()

        if match.mentor != request.user:
            return Response(
                {'success': False, 'error': {'code': 403, 'message': 'Only the mentor can decline this match.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        if match.status != Match.Status.PENDING:
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'Match is not in pending status.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        match.decline()

        serializer = self.get_serializer(match)
        return Response(
            {'success': True, 'message': 'Match declined', 'data': serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='cancel', permission_classes=[IsAuthenticated])
    def cancel(self, request, pk=None):
        """Cancel a match (student or mentor)."""
        match = self.get_object()

        if match.student != request.user and match.mentor != request.user:
            return Response(
                {'success': False, 'error': {'code': 403, 'message': 'Not authorized to cancel this match.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        if match.status in [Match.Status.COMPLETED, Match.Status.CANCELLED]:
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'Match cannot be cancelled.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        match.status = Match.Status.CANCELLED
        match.save(update_fields=['status', 'updated_at'])

        serializer = self.get_serializer(match)
        return Response(
            {'success': True, 'message': 'Match cancelled', 'data': serializer.data},
            status=status.HTTP_200_OK,
        )


class MentorMatchSuggestionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for mentor match suggestions."""

    serializer_class = MentorMatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MentorMatch.objects.select_related(
            'mentor__user', 'mentor__user__mentor_profile'
        ).prefetch_related(
            'mentor__user__mentor_profile__expertise_careers'
        ).filter(match_request__student=self.request.user)