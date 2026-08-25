"""
URL configuration for the Progress app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SkillAssessmentViewSet,
    MilestoneViewSet,
    LearningPathViewSet,
    ProgressSnapshotViewSet,
    StudentProgressViewSet,
)

router = DefaultRouter()
router.register(r'skills', SkillAssessmentViewSet, basename='skill-assessment')
router.register(r'milestones', MilestoneViewSet, basename='milestone')
router.register(r'learning-path', LearningPathViewSet, basename='learning-path')
router.register(r'snapshots', ProgressSnapshotViewSet, basename='progress-snapshot')

# Separate router for aggregated progress summary
progress_router = DefaultRouter()
progress_router.register(r'', StudentProgressViewSet, basename='progress-summary')

urlpatterns = [
    path('', include(router.urls)),
    path('summary/', include(progress_router.urls)),
]