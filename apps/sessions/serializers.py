"""
Serializers for the Sessions app.
"""
from rest_framework import serializers
from .models import Session, SessionRecurrence, Availability, SessionFeedback
from apps.accounts.serializers import StudentListSerializer, MentorListSerializer
from apps.matching.serializers import MatchSerializer


class SessionSerializer(serializers.ModelSerializer):
    """Serializer for sessions."""

    student = StudentListSerializer(read_only=True)
    mentor = MentorListSerializer(read_only=True)
    match = MatchSerializer(read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    mentor_email = serializers.EmailField(source='mentor.email', read_only=True)
    mentor_name = serializers.CharField(source='mentor.get_full_name', read_only=True)
    is_upcoming = serializers.SerializerMethodField()
    is_past = serializers.SerializerMethodField()
    can_be_cancelled = serializers.SerializerMethodField()
    can_be_rescheduled = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id', 'match',
            'student', 'student_email', 'student_name',
            'mentor', 'mentor_email', 'mentor_name',
            'scheduled_at', 'duration_minutes', 'status',
            'meeting_link', 'meeting_id',
            'notes', 'student_notes', 'mentor_notes',
            'feedback_student', 'feedback_mentor',
            'rating_student', 'rating_mentor',
            'created_at', 'updated_at',
            'started_at', 'completed_at', 'cancelled_at',
            'is_upcoming', 'is_past', 'can_be_cancelled', 'can_be_rescheduled',
        ]
        read_only_fields = [
            'id', 'student', 'mentor', 'match',
            'created_at', 'updated_at',
            'started_at', 'completed_at', 'cancelled_at',
            'is_upcoming', 'is_past', 'can_be_cancelled', 'can_be_rescheduled',
        ]

    def get_is_upcoming(self, obj):
        return obj.is_upcoming()

    def get_is_past(self, obj):
        return obj.is_past()

    def get_can_be_cancelled(self, obj):
        return obj.can_be_cancelled()

    def get_can_be_rescheduled(self, obj):
        return obj.can_be_rescheduled()


class SessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating sessions."""

    match_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Session
        fields = [
            'match_id', 'scheduled_at', 'duration_minutes',
            'meeting_link', 'meeting_id', 'notes',
        ]

    def validate_match_id(self, value):
        from apps.matching.models import Match
        try:
            match = Match.objects.select_related('student', 'mentor').get(id=value)
        except Match.DoesNotExist:
            raise serializers.ValidationError('Match not found.')

        if match.status != Match.Status.ACTIVE:
            raise serializers.ValidationError('Match must be active to schedule sessions.')

        request = self.context.get('request')
        if request and request.user != match.student and request.user != match.mentor:
            raise serializers.ValidationError('Not authorized to schedule sessions for this match.')

        return value

    def validate_scheduled_at(self, value):
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError('Session cannot be scheduled in the past.')
        return value

    def validate_duration_minutes(self, value):
        if value < 15 or value > 240:
            raise serializers.ValidationError('Duration must be between 15 and 240 minutes.')
        return value

    def create(self, validated_data):
        match_id = validated_data.pop('match_id')
        from apps.matching.models import Match
        match = Match.objects.select_related('student', 'mentor').get(id=match_id)

        session = Session.objects.create(
            match=match,
            student=match.student,
            mentor=match.mentor,
            **validated_data,
        )
        return session


class SessionUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating sessions (reschedule, cancel)."""

    class Meta:
        model = Session
        fields = [
            'scheduled_at', 'duration_minutes',
            'meeting_link', 'meeting_id',
            'notes', 'student_notes', 'mentor_notes',
            'status',
        ]

    def validate_scheduled_at(self, value):
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError('Session cannot be scheduled in the past.')

        instance = self.instance
        if instance and instance.status in [Session.Status.COMPLETED, Session.Status.CANCELLED, Session.Status.NO_SHOW]:
            raise serializers.ValidationError('Cannot reschedule a completed or cancelled session.')

        return value

    def validate_status(self, value):
        instance = self.instance
        if instance and instance.status in [Session.Status.COMPLETED, Session.Status.CANCELLED, Session.Status.NO_SHOW]:
            if value != instance.status:
                raise serializers.ValidationError('Cannot change status of completed or cancelled session.')
        return value


class SessionCompleteSerializer(serializers.Serializer):
    """Serializer for completing a session with feedback."""

    feedback = serializers.CharField(required=False, allow_blank=True)
    rating = serializers.ChoiceField(choices=[1, 2, 3, 4, 5], required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class SessionFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for detailed session feedback."""

    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = SessionFeedback
        fields = [
            'id', 'session', 'author', 'author_name',
            'feedback_type', 'rating',
            'strengths', 'areas_for_improvement', 'additional_comments',
            'is_shared', 'created_at',
        ]
        read_only_fields = ['id', 'author', 'created_at']


class SessionFeedbackCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating session feedback."""

    class Meta:
        model = SessionFeedback
        fields = [
            'feedback_type', 'rating',
            'strengths', 'areas_for_improvement', 'additional_comments',
            'is_shared',
        ]

    def validate_feedback_type(self, value):
        request = self.context.get('request')
        if request:
            user = request.user
            if value == Session.FeedbackType.STUDENT and not user.is_student:
                raise serializers.ValidationError('Only students can give student feedback.')
            if value == Session.FeedbackType.MENTOR and not user.is_mentor:
                raise serializers.ValidationError('Only mentors can give mentor feedback.')
        return value

    def create(self, validated_data):
        session = self.context['session']
        author = self.context['request'].user
        feedback, _ = SessionFeedback.objects.update_or_create(
            session=session,
            author=author,
            feedback_type=validated_data['feedback_type'],
            defaults=validated_data,
        )
        return feedback


class SessionRecurrenceSerializer(serializers.ModelSerializer):
    """Serializer for session recurrences."""

    class Meta:
        model = SessionRecurrence
        fields = [
            'id', 'session', 'frequency', 'end_date',
            'occurrences_count', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'occurrences_count', 'created_at', 'updated_at']


class AvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for mentor availability."""

    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = Availability
        fields = [
            'id', 'mentor', 'day_of_week', 'day_of_week_display',
            'start_time', 'end_time', 'timezone',
            'is_recurring', 'specific_date', 'is_available',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'mentor', 'created_at', 'updated_at']


class AvailabilityCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating mentor availability."""

    class Meta:
        model = Availability
        fields = [
            'day_of_week', 'start_time', 'end_time', 'timezone',
            'is_recurring', 'specific_date', 'is_available',
        ]

    def validate(self, attrs):
        if attrs['start_time'] >= attrs['end_time']:
            raise serializers.ValidationError('Start time must be before end time.')

        if not attrs.get('is_recurring') and not attrs.get('specific_date'):
            raise serializers.ValidationError('Specific date required for non-recurring availability.')

        return attrs

    def create(self, validated_data):
        mentor = self.context['request'].user
        return Availability.objects.create(mentor=mentor, **validated_data)


class MentorAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for listing mentor availability (public view)."""

    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = Availability
        fields = [
            'id', 'day_of_week', 'day_of_week_display',
            'start_time', 'end_time', 'timezone',
            'is_recurring', 'specific_date',
        ]