"""
Views for the Progress app.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from .models import SkillAssessment, Milestone, LearningPath, ProgressSnapshot
from .serializers import (
    SkillAssessmentSerializer,
    SkillAssessmentCreateSerializer,
    MilestoneSerializer,
    MilestoneCreateSerializer,
    LearningPathSerializer,
    LearningPathUpdateSerializer,
    ProgressSnapshotSerializer,
    StudentProgressSummarySerializer,
)
from apps.core.permissions import IsStudent, IsMentor, IsOwnerOrMentorOrAdmin


class SkillAssessmentViewSet(viewsets.ModelViewSet):
    """ViewSet for skill assessments."""

    permission_classes = [IsAuthenticated, IsStudent]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SkillAssessmentCreateSerializer
        return SkillAssessmentSerializer

    def get_queryset(self):
        return SkillAssessment.objects.select_related(
            'career_skill__career', 'assessed_by'
        ).filter(student=self.request.user).order_by('career_skill__career', 'career_skill__order')

    @action(detail=False, methods=['get'], url_path='by-career')
    def by_career(self, request):
        """Get skill assessments grouped by career."""
        career_id = request.query_params.get('career_id')
        queryset = self.get_queryset()

        if career_id:
            queryset = queryset.filter(career_skill__career_id=career_id)

        # Group by career
        from itertools import groupby
        from apps.careers.serializers import CareerSerializer

        assessments = list(queryset)
        assessments.sort(key=lambda x: x.career_skill.career.id)

        result = []
        for career, group in groupby(assessments, key=lambda x: x.career_skill.career):
            career_serializer = CareerSerializer(career)
            skills_serializer = SkillAssessmentSerializer(list(group), many=True)
            result.append({
                'career': career_serializer.data,
                'assessments': skills_serializer.data,
            })

        return Response({'success': True, 'data': result})

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """Get skill assessment summary statistics."""
        queryset = self.get_queryset()

        # Get latest assessment per skill
        latest_assessments = queryset.order_by('career_skill', '-assessed_at').distinct('career_skill')

        total_assessed = latest_assessments.exclude(assessed_level__isnull=True).count()
        total_self_rated = latest_assessments.exclude(self_rated_level__isnull=True).count()

        avg_level = latest_assessments.exclude(assessed_level__isnull=True).aggregate(
            avg=Avg('assessed_level')
        )['avg'] or 0

        by_level = latest_assessments.exclude(assessed_level__isnull=True).values('assessed_level').annotate(
            count=Count('id')
        ).order_by('assessed_level')

        return Response({
            'success': True,
            'data': {
                'total_skills_assessed': total_assessed,
                'total_self_rated': total_self_rated,
                'average_skill_level': round(avg_level, 2),
                'by_level': list(by_level),
            }
        })


class MilestoneViewSet(viewsets.ModelViewSet):
    """ViewSet for milestones."""

    permission_classes = [IsAuthenticated, IsStudent]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MilestoneCreateSerializer
        return MilestoneSerializer

    def get_queryset(self):
        return Milestone.objects.select_related('career').filter(student=self.request.user)

    @action(detail=False, methods=['get'], url_path='by-type')
    def by_type(self, request):
        """Get milestones grouped by type."""
        queryset = self.get_queryset()

        from itertools import groupby
        milestones = list(queryset)
        milestones.sort(key=lambda x: x.milestone_type)

        result = {}
        for mtype, group in groupby(milestones, key=lambda x: x.milestone_type):
            serializer = MilestoneSerializer(list(group), many=True)
            result[mtype] = serializer.data

        return Response({'success': True, 'data': result})

    @action(detail=False, methods=['get'], url_path='recent')
    def recent(self, request):
        """Get recent milestones (last 10)."""
        queryset = self.get_queryset()[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True, 'data': serializer.data})


class LearningPathViewSet(viewsets.ModelViewSet):
    """ViewSet for learning paths."""

    permission_classes = [IsAuthenticated, IsStudent]

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return LearningPathUpdateSerializer
        return LearningPathSerializer

    def get_queryset(self):
        return LearningPath.objects.select_related(
            'career', 'current_stage'
        ).filter(student=self.request.user)

    def get_object(self):
        """Get or create learning path for current user."""
        career_id = self.kwargs.get('pk')
        if career_id:
            return get_object_or_404(self.get_queryset(), career_id=career_id)

        # For detail without pk, get the active learning path
        return get_object_or_404(self.get_queryset(), is_active=True)

    @action(detail=True, methods=['post'], url_path='advance')
    def advance(self, request, pk=None):
        """Advance to the next stage."""
        learning_path = self.get_object()
        next_stage = learning_path.get_next_stage()

        if not next_stage:
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'Already at the final stage.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        learning_path.advance_stage(next_stage)

        serializer = LearningPathSerializer(learning_path)
        return Response(
            {'success': True, 'message': f'Advanced to {next_stage.title}', 'data': serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='set-stage')
    def set_stage(self, request, pk=None):
        """Set current stage directly."""
        learning_path = self.get_object()
        stage_id = request.data.get('stage_id')

        if not stage_id:
            return Response(
                {'success': False, 'error': {'code': 400, 'message': 'stage_id is required.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.careers.models import RoadmapStage
        try:
            new_stage = RoadmapStage.objects.get(id=stage_id, career=learning_path.career)
        except RoadmapStage.DoesNotExist:
            return Response(
                {'success': False, 'error': {'code': 404, 'message': 'Stage not found.'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        learning_path.advance_stage(new_stage)

        serializer = LearningPathSerializer(learning_path)
        return Response(
            {'success': True, 'message': f'Stage set to {new_stage.title}', 'data': serializer.data},
            status=status.HTTP_200_OK,
        )


class ProgressSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for progress snapshots."""

    serializer_class = ProgressSnapshotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProgressSnapshot.objects.select_related('career').filter(student=self.request.user)


