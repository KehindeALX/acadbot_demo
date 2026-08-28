"""
Serializers for the Matching app.
"""
from rest_framework import serializers
from .models import MatchRequest, Match, MentorMatch
from apps.careers.serializers import CareerSerializer
from apps.accounts.serializers import MentorListSerializer


def get_active_careers():
    from apps.careers.models import Career
    return Career.objects.filter(is_active=True)


class MatchRequestSerializer(serializers.ModelSerializer):
    """Serializer for match requests."""

    preferred_careers = CareerSerializer(many=True, read_only=True)
    preferred_career_ids = serializers.PrimaryKeyRelatedField(
        queryset=get_active_careers(),
        source='preferred_careers',
        write_only=True,
        many=True,
        required=False,
    )
    student_email = serializers.EmailField(source='student.email', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)

    class Meta:
        model = MatchRequest
        fields = [
            'id', 'student_email', 'student_name',
            'preferred_careers', 'preferred_career_ids',
            'preferred_schedule', 'status', 'notes',
            'created_at', 'updated_at', 'matched_at',
        ]
        read_only_fields = ['id', 'student', 'status', 'created_at', 'updated_at', 'matched_at']


class MatchRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating match requests."""

    preferred_career_ids = serializers.PrimaryKeyRelatedField(
        queryset=get_active_careers(),
        source='preferred_careers',
        write_only=True,
        many=True,
        required=False,
    )

    class Meta:
        model = MatchRequest
        fields = ['preferred_career_ids', 'preferred_schedule', 'notes']

    def create(self, validated_data):
        preferred_careers = validated_data.pop('preferred_careers', [])
        match_request = MatchRequest.objects.create(
            student=self.context['request'].user,
            **validated_data,
        )
        if preferred_careers:
            match_request.preferred_careers.set(preferred_careers)
        return match_request


class MentorMatchSerializer(serializers.ModelSerializer):
    """Serializer for mentor match suggestions."""

    mentor = MentorListSerializer(read_only=True)
    mentor_id = serializers.IntegerField(source='mentor.id', read_only=True)

    class Meta:
        model = MentorMatch
        fields = [
            'id', 'mentor_id', 'mentor', 'compatibility_score', 'is_accepted', 'created_at',
        ]


class MatchSerializer(serializers.ModelSerializer):
    """Serializer for matches."""

    student_email = serializers.EmailField(source='student.email', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    mentor_email = serializers.EmailField(source='mentor.email', read_only=True)
    mentor_name = serializers.CharField(source='mentor.get_full_name', read_only=True)
    match_request = MatchRequestSerializer(read_only=True)

    class Meta:
        model = Match
        fields = [
            'id', 'match_request',
            'student_email', 'student_name',
            'mentor_email', 'mentor_name',
            'status', 'compatibility_score',
            'created_at', 'updated_at', 'accepted_at', 'completed_at',
        ]
        read_only_fields = fields


class MatchActionSerializer(serializers.Serializer):
    """Serializer for match actions (accept/decline)."""

    pass