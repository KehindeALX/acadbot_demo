"""
Views for the Sessions app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from .models import Session, SessionRecurrence, Availability, SessionFeedback
from .serializers import (
    SessionSerializer,
    SessionCreateSerializer,
    SessionUpdateSerializer,
    SessionCompleteSerializer,
    SessionFeedbackSerializer,
    SessionFeedbackCreateSerializer,
    SessionRecurrenceSerializer,
    AvailabilitySerializer,
    AvailabilityCreateSerializer,
    MentorAvailabilitySerializer,
)
from apps.core.permissions import IsStudent, IsMentor, IsOwnerOrMentorOrAdmin
from apps.matching.models import Match


class SessionViewSet(viewsets.ModelViewSet):
    """ViewSet for sessions."""

    permission_classes = [IsAuthenticated, IsOwnerOrMentorOrAdmin]

    def get_serializer_class(self):
        if self.action == 'create':
            return SessionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SessionUpdateSerializer
        return SessionSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Session.objects.select_related(
            'student', 'mentor', 'match'
        ).prefetch_related('detailed_feedback')

        if user.is_student:
            return queryset.filter(student=user)
        elif user.is_mentor:
            return queryset.filter(mentor=user)
        return queryset.all()

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """Complete a session with feedback."""
        session = self.get_object()

        if session.status != Session.Status.IN_PROGRESS and session.status != Session.Status.SCHEDULED:
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'Session cannot be completed.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Only mentor can mark as completed (or student if mentor already started)
        if session.mentor != request.user and session.student != request.user:
            return Response(
                {'success': False, 'error': {'code': 403, 'message': 'Not authorized.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SessionCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Mark session as completed
        session.mark_completed()

        # Save feedback if provided
        feedback_data = serializer.validated_data
        if request.user == session.student:
            if feedback_data.get('feedback'):
                session.feedback_student = feedback_data['feedback']
            if feedback_data.get('rating'):
                session.rating_student = feedback_data['rating']
            if feedback_data.get('notes'):
                session.student_notes = feedback_data['notes']
        elif request.user == session.mentor:
            if feedback_data.get('feedback'):
                session.feedback_mentor = feedback_data['feedback']
            if feedback_data.get('rating'):
                session.rating_mentor = feedback_data['rating']
            if feedback_data.get('notes'):
                session.mentor_notes = feedback_data['notes']

        session.save(update_fields=[
            'feedback_student', 'feedback_mentor',
            'rating_student', 'rating_mentor',
            'student_notes', 'mentor_notes',
        ])

        # Also create detailed feedback entry
        if feedback_data.get('rating') or feedback_data.get('feedback'):
            feedback_type = Session.FeedbackType.STUDENT if request.user == session.student else Session.FeedbackType.MENTOR
            SessionFeedback.objects.update_or_create(
                session=session,
                author=request.user,
                feedback_type=feedback_type,
                defaults={
                    'rating': feedback_data.get('rating', 5),
                    'strengths': feedback_data.get('feedback', ''),
                    'additional_comments': feedback_data.get('notes', ''),
                }
            )

        response_serializer = SessionSerializer(session)
        return Response(
            {'success': True, 'message': 'Session completed', 'data': response_serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, pk=None):
        """Start a session (mentor only)."""
        session = self.get_object()

        if session.mentor != request.user:
            return Response(
                {'success': False, 'error': {'code': 403, 'message': 'Only mentor can start the session.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        if session.status != Session.Status.SCHEDULED:
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'Session is not scheduled.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.mark_started()

        serializer = SessionSerializer(session)
        return Response(
            {'success': True, 'message': 'Session started', 'data': serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """Cancel a session."""
        session = self.get_object()

        if session.student != request.user and session.mentor != request.user:
            return Response(
                {'success': False, 'error': {'code': 403, 'message': 'Not authorized to cancel this session.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not session.can_be_cancelled():
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'Session cannot be cancelled.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.cancel(request.user)

        serializer = SessionSerializer(session)
        return Response(
            {'success': True, 'message': 'Session cancelled', 'data': serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='reschedule')
    def reschedule(self, request, pk=None):
        """Reschedule a session."""
        session = self.get_object()

        if session.student != request.user and session.mentor != request.user:
            return Response(
                {'success': False, 'error': {'code': 403, 'message': 'Not authorized to reschedule this session.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not session.can_be_rescheduled():
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'Session cannot be rescheduled.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_scheduled_at = request.data.get('scheduled_at')
        new_duration = request.data.get('duration_minutes')

        if not new_scheduled_at:
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'scheduled_at is required.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.utils.dateparse import parse_datetime
        scheduled_dt = parse_datetime(new_scheduled_at)
        if not scheduled_dt:
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'Invalid datetime format.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if scheduled_dt < timezone.now():
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'Cannot reschedule to the past.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.scheduled_at = scheduled_dt
        if new_duration:
            session.duration_minutes = new_duration
        session.status = Session.Status.RESCHEDULED
        session.save(update_fields=['scheduled_at', 'duration_minutes', 'status', 'updated_at'])

        serializer = SessionSerializer(session)
        return Response(
            {'success': True, 'message': 'Session rescheduled', 'data': serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming(self, request):
        """Get upcoming sessions for the current user."""
        queryset = self.get_queryset().filter(
            status__in=[Session.Status.SCHEDULED, Session.Status.RESCHEDULED],
            scheduled_at__gt=timezone.now(),
        ).order_by('scheduled_at')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='past')
    def past(self, request):
        """Get past sessions for the current user."""
        queryset = self.get_queryset().filter(
            Q(status__in=[Session.Status.COMPLETED, Session.Status.CANCELLED, Session.Status.NO_SHOW]) |
            Q(scheduled_at__lt=timezone.now())
        ).order_by('-scheduled_at')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})


class SessionRecurrenceViewSet(viewsets.ModelViewSet):
    """ViewSet for session recurrences."""

    serializer_class = SessionRecurrenceSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrMentorOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_student:
            return SessionRecurrence.objects.select_related('session__student', 'session__mentor').filter(session__student=user)
        elif user.is_mentor:
            return SessionRecurrence.objects.select_related('session__student', 'session__mentor').filter(session__mentor=user)
        return SessionRecurrence.objects.select_related('session__student', 'session__mentor').all()


class AvailabilityViewSet(viewsets.ModelViewSet):
    """ViewSet for mentor availability (mentor only)."""

    permission_classes = [IsAuthenticated, IsMentor]

    def get_serializer_class(self):
        if self.action == 'create':
            return AvailabilityCreateSerializer
        return AvailabilitySerializer

    def get_queryset(self):
        return Availability.objects.filter(mentor=self.request.user)

    def perform_create(self, serializer):
        serializer.save(mentor=self.request.user)

    @action(detail=False, methods=['get'], url_path='my-schedule')
    def my_schedule(self, request):
        """Get mentor's weekly schedule."""
        availabilities = self.get_queryset().filter(is_recurring=True).order_by('day_of_week', 'start_time')
        serializer = self.get_serializer(availabilities, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['delete'], url_path='clear-all')
    def clear_all(self, request):
        """Clear all recurring availability."""
        self.get_queryset().filter(is_recurring=True).delete()
        return Response({'success': True, 'message': 'All recurring availability cleared'})


