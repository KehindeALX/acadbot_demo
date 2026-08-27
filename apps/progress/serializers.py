"""
Serializers for the Progress app.
"""
from rest_framework import serializers
from .models import SkillAssessment, Milestone, LearningPath, ProgressSnapshot
from apps.careers.serializers import CareerSkillSerializer, CareerSerializer, RoadmapStageSerializer


def get_active_career_skills():
    from apps.careers.models import CareerSkill
    return CareerSkill.objects.filter(career__is_active=True)


def get_active_careers():
    from apps.careers.models import Career
    return Career.objects.filter(is_active=True)


def get_active_roadmap_stages():
    from apps.careers.models import RoadmapStage
    return RoadmapStage.objects.filter(career__is_active=True)


class SkillAssessmentSerializer(serializers.ModelSerializer):
    """Serializer for skill assessments."""

    career_skill = CareerSkillSerializer(read_only=True)
    career_skill_id = serializers.PrimaryKeyRelatedField(
        queryset=get_active_career_skills,
        source='career_skill',
        write_only=True,
        required=True,
    )
    assessed_by_name = serializers.CharField(source='assessed_by.get_full_name', read_only=True)
    level_display = serializers.CharField(read_only=True)
    is_assessed = serializers.BooleanField(read_only=True)

    class Meta:
        model = SkillAssessment
        fields = [
            'id', 'career_skill', 'career_skill_id',
            'self_rated_level', 'assessed_level',
            'assessment_type', 'assessed_by', 'assessed_by_name',
            'evidence', 'notes',
            'assessed_at', 'updated_at',
            'level_display', 'is_assessed',
        ]
        read_only_fields = [
            'id', 'student', 'assessed_by', 'assessed_at', 'updated_at',
            'level_display', 'is_assessed',
        ]

    def validate(self, attrs):
        assessment_type = attrs.get('assessment_type', SkillAssessment.AssessmentType.SELF)
        if assessment_type == SkillAssessment.AssessmentType.SELF:
            if 'self_rated_level' not in attrs or attrs['self_rated_level'] is None:
                raise serializers.ValidationError('self_rated_level is required for self assessments.')
        elif assessment_type in [SkillAssessment.AssessmentType.MENTOR, SkillAssessment.AssessmentType.PEER]:
            if 'assessed_level' not in attrs or attrs['assessed_level'] is None:
                raise serializers.ValidationError('assessed_level is required for mentor/peer assessments.')
        return attrs


class SkillAssessmentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating skill assessments."""

    career_skill_id = serializers.PrimaryKeyRelatedField(
        queryset=get_active_career_skills,
        source='career_skill',
        write_only=True,
        required=True,
    )

    class Meta:
        model = SkillAssessment
        fields = [
            'career_skill_id', 'self_rated_level', 'assessed_level',
            'assessment_type', 'evidence', 'notes',
        ]

    def create(self, validated_data):
        student = self.context['request'].user
        assessment_type = validated_data.get('assessment_type', SkillAssessment.AssessmentType.SELF)

        if assessment_type in [SkillAssessment.AssessmentType.MENTOR, SkillAssessment.AssessmentType.PEER]:
            validated_data['assessed_by'] = student
        else:
            validated_data['assessed_by'] = None

        assessment, created = SkillAssessment.objects.update_or_create(
            student=student,
            career_skill=validated_data['career_skill'],
            assessment_type=assessment_type,
            defaults=validated_data,
        )
        return assessment


class MilestoneSerializer(serializers.ModelSerializer):
    """Serializer for milestones."""

    career = CareerSerializer(read_only=True)
    career_id = serializers.PrimaryKeyRelatedField(
        queryset=get_active_careers,
        source='career',
        write_only=True,
        required=False,
        allow_null=True,
    )
    milestone_type_display = serializers.CharField(source='get_milestone_type_display', read_only=True)

    class Meta:
        model = Milestone
        fields = [
            'id', 'career', 'career_id',
            'title', 'description', 'milestone_type', 'milestone_type_display',
            'achieved_at', 'metadata', 'is_public',
            'created_at',
        ]
        read_only_fields = ['id', 'student', 'created_at', 'milestone_type_display']


class MilestoneCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating milestones."""

    career_id = serializers.PrimaryKeyRelatedField(
        queryset=get_active_careers,
        source='career',
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Milestone
        fields = [
            'career_id', 'title', 'description',
            'milestone_type', 'achieved_at', 'metadata', 'is_public',
        ]

    def create(self, validated_data):
        student = self.context['request'].user
        return Milestone.objects.create(student=student, **validated_data)


class LearningPathSerializer(serializers.ModelSerializer):
    """Serializer for learning paths."""

    career = CareerSerializer(read_only=True)
    career_id = serializers.PrimaryKeyRelatedField(
        queryset=get_active_careers,
        source='career',
        write_only=True,
        required=True,
    )
    current_stage = RoadmapStageSerializer(read_only=True)
    current_stage_id = serializers.PrimaryKeyRelatedField(
        queryset=get_active_roadmap_stages,
        source='current_stage',
        write_only=True,
        required=False,
        allow_null=True,
    )
    progress_percent = serializers.SerializerMethodField()
    completed_stages_count = serializers.IntegerField(read_only=True)
    total_stages_count = serializers.IntegerField(read_only=True)
    next_stage = serializers.SerializerMethodField()

    class Meta:
        model = LearningPath
        fields = [
            'id', 'career', 'career_id',
            'current_stage', 'current_stage_id',
            'started_at', 'target_completion_date',
            'is_active', 'completed_at',
            'progress_percent', 'completed_stages_count', 'total_stages_count',
            'next_stage',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'student', 'started_at', 'completed_at',
            'progress_percent', 'completed_stages_count', 'total_stages_count',
            'next_stage', 'created_at', 'updated_at',
        ]

    def get_progress_percent(self, obj):
        return obj.get_progress_percent()

    def get_next_stage(self, obj):
        next_stage = obj.get_next_stage()
        if next_stage:
            return RoadmapStageSerializer(next_stage).data
        return None


class LearningPathUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating learning path (advancing stages)."""

    current_stage_id = serializers.PrimaryKeyRelatedField(
        queryset=get_active_roadmap_stages,
        source='current_stage',
        write_only=True,
        required=False,
        allow_null=True,
    )
    target_completion_date = serializers.DateField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = LearningPath
        fields = ['current_stage_id', 'target_completion_date', 'is_active']

    def update(self, instance, validated_data):
        new_stage = validated_data.get('current_stage')
        if new_stage and new_stage != instance.current_stage:
            instance.advance_stage(new_stage)
        else:
            instance = super().update(instance, validated_data)
        return instance


class ProgressSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for progress snapshots."""

    career = CareerSerializer(read_only=True)

    class Meta:
        model = ProgressSnapshot
        fields = [
            'id', 'career',
            'courses_completed', 'courses_in_progress',
            'lessons_completed', 'total_lesson_time_minutes',
            'sessions_completed', 'total_session_minutes',
            'skills_assessed', 'average_skill_level',
            'milestones_achieved', 'learning_path_progress',
            'snapshot_date', 'created_at',
        ]
        read_only_fields = fields


class StudentProgressSummarySerializer(serializers.Serializer):
    """Serializer for student progress summary (dashboard)."""

    career = CareerSerializer()
    learning_path = LearningPathSerializer(allow_null=True)
    skill_assessments = SkillAssessmentSerializer(many=True)
    milestones = MilestoneSerializer(many=True)
    recent_snapshots = ProgressSnapshotSerializer(many=True)

    # Aggregated stats
    total_skills_assessed = serializers.IntegerField()
    average_skill_level = serializers.DecimalField(max_digits=3, decimal_places=2)
    milestones_count = serializers.IntegerField()
    courses_completed = serializers.IntegerField()
    sessions_completed = serializers.IntegerField()
    learning_path_progress = serializers.DecimalField(max_digits=5, decimal_places=2)