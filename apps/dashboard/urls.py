"""
URL configuration for the Dashboard app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentDashboardViewSet, MentorDashboardViewSet, AdminDashboardViewSet

router = DefaultRouter()
router.register(r'student', StudentDashboardViewSet, basename='student-dashboard')
router.register(r'mentor', MentorDashboardViewSet, basename='mentor-dashboard')
router.register(r'admin', AdminDashboardViewSet, basename='admin-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]