class MentorAvailabilityViewSet(viewsets.ReadOnlyModelViewSet):
    """Public view of mentor availability (for students)."""

    serializer_class = MentorAvailabilitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        mentor_id = self.kwargs.get('mentor_id')
        if not mentor_id:
            return Availability.objects.none()

        from apps.accounts.models import MentorProfile
        try:
            mentor_profile = MentorProfile.objects.select_related('user').get(user_id=mentor_id, is_verified=True)
        except MentorProfile.DoesNotExist:
            return Availability.objects.none()

        return Availability.objects.filter(
            mentor=mentor_profile.user,
            is_available=True,
        ).order_by('day_of_week', 'start_time')


class SessionFeedbackViewSet(viewsets.ModelViewSet):
    """ViewSet for session feedback."""

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return SessionFeedbackCreateSerializer
        return SessionFeedbackSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_student:
            return SessionFeedback.objects.select_related('session', 'author').filter(
                session__student=user
            )
        elif user.is_mentor:
            return SessionFeedback.objects.select_related('session', 'author').filter(
                session__mentor=user
            )
        return SessionFeedback.objects.select_related('session', 'author').all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'create':
            session_id = self.kwargs.get('session_pk') or self.request.data.get('session')
            if session_id:
                context['session'] = get_object_or_404(Session, id=session_id)
        return context

    def perform_create(self, serializer):
        session = self.get_serializer_context()['session']
        serializer.save(author=self.request.user, session=session)