class StudentProgressViewSet(viewsets.GenericViewSet):
    """Aggregated progress view for student dashboard."""

    permission_classes = [IsAuthenticated, IsStudent]

    def get_serializer_class(self):
        return StudentProgressSummarySerializer

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """Get comprehensive progress summary for the student."""
        student = request.user

        # Get or create learning path
        learning_path = LearningPath.objects.select_related('career', 'current_stage').filter(
            student=student, is_active=True
        ).first()

        # Get skill assessments
        skill_assessments = SkillAssessment.objects.select_related('career_skill__career').filter(
            student=student
        ).order_by('career_skill__career', 'career_skill__order')

        # Get milestones
        milestones = Milestone.objects.select_related('career').filter(
            student=student
        )[:20]

        # Get recent snapshots
        snapshots = ProgressSnapshot.objects.select_related('career').filter(
            student=student
        )[:12]

        # Aggregate stats
        career = learning_path.career if learning_path else None

        if career:
            from apps.courses.models import Enrollment
            from apps.matching.models import Match
            from apps.sessions.models import Session

            courses_completed = Enrollment.objects.filter(
                student=student, course__career=career, completed_at__isnull=False
            ).count()

            sessions_completed = Session.objects.filter(
                student=student, match__career=career, status=Session.Status.COMPLETED
            ).count()

            learning_path_progress = learning_path.get_progress_percent() if learning_path else 0
        else:
            courses_completed = 0
            sessions_completed = 0
            learning_path_progress = 0

        latest_assessments = skill_assessments.order_by('career_skill', '-assessed_at').distinct('career_skill')
        avg_level = latest_assessments.exclude(assessed_level__isnull=True).aggregate(
            avg=Avg('assessed_level')
        )['avg'] or 0

        total_skills_assessed = latest_assessments.exclude(assessed_level__isnull=True).count()
        milestones_count = milestones.count()

        data = {
            'career': career,
            'learning_path': learning_path,
            'skill_assessments': skill_assessments,
            'milestones': milestones,
            'recent_snapshots': snapshots,
            'total_skills_assessed': total_skills_assessed,
            'average_skill_level': round(avg_level, 2),
            'milestones_count': milestones_count,
            'courses_completed': courses_completed,
            'sessions_completed': sessions_completed,
            'learning_path_progress': learning_path_progress,
        }

        serializer = StudentProgressSummarySerializer(data)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['post'], url_path='generate-snapshot')
    def generate_snapshot(self, request):
        """Generate a new progress snapshot for the student."""
        student = request.user
        career_id = request.data.get('career_id')

        if not career_id:
            learning_path = LearningPath.objects.filter(student=student, is_active=True).first()
            if not learning_path:
                return Response(
                    {'success': False, 'error': {'code': 400, 'message': 'No active learning path found.'}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            career = learning_path.career
        else:
            from apps.careers.models import Career
            career = get_object_or_404(Career, id=career_id, is_active=True)

        # Calculate metrics
        from apps.courses.models import Enrollment, LessonProgress
        from apps.matching.models import Match
        from apps.sessions.models import Session

        courses_qs = Enrollment.objects.filter(student=student, course__career=career)
        courses_completed = courses_qs.filter(completed_at__isnull=False).count()
        courses_in_progress = courses_qs.filter(completed_at__isnull=True).count()

        lessons_completed = LessonProgress.objects.filter(
            enrollment__student=student, enrollment__course__career=career, completed_at__isnull=False
        ).count()

        total_lesson_time = LessonProgress.objects.filter(
            enrollment__student=student, enrollment__course__career=career, completed_at__isnull=False
        ).aggregate(total=models.Sum('lesson__duration_minutes'))['total'] or 0

        sessions_completed = Session.objects.filter(
            student=student, status=Session.Status.COMPLETED
        ).count()

        total_session_minutes = Session.objects.filter(
            student=student, status=Session.Status.COMPLETED
        ).aggregate(total=models.Sum('duration_minutes'))['total'] or 0

        latest_assessments = SkillAssessment.objects.filter(
            student=student, career_skill__career=career
        ).order_by('career_skill', '-assessed_at').distinct('career_skill')

        skills_assessed = latest_assessments.exclude(assessed_level__isnull=True).count()
        avg_skill = latest_assessments.exclude(assessed_level__isnull=True).aggregate(
            avg=Avg('assessed_level')
        )['avg'] or 0

        milestones_achieved = Milestone.objects.filter(
            student=student, career=career
        ).count()

        learning_path_progress = 0
        if hasattr(student, 'learning_path') and student.learning_path.career == career:
            learning_path_progress = student.learning_path.get_progress_percent()

        # Create or update snapshot
        snapshot, created = ProgressSnapshot.objects.update_or_create(
            student=student,
            career=career,
            snapshot_date=timezone.now().date(),
            defaults={
                'courses_completed': courses_completed,
                'courses_in_progress': courses_in_progress,
                'lessons_completed': lessons_completed,
                'total_lesson_time_minutes': total_lesson_time,
                'sessions_completed': sessions_completed,
                'total_session_minutes': total_session_minutes,
                'skills_assessed': skills_assessed,
                'average_skill_level': round(avg_skill, 2),
                'milestones_achieved': milestones_achieved,
                'learning_path_progress': learning_path_progress,
            }
        )

        serializer = ProgressSnapshotSerializer(snapshot)
        return Response(
            {'success': True, 'message': 'Snapshot generated', 'data': serializer.data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )