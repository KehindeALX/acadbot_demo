"""
URL configuration for the Accounts app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuthViewSet,
    StudentProfileViewSet,
    MentorProfileViewSet,
    MentorPublicViewSet,
    csrf_token_view,
)

router = DefaultRouter()
router.register(r'students/profile', StudentProfileViewSet, basename='student-profile')
router.register(r'mentors/profile', MentorProfileViewSet, basename='mentor-profile')
router.register(r'mentors', MentorPublicViewSet, basename='mentor-public')

auth_viewset = AuthViewSet.as_view({
    'post': 'register',
})
login_viewset = AuthViewSet.as_view({
    'post': 'login',
})
logout_viewset = AuthViewSet.as_view({
    'post': 'logout',
})
me_viewset = AuthViewSet.as_view({
    'get': 'me',
    'patch': 'update_me',
})

urlpatterns = [
    path('csrf/', csrf_token_view, name='csrf-token'),
    path('register/', auth_viewset, name='register'),
    path('login/', login_viewset, name='login'),
    path('logout/', logout_viewset, name='logout'),
    path('me/', me_viewset, name='me'),
    path('', include(router.urls)),
]