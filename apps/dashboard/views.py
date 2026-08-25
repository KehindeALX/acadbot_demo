"""
Views for the Dashboard app - analytics and reporting.
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict

from apps.accounts.models import User, StudentProfile, MentorProfile
from apps.careers.models import Career, CareerSkill, RoadmapStage
from apps.courses.models import Course, Enrollment, LessonProgress
from apps.matching.models import MatchRequest, Match, MentorMatch
from apps.sessions.models import Session, Availability
from apps.progress.models import SkillAssessment, Milestone, LearningPath, ProgressSnapshot
from apps.core.permissions import IsAdmin, IsMentor, IsStudent


class StudentDashboardViewSet(viewsets.GenericViewSet):
    """Student dashboard - personal analytics and progress."""

    permission_classes = [IsAuthenticated, IsStudent]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get student dashboard overview."""
        student = request.user

        # Learning path
        learning_path = LearningPath.objects.select_related('career', 'current_stage').filter(
            student=student, is_active=True
        ).first()

        # Active match
        active_match = Match.objects.select_related('mentor__mentor_profile').filter(
            student=student, status=Match.Status.ACTIVE
        ).first()

        # Upcoming sessions
        upcoming_sessions = Session.objects.select_related('mentor').filter(
            student=student,
            status__in=[Session.Status.SCHEDULED, Session.Status.RESCHEDULED],
            scheduled_at__gt=timezone.now()
        ).order_by('scheduled_at')[:5]

        # Recent sessions
        recent_sessions = Session.objects.select_related('mentor').filter(
            student=student,
            status=Session.Status.COMPLETED
        ).order_by('-completed_at')[:5]

        # Courses
        enrollments = Enrollment.objects.select_related('course__career').filter(
            student=student
        ).order_by('-enrolled_at')

        in_progress_courses = enrollments.filter(completed_at__isnull=True)[:3]
        completed_courses = enrollments.filter(completed_at__isnull=False)[:3]

        # Skill assessments
        latest_assessments = SkillAssessment.objects.select_related('career_skill__career').filter(
            student=student
        ).order_by('career_skill', '-assessed_at').distinct('career_skill')

        assessed_skills = latest_assessments.exclude(assessed_level__isnull=True).count()
        avg_skill_level = latest_assessments.exclude(assessed_level__isnull=True).aggregate(
            avg=Avg('assessed_level')
        )['avg'] or 0

        # Milestones
        milestones = Milestone.objects.select_related('career').filter(
            student=student
        ).order_by('-achieved_at')[:5]

        # Match request status
        match_request = MatchRequest.objects.filter(
            student=student
        ).order_by('-created_at').first()

        # Calculate streak (consecutive days with activity)
        streak = self._calculate_streak(student)

        data = {
            'learning_path': learning_path,
            'active_match': active_match,
            'upcoming_sessions': upcoming_sessions,
            'recent_sessions': recent_sessions,
            'in_progress_courses': in_progress_courses,
            'completed_courses': completed_courses,
            'assessed_skills_count': assessed_skills,
            'average_skill_level': round(avg_skill_level, 2),
            'recent_milestones': milestones,
            'match_request': match_request,
            'streak_days': streak,
        }

        from .serializers import StudentDashboardSerializer
        serializer = StudentDashboardSerializer(data)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='career-progress')
    def career_progress(self, request):
        """Get detailed career progress."""
        student = request.user
        career_id = request.query_params.get('career_id')

        if career_id:
            from apps.careers.models import Career
            career = get_object_or_404(Career, id=career_id, is_active=True)
        else:
            learning_path = LearningPath.objects.filter(student=student, is_active=True).first()
            if not learning_path:
                return Response(
                    {'success': False, 'error': {'code': 400, 'message': 'No active career found.'}},
                    status=400
                )
            career = learning_path.career

        # Course progress
        courses = Course.objects.filter(career=career, is_published=True).prefetch_related('lessons')
        enrollments = Enrollment.objects.filter(student=student, course__career=career)

        course_progress = []
        for course in courses:
            enrollment = enrollments.filter(course=course).first()
            if enrollment:
                lessons = course.lessons.count()
                completed = LessonProgress.objects.filter(enrollment=enrollment, completed_at__isnull=False).count()
                progress = round((completed / lessons * 100) if lessons > 0 else 0, 1)
            else:
                progress = 0
                lessons = course.lessons.count()
                completed = 0

            course_progress.append({
                'course': course,
                'enrolled': bool(enrollment),
                'completed_lessons': completed,
                'total_lessons': lessons,
                'progress_percent': progress,
            })

        # Skill assessments for this career
        skills = CareerSkill.objects.filter(career=career).order_by('order')
        skill_progress = []
        for skill in skills:
            assessment = SkillAssessment.objects.filter(
                student=student, career_skill=skill
            ).order_by('-assessed_at').first()

            skill_progress.append({
                'skill': skill,
                'self_rated': assessment.self_rated_level if assessment else None,
                'assessed': assessment.assessed_level if assessment else None,
                'last_assessed': assessment.assessed_at if assessment else None,
            })

        # Roadmap progress
        stages = RoadmapStage.objects.filter(career=career).order_by('order')
        roadmap_progress = []
        current_stage = learning_path.current_stage if learning_path else None

        for stage in stages:
            is_completed = current_stage and stage.order < current_stage.order
            is_current = current_stage and stage.id == current_stage.id

            roadmap_progress.append({
                'stage': stage,
                'is_completed': is_completed,
                'is_current': is_current,
            })

        from .serializers import CareerProgressSerializer
        serializer = CareerProgressSerializer({
            'career': career,
            'course_progress': course_progress,
            'skill_progress': skill_progress,
            'roadmap_progress': roadmap_progress,
        })
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='activity')
    def activity(self, request):
        """Get student activity timeline."""
        student = request.user
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        activities = []

        # Session activity
        sessions = Session.objects.select_related('mentor').filter(
            student=student,
            created_at__gte=start_date
        ).order_by('-created_at')

        for session in sessions:
            activities.append({
                'type': 'session',
                'title': f'Session with {session.mentor.get_full_name()}',
                'description': session.notes or '',
                'date': session.scheduled_at,
                'status': session.status,
                'metadata': {'session_id': session.id},
            })

        # Milestone activity
        milestones = Milestone.objects.filter(
            student=student,
            achieved_at__gte=start_date
        ).order_by('-achieved_at')

        for milestone in milestones:
            activities.append({
                'type': 'milestone',
                'title': milestone.title,
                'description': milestone.description,
                'date': milestone.achieved_at,
                'status': milestone.milestone_type,
                'metadata': {'milestone_id': milestone.id},
            })

        # Course completion
        enrollments = Enrollment.objects.select_related('course').filter(
            student=student,
            completed_at__gte=start_date
        ).order_by('-completed_at')

        for enrollment in enrollments:
            activities.append({
                'type': 'course_completion',
                'title': f'Completed {enrollment.course.title}',
                'description': enrollment.course.description[:200],
                'date': enrollment.completed_at,
                'status': 'completed',
                'metadata': {'course_id': enrollment.course.id},
            })

        # Sort by date
        activities.sort(key=lambda x: x['date'], reverse=True)

        from .serializers import ActivitySerializer
        serializer = ActivitySerializer(activities, many=True)
        return Response({'success': True, 'data': serializer.data})

    def _calculate_streak(self, student):
        """Calculate consecutive days with learning activity."""
        # This is a simplified version - in production, you'd track daily activity
        return 0


