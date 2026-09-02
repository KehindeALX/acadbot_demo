"""
URL configuration for the Courses app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CourseViewSet,
    LessonViewSet,
    EnrollmentViewSet,
)

router = DefaultRouter()
# Register specific routes FIRST to avoid conflicts with course-detail catch-all
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'', CourseViewSet, basename='course')

urlpatterns = [
    path('', include(router.urls)),
]