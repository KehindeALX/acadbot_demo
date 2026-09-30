"""
Serializers for the Courses app.
"""
from rest_framework import serializers
from .models import Course, Lesson, Enrollment, LessonProgress, Certificate
from apps.careers.serializers import CareerSerializer
from apps.payments.services import has_active_access, is_lesson_locked


class LessonSerializer(serializers.ModelSerializer):

    """Serializer for lessons (without quiz answer for students)."""

    has_quiz = serializers.BooleanField(read_only=True)
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id', 'title', 'content_html', 'order', 'duration_minutes',
            'has_quiz', 'quiz_question', 'quiz_options', 'is_locked',
        ]

    def get_is_locked(self, obj):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return False
        return is_lesson_locked(obj) and not has_active_access(request.user)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('is_locked'):
            data['content_html'] = ''
            data['has_quiz'] = False
            data['quiz_question'] = ''
            data['quiz_options'] = []
        return data


class LessonDetailSerializer(LessonSerializer):

    """Detailed serializer for lesson. The quiz answer key is never exposed here."""


class CourseSerializer(serializers.ModelSerializer):

    """Serializer for courses."""

    career = CareerSerializer(read_only=True)
    lessons_count = serializers.IntegerField(read_only=True)
    total_duration_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'career', 'title', 'description', 'module_number',
            'duration_minutes', 'order', 'is_published', 'content_reviewed', 'thumbnail',
            'lessons_count', 'total_duration_minutes', 'created_at', 'updated_at',
        ]


class CourseDetailSerializer(CourseSerializer):

    """Detailed serializer for course with lessons."""

    lessons = LessonSerializer(many=True, read_only=True)

    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ['lessons']


class EnrollmentSerializer(serializers.ModelSerializer):

    """Serializer for enrollments."""

    course = CourseSerializer(read_only=True)
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.filter(is_published=True),
        source='course',
        write_only=True,
    )
    progress_percent = serializers.IntegerField(read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            'id', 'course', 'course_id', 'status', 'enrolled_at',
            'started_at', 'completed_at', 'progress_percent', 'last_accessed_at',
        ]
        read_only_fields = ['id', 'enrolled_at', 'started_at', 'completed_at', 'progress_percent', 'last_accessed_at']


class EnrollmentDetailSerializer(EnrollmentSerializer):

    """Detailed serializer for enrollment with lesson progress."""

    lesson_progress = serializers.SerializerMethodField()

    class Meta(EnrollmentSerializer.Meta):
        fields = EnrollmentSerializer.Meta.fields + ['lesson_progress']

    def get_lesson_progress(self, obj):
        progress = obj.lesson_progress.select_related('lesson').all()
        return LessonProgressSerializer(progress, many=True).data


class LessonProgressSerializer(serializers.ModelSerializer):

    """Serializer for lesson progress."""

    lesson = LessonSerializer(read_only=True)
    lesson_id = serializers.PrimaryKeyRelatedField(
        queryset=Lesson.objects.filter(is_published=True),
        source='lesson',
        write_only=True,
    )

    class Meta:
        model = LessonProgress
        fields = [
            'id', 'lesson', 'lesson_id', 'completed_at',
            'quiz_answered', 'quiz_correct', 'time_spent_minutes',
        ]
        read_only_fields = ['id', 'completed_at', 'quiz_correct']


class QuizSubmissionSerializer(serializers.Serializer):

    """Serializer for quiz submission."""

    answer_index = serializers.IntegerField(min_value=0)

    def validate_answer_index(self, value):
        lesson = self.context.get('lesson')
        if lesson and lesson.quiz_options:
            if value >= len(lesson.quiz_options):
                raise serializers.ValidationError('Invalid answer index.')
        return value


class EnrollSerializer(serializers.Serializer):

    """Serializer for course enrollment."""

    course_id = serializers.IntegerField()

    def validate_course_id(self, value):
        try:
            course = Course.objects.get(id=value, is_published=True)
        except Course.DoesNotExist:
            raise serializers.ValidationError('Course not found or not published.')
        return value


class CertificateSerializer(serializers.ModelSerializer):

    course_title = serializers.CharField(source='course.title', read_only=True)
    career_name = serializers.CharField(source='course.career.name', read_only=True)
    holder_name = serializers.CharField(read_only=True)
    issued_at = serializers.DateTimeField(read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'id', 'code', 'course', 'course_title', 'career_name',
            'holder_name', 'score', 'issued_at', 'pdf_url',
        ]

    def get_pdf_url(self, obj):
        request = self.context.get('request')
        path = f'/api/certificates/{obj.code}/pdf/'
        if request is not None:
            return request.build_absolute_uri(path)
        return path


class CertificateVerifySerializer(serializers.ModelSerializer):

    holder_name = serializers.CharField(read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    issued_at = serializers.SerializerMethodField()
    valid = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = ['holder_name', 'course_title', 'issued_at', 'valid']

    def get_issued_at(self, obj):
        return obj.issued_at.date()

    def get_valid(self, obj):
        return True