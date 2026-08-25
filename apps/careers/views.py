"""
Views for the Careers app.
"""
from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404

from .models import Career, CareerSkill, RoadmapStage, InterviewQuestion
from .serializers import (
    CareerListSerializer,
    CareerDetailSerializer,
    CareerSkillSerializer,
    RoadmapStageSerializer,
    InterviewQuestionSerializer,
)


class CareerViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for careers - read only for students/mentors."""

    queryset = Career.objects.filter(is_active=True).prefetch_related(
        'skills', 'roadmap_stages', 'interview_questions'
    )
    permission_classes = [AllowAny]
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return CareerListSerializer
        return CareerDetailSerializer

    @action(detail=True, methods=['get'], url_path='skills')
    def skills(self, request, slug=None):
        """Get skills for a specific career."""
        career = self.get_object()
        skills = career.skills.filter(is_core=True).order_by('order')
        serializer = CareerSkillSerializer(skills, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=True, methods=['get'], url_path='roadmap')
    def roadmap(self, request, slug=None):
        """Get roadmap stages for a specific career."""
        career = self.get_object()
        stages = career.roadmap_stages.filter(is_active=True).order_by('order')
        serializer = RoadmapStageSerializer(stages, many=True)
        return Response({'success': True, 'data': serializer.data})

    @action(detail=True, methods=['get'], url_path='interview-questions')
    def interview_questions(self, request, slug=None):
        """Get interview questions for a specific career."""
        career = self.get_object()
        questions = career.interview_questions.filter(is_active=True).order_by('order')
        serializer = InterviewQuestionSerializer(questions, many=True)
        return Response({'success': True, 'data': serializer.data})


class CareerSkillViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for career skills."""

    queryset = CareerSkill.objects.select_related('career').filter(career__is_active=True)
    serializer_class = CareerSkillSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['career', 'is_core']


class RoadmapStageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for roadmap stages."""

    queryset = RoadmapStage.objects.select_related('career').filter(career__is_active=True, is_active=True)
    serializer_class = RoadmapStageSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['career']


class InterviewQuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for interview questions."""

    queryset = InterviewQuestion.objects.select_related('career').filter(career__is_active=True, is_active=True)
    serializer_class = InterviewQuestionSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['career', 'difficulty']