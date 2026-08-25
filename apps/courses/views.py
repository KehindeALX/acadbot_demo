"""
Views for the Courses app.
"""
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Course, Lesson, Enrollment, LessonProgress
from .serializers import (
    CourseSerializer,
    CourseDetailSerializer,
    LessonSerializer,
    LessonDetailSerializer,
    EnrollmentSerializer,
    EnrollmentDetailSerializer,
    LessonProgressSerializer,
    QuizSubmissionSerializer,
    EnrollSerializer,
)
from apps.core.permissions import IsStudent, IsOwnerOrReadOnly


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for courses - read only for students."""

    queryset = Course.objects.select_related('career').filter(is_published=True, career__is_active=True)
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        career_slug = self.request.query_params.get('career')
        if career_slug:
            queryset = queryset.filter(career__slug=career_slug)
        return queryset

    @action(detail=True, methods=['post'], url_path='enroll', permission_classes=[IsAuthenticated, IsStudent])
    def enroll(self, request, pk=None):
        """Enroll the current student in this course."""
        course = self.get_object()
        student = request.user

        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            course=course,
            defaults={'status': Enrollment.Status.ACTIVE},
        )

        if not created and enrollment.status == Enrollment.Status.DROPPED:
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.save()

        serializer = EnrollmentSerializer(enrollment)
        return Response(
            {
                'success': True,
                'message': 'Enrolled successfully' if created else 'Re-enrolled successfully',
                'data': serializer.data,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for lessons."""

    queryset = Lesson.objects.select_related('course').filter(is_published=True, course__is_published=True)
    permission_classes = [IsAuthenticated, IsStudent]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LessonDetailSerializer
        return LessonSerializer

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """Mark lesson as complete."""
        lesson = self.get_object()
        enrollment = get_object_or_404(Enrollment, student=request.user, course=lesson.course)

        progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson,
        )

        progress.mark_complete()

        serializer = LessonProgressSerializer(progress)
        return Response(
            {'success': True, 'message': 'Lesson marked complete', 'data': serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='quiz')
    def quiz(self, request, pk=None):
        """Submit quiz answer for a lesson."""
        lesson = self.get_object()

        if not lesson.has_quiz:
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'This lesson does not have a quiz.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enrollment = get_object_or_404(Enrollment, student=request.user, course=lesson.course)

        serializer = QuizSubmissionSerializer(data=request.data, context={'lesson': lesson})
        serializer.is_valid(raise_exception=True)

        progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson,
        )

        result = progress.submit_quiz(serializer.validated_data['answer_index'])

        progress_serializer = LessonProgressSerializer(progress)
        return Response(
            {
                'success': True,
                'message': 'Quiz submitted',
                'data': {
                    'progress': progress_serializer.data,
                    'result': result,
                },
            },
            status=status.HTTP_200_OK,
        )


class EnrollmentViewSet(viewsets.ModelViewSet):
    """ViewSet for student enrollments."""

    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        return Enrollment.objects.select_related('course', 'course__career').filter(student=self.request.user)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EnrollmentDetailSerializer
        return EnrollmentSerializer

    @action(detail=True, methods=['get'], url_path='progress')
    def progress(self, request, pk=None):
        """Get detailed progress for an enrollment."""
        enrollment = self.get_object()
        serializer = EnrollmentDetailSerializer(enrollment)
        return Response({'success': True, 'data': serializer.data})