class MentorDashboardViewSet(viewsets.GenericViewSet):
    """Mentor dashboard - student management and earnings."""

    permission_classes = [IsAuthenticated, IsMentor]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get mentor dashboard overview."""
        mentor = request.user

        # Active students (matches)
        active_matches = Match.objects.select_related('student__student_profile').filter(
            mentor=mentor, status=Match.Status.ACTIVE
        )

        # Pending match requests
        pending_matches = Match.objects.select_related('student__student_profile').filter(
            mentor=mentor, status=Match.Status.PENDING
        )

        # Upcoming sessions
        upcoming_sessions = Session.objects.select_related('student').filter(
            mentor=mentor,
            status__in=[Session.Status.SCHEDULED, Session.Status.RESCHEDULED],
            scheduled_at__gt=timezone.now()
        ).order_by('scheduled_at')[:10]

        # Past sessions this month
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_sessions = Session.objects.filter(
            mentor=mentor,
            status=Session.Status.COMPLETED,
            completed_at__gte=month_start
        ).count()

        # Earnings (simplified - would integrate with payment system)
        total_sessions = Session.objects.filter(
            mentor=mentor, status=Session.Status.COMPLETED
        ).count()

        # Average rating
        avg_rating = Session.objects.filter(
            mentor=mentor, status=Session.Status.COMPLETED, rating_mentor__isnull=False
        ).aggregate(avg=Avg('rating_mentor'))['avg'] or 0

        # Profile stats
        mentor_profile = mentor.mentor_profile if hasattr(mentor, 'mentor_profile') else None

        data = {
            'active_students_count': active_matches.count(),
            'pending_matches_count': pending_matches.count(),
            'upcoming_sessions': upcoming_sessions,
            'monthly_sessions_count': monthly_sessions,
            'total_sessions_count': total_sessions,
            'average_rating': round(avg_rating, 2),
            'mentor_profile': mentor_profile,
        }

        from .serializers import MentorDashboardSerializer
        serializer = MentorDashboardSerializer(data)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='students')
    def students(self, request):
        """Get mentor's students with progress."""
        mentor = request.user

        active_matches = Match.objects.select_related(
            'student__student_profile', 'student__student_profile__career'
        ).filter(
            mentor=mentor, status=Match.Status.ACTIVE
        )

        students_data = []
        for match in active_matches:
            student = match.student
            # Get student's progress for this mentor's expertise
            career = student.student_profile.career if hasattr(student, 'student_profile') else None

            # Sessions with this student
            sessions = Session.objects.filter(
                student=student, mentor=mentor, status=Session.Status.COMPLETED
            ).count()

            # Last session
            last_session = Session.objects.filter(
                student=student, mentor=mentor
            ).order_by('-scheduled_at').first()

            students_data.append({
                'student': student,
                'career': career,
                'total_sessions': sessions,
                'last_session': last_session,
                'match_since': match.accepted_at,
            })

        from .serializers import MentorStudentSerializer
        serializer = MentorStudentSerializer(students_data, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='schedule')
    def schedule(self, request):
        """Get mentor's weekly schedule."""
        mentor = request.user

        # Availability
        availabilities = Availability.objects.filter(
            mentor=mentor, is_available=True
        ).order_by('day_of_week', 'start_time')

        # Upcoming sessions
        upcoming_sessions = Session.objects.select_related('student').filter(
            mentor=mentor,
            status__in=[Session.Status.SCHEDULED, Session.Status.RESCHEDULED],
            scheduled_at__gt=timezone.now()
        ).order_by('scheduled_at')

        from .serializers import MentorScheduleSerializer
        serializer = MentorScheduleSerializer({
            'availabilities': availabilities,
            'upcoming_sessions': upcoming_sessions,
        })
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='earnings')
    def earnings(self, request):
        """Get mentor earnings report."""
        mentor = request.user

        # Time range
        period = request.query_params.get('period', 'month')
        if period == 'week':
            start_date = timezone.now() - timedelta(weeks=1)
        elif period == 'month':
            start_date = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'year':
            start_date = timezone.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = None

        sessions_qs = Session.objects.filter(mentor=mentor, status=Session.Status.COMPLETED)
        if start_date:
            sessions_qs = sessions_qs.filter(completed_at__gte=start_date)

        completed_sessions = sessions_qs.count()
        total_minutes = sessions_qs.aggregate(total=Sum('duration_minutes'))['total'] or 0

        # This would integrate with a payment system
        # For now, just return session stats
        data = {
            'period': period,
            'completed_sessions': completed_sessions,
            'total_minutes': total_minutes,
            'total_hours': round(total_minutes / 60, 1),
            'hourly_rate': mentor.mentor_profile.hourly_rate if hasattr(mentor, 'mentor_profile') else 0,
            'estimated_earnings': 0,  # Would calculate from payment records
        }

        from .serializers import MentorEarningsSerializer
        serializer = MentorEarningsSerializer(data)
        return Response({'success': True, 'data': serializer.data})


