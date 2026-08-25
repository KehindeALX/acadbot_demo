"""
Serializers for the Dashboard app.
"""
from rest_framework import serializers
from apps.accounts.serializers import StudentListSerializer, MentorListSerializer
from apps.careers.serializers import CareerSerializer, CourseSerializer, CareerSkillSerializer, RoadmapStageSerializer
from apps.matching.serializers import MatchRequestSerializer, MatchSerializer
from apps.sessions.serializers import SessionSerializer, AvailabilitySerializer
from apps.accounts.models import MentorProfile
from apps.courses.models import Enrollment
from apps.careers.models import Career


class StudentDashboardSerializer(serializers.Serializer):
    """Serializer for student dashboard overview."""

    learning_path = serializers.SerializerMethodField()
    active_match = MatchSerializer(allow_null=True)
    upcoming_sessions = SessionSerializer(many=True)
    recent_sessions = SessionSerializer(many=True)
    in_progress_courses = EnrollmentSerializer(many=True)
    completed_courses = EnrollmentSerializer(many=True)
    assessed_skills_count = serializers.IntegerField()
    average_skill_level = serializers.DecimalField(max_digits=3, decimal_places=2)
    recent_milestones = serializers.ListField(child=serializers.DictField())
    match_request = MatchRequestSerializer(allow_null=True)
    streak_days = serializers.IntegerField()

    def get_learning_path(self, obj):
        from apps.progress.serializers import LearningPathSerializer
        if obj.get('learning_path'):
            return LearningPathSerializer(obj['learning_path']).data
        return None


class EnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for enrollment in dashboard."""

    course = CourseSerializer()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'enrolled_at', 'completed_at', 'progress_percent']

    def get_progress_percent(self, obj):
        from apps.courses.models import LessonProgress
        lessons = obj.course.lessons.count()
        if lessons == 0:
            return 0
        completed = LessonProgress.objects.filter(enrollment=obj, completed_at__isnull=False).count()
        return round((completed / lessons * 100), 1)


class CareerProgressSerializer(serializers.Serializer):
    """Serializer for detailed career progress."""

    career = CareerSerializer()
    course_progress = serializers.ListField(child=serializers.DictField())
    skill_progress = serializers.ListField(child=serializers.DictField())
    roadmap_progress = serializers.ListField(child=serializers.DictField())


class ActivitySerializer(serializers.Serializer):
    """Serializer for activity timeline."""

    type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    date = serializers.DateTimeField()
    status = serializers.CharField()
    metadata = serializers.DictField()


class MentorDashboardSerializer(serializers.Serializer):
    """Serializer for mentor dashboard overview."""

    active_students_count = serializers.IntegerField()
    pending_matches_count = serializers.IntegerField()
    upcoming_sessions = SessionSerializer(many=True)
    monthly_sessions_count = serializers.IntegerField()
    total_sessions_count = serializers.IntegerField()
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    mentor_profile = serializers.SerializerMethodField()

    def get_mentor_profile(self, obj):
        if obj.get('mentor_profile'):
            from apps.accounts.serializers import MentorProfileSerializer
            return MentorProfileSerializer(obj['mentor_profile']).data
        return None


class MentorStudentSerializer(serializers.Serializer):
    """Serializer for mentor's students list."""

    student = StudentListSerializer()
    career = CareerSerializer(allow_null=True)
    total_sessions = serializers.IntegerField()
    last_session = SessionSerializer(allow_null=True)
    match_since = serializers.DateTimeField()


class MentorScheduleSerializer(serializers.Serializer):
    """Serializer for mentor schedule."""

    availabilities = AvailabilitySerializer(many=True)
    upcoming_sessions = SessionSerializer(many=True)


class MentorEarningsSerializer(serializers.Serializer):
    """Serializer for mentor earnings."""

    period = serializers.CharField()
    completed_sessions = serializers.IntegerField()
    total_minutes = serializers.IntegerField()
    total_hours = serializers.DecimalField(max_digits=6, decimal_places=1)
    hourly_rate = serializers.DecimalField(max_digits=8, decimal_places=2)
    estimated_earnings = serializers.DecimalField(max_digits=10, decimal_places=2)


class AdminDashboardSerializer(serializers.Serializer):
    """Serializer for admin dashboard overview."""

    users = serializers.DictField()
    matches = serializers.DictField()
    sessions = serializers.DictField()
    courses = serializers.DictField()
    recent_registrations = StudentListSerializer(many=True)


class CareerDistributionSerializer(serializers.Serializer):
    """Serializer for career distribution."""

    students_by_career = serializers.ListField(child=serializers.DictField())
    mentors_by_career = serializers.ListField(child=serializers.DictField())
    enrollments_by_career = serializers.ListField(child=serializers.DictField())


class CompletionRateSerializer(serializers.Serializer):
    """Serializer for completion rates."""

    career = serializers.CharField()
    career_slug = serializers.CharField()
    total_enrollments = serializers.IntegerField()
    completed_enrollments = serializers.IntegerField()
    completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_days_to_complete = serializers.DecimalField(max_digits=6, decimal_places=1)


class EngagementSerializer(serializers.Serializer):
    """Serializer for engagement metrics."""

    daily_active_users = serializers.ListField(child=serializers.DictField())
    daily_sessions = serializers.ListField(child=serializers.DictField())
    match_conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_sessions_per_match = serializers.DecimalField(max_digits=5, decimal_places=2)