"""
Serializers for the Careers app.
"""
from rest_framework import serializers
from .models import Career, CareerSkill, RoadmapStage, InterviewQuestion


class CareerSkillSerializer(serializers.ModelSerializer):
    """Serializer for career skills."""

    class Meta:
        model = CareerSkill
        fields = ['id', 'name', 'order', 'is_core']


class RoadmapStageSerializer(serializers.ModelSerializer):
    """Serializer for roadmap stages."""

    class Meta:
        model = RoadmapStage
        fields = ['id', 'title', 'description', 'order', 'estimated_weeks']


class InterviewQuestionSerializer(serializers.ModelSerializer):
    """Serializer for interview questions."""

    class Meta:
        model = InterviewQuestion
        fields = ['id', 'question', 'order', 'difficulty']


class CareerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for career listings."""

    skills_count = serializers.IntegerField(source='skills.count', read_only=True)
    roadmap_stages_count = serializers.IntegerField(source='roadmap_stages.count', read_only=True)
    interview_questions_count = serializers.IntegerField(source='interview_questions.count', read_only=True)

    class Meta:
        model = Career
        fields = [
            'id', 'slug', 'name', 'icon', 'tag', 'color', 'description',
            'order', 'skills_count', 'roadmap_stages_count', 'interview_questions_count',
        ]


class CareerDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for career with nested data."""

    skills = CareerSkillSerializer(many=True, read_only=True)
    roadmap_stages = RoadmapStageSerializer(many=True, read_only=True)
    interview_questions = InterviewQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Career
        fields = [
            'id', 'slug', 'name', 'icon', 'tag', 'color', 'description',
            'order', 'skills', 'roadmap_stages', 'interview_questions',
        ]


class CareerSerializer(serializers.ModelSerializer):
    """Base serializer for career (used in relations)."""

    class Meta:
        model = Career
        fields = ['id', 'slug', 'name', 'icon', 'tag', 'color']