class AdminDashboardViewSet(viewsets.GenericViewSet):
    """Admin dashboard - platform analytics."""

    permission_classes = [IsAuthenticated, IsAdmin]

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get admin dashboard overview."""
        # User stats
        total_users = User.objects.count()
        total_students = User.objects.filter(role=User.Role.STUDENT).count()
        total_mentors = User.objects.filter(role=User.Role.MENTOR).count()
        total_admins = User.objects.filter(role=User.Role.ADMIN).count()

        # Verified mentors
        verified_mentors = MentorProfile.objects.filter(is_verified=True).count()

        # Active users (logged in last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        active_users = User.objects.filter(last_login__gte=thirty_days_ago).count()

        # Match stats
        total_match_requests = MatchRequest.objects.count()
        active_matches = Match.objects.filter(status=Match.Status.ACTIVE).count()
        completed_matches = Match.objects.filter(status=Match.Status.COMPLETED).count()

        # Session stats
        total_sessions = Session.objects.count()
        completed_sessions = Session.objects.filter(status=Session.Status.COMPLETED).count()
        scheduled_sessions = Session.objects.filter(status=Session.Status.SCHEDULED).count()

        # Course stats
        total_courses = Course.objects.filter(is_published=True).count()
        total_enrollments = Enrollment.objects.count()
        completed_enrollments = Enrollment.objects.filter(completed_at__isnull=False).count()

        # Recent activity
        recent_registrations = User.objects.filter(
            date_joined__gte=thirty_days_ago
        ).order_by('-date_joined')[:10]

        data = {
            'users': {
                'total': total_users,
                'students': total_students,
                'mentors': total_mentors,
                'admins': total_admins,
                'verified_mentors': verified_mentors,
                'active_last_30_days': active_users,
            },
            'matches': {
                'total_requests': total_match_requests,
                'active': active_matches,
                'completed': completed_matches,
            },
            'sessions': {
                'total': total_sessions,
                'completed': completed_sessions,
                'scheduled': scheduled_sessions,
            },
            'courses': {
                'total_published': total_courses,
                'total_enrollments': total_enrollments,
                'completed_enrollments': completed_enrollments,
            },
            'recent_registrations': recent_registrations,
        }

        from .serializers import AdminDashboardSerializer
        serializer = AdminDashboardSerializer(data)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='career-distribution')
    def career_distribution(self, request):
        """Get career popularity distribution."""
        # Students by career
        student_careers = StudentProfile.objects.values('career__name', 'career__slug').annotate(
            count=Count('id')
        ).order_by('-count')

        # Mentors by expertise
        mentor_careers = MentorProfile.objects.prefetch_related('expertise_careers').all()
        mentor_distribution = defaultdict(int)
        for mentor in mentor_careers:
            for career in mentor.expertise_careers.all():
                mentor_distribution[career.name] += 1

        mentor_career_list = [
            {'career__name': name, 'count': count}
            for name, count in sorted(mentor_distribution.items(), key=lambda x: x[1], reverse=True)
        ]

        # Course enrollments by career
        course_enrollments = Enrollment.objects.values('course__career__name', 'course__career__slug').annotate(
            count=Count('id')
        ).order_by('-count')

        data = {
            'students_by_career': list(student_careers),
            'mentors_by_career': mentor_career_list,
            'enrollments_by_career': list(course_enrollments),
        }

        from .serializers import CareerDistributionSerializer
        serializer = CareerDistributionSerializer(data)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='completion-rates')
    def completion_rates(self, request):
        """Get course completion rates by career."""
        careers = Career.objects.filter(is_active=True)
        results = []

        for career in careers:
            courses = Course.objects.filter(career=career, is_published=True)
            if not courses.exists():
                continue

            enrollments = Enrollment.objects.filter(course__in=courses)
            total = enrollments.count()
            completed = enrollments.filter(completed_at__isnull=False).count()
            rate = round((completed / total * 100) if total > 0 else 0, 1)

            # Average time to completion
            completed_enrollments = enrollments.filter(completed_at__isnull=False)
            avg_days = completed_enrollments.aggregate(
                avg=Avg((F('completed_at') - F('enrolled_at')).total_seconds() / 86400)
            )['avg'] or 0

            results.append({
                'career': career.name,
                'career_slug': career.slug,
                'total_enrollments': total,
                'completed_enrollments': completed,
                'completion_rate': rate,
                'average_days_to_complete': round(avg_days, 1),
            })

        # Sort by completion rate
        results.sort(key=lambda x: x['completion_rate'], reverse=True)

        from .serializers import CompletionRateSerializer
        serializer = CompletionRateSerializer(results, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=False, methods=['get'], url_path='engagement')
    def engagement(self, request):
        """Get platform engagement metrics."""
        # Daily active users (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)

        daily_active = User.objects.filter(
            last_login__gte=thirty_days_ago
        ).extra(
            select={'date': 'DATE(last_login)'}
        ).values('date').annotate(
            count=Count('id', distinct=True)
        ).order_by('date')

        # Session volume (last 30 days)
        daily_sessions = Session.objects.filter(
            scheduled_at__gte=thirty_days_ago
        ).extra(
            select={'date': 'DATE(scheduled_at)'}
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')

        # Match conversion rate
        total_requests = MatchRequest.objects.count()
        matched_requests = MatchRequest.objects.filter(status=MatchRequest.Status.MATCHED).count()
        conversion_rate = round((matched_requests / total_requests * 100) if total_requests > 0 else 0, 1)

        # Average sessions per match
        active_matches = Match.objects.filter(status=Match.Status.ACTIVE)
        avg_sessions = active_matches.annotate(
            session_count=Count('sessions')
        ).aggregate(avg=Avg('session_count'))['avg'] or 0

        data = {
            'daily_active_users': list(daily_active),
            'daily_sessions': list(daily_sessions),
            'match_conversion_rate': conversion_rate,
            'average_sessions_per_match': round(avg_sessions, 1),
        }

        from .serializers import EngagementSerializer
        serializer = EngagementSerializer(data)
        return Response({'success': True, 'data': serializer.data})


from django.shortcuts import get_object_or_404
from django.db.models import F