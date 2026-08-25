"""
URL configuration for the Matching app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MatchRequestViewSet, MatchViewSet, MentorMatchSuggestionViewSet

router = DefaultRouter()
router.register(r'requests', MatchRequestViewSet, basename='match-request')
router.register(r'matches', MatchViewSet, basename='match')
router.register(r'suggestions', MentorMatchSuggestionViewSet, basename='mentor-suggestion')

urlpatterns = [
    path('', include(router.urls)),
]