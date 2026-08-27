"""
URL configuration for the Careers app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CareerViewSet,
    CareerSkillViewSet,
    RoadmapStageViewSet,
    InterviewQuestionViewSet,
)

router = DefaultRouter()
router.register(r'', CareerViewSet, basename='career')
router.register(r'skills', CareerSkillViewSet, basename='career-skill')
router.register(r'roadmap', RoadmapStageViewSet, basename='roadmap-stage')
router.register(r'interview-questions', InterviewQuestionViewSet, basename='interview-question')

urlpatterns = [
    path('', include(router.urls)),
]