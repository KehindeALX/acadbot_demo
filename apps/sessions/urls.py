"""
URL configuration for the Sessions app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SessionViewSet,
    SessionRecurrenceViewSet,
    AvailabilityViewSet,
    MentorAvailabilityViewSet,
    SessionFeedbackViewSet,
)

router = DefaultRouter()
router.register(r'', SessionViewSet, basename='session')
router.register(r'recurrences', SessionRecurrenceViewSet, basename='session-recurrence')
router.register(r'availability', AvailabilityViewSet, basename='availability')

# Nested routes for mentor availability (public)
mentor_router = DefaultRouter()
mentor_router.register(r'availability', MentorAvailabilityViewSet, basename='mentor-availability')

# Nested routes for session feedback
feedback_router = DefaultRouter()
feedback_router.register(r'feedback', SessionFeedbackViewSet, basename='session-feedback')

urlpatterns = [
    path('', include(router.urls)),
    # Public mentor availability
    path('mentors/<int:mentor_id>/', include(mentor_router.urls)),
    # Session feedback (nested under sessions)
    path('<int:session_pk>/', include(feedback_router.urls)),
]