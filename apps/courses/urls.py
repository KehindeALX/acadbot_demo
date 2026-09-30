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
from .certificates import issue_certificate

router = DefaultRouter()
# Register specific routes FIRST to avoid conflicts with course-detail catch-all
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'', CourseViewSet, basename='course')

urlpatterns = [
    path('<int:course_id>/certificate/', issue_certificate, name='certificate-issue'),
    path('', include(router.urls)),
]