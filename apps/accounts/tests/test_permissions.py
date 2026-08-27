"""
Tests for permission checks around authentication and profile access.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts.models import User, StudentProfile, MentorProfile
from apps.core.permissions import IsOwnerOrMentorOrAdmin
from apps.matching.models import MatchRequest


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def student_user(db):
    user = User.objects.create_user(
        username='permstudent', email='permstudent@test.com',
        password='TestPass123', role=User.Role.STUDENT,
    )
    StudentProfile.objects.create(user=user)
    return user


@pytest.fixture
def other_student_user(db):
    user = User.objects.create_user(
        username='otherpermstudent', email='otherpermstudent@test.com',
        password='TestPass123', role=User.Role.STUDENT,
    )
    StudentProfile.objects.create(user=user)
    return user


@pytest.fixture
def mentor_user(db):
    user = User.objects.create_user(
        username='permmentor', email='permmentor@test.com',
        password='TestPass123', role=User.Role.MENTOR,
    )
    MentorProfile.objects.create(user=user)
    return user


@pytest.mark.django_db
class TestStudentProfileRoleAccess:
    """A mentor account should never be able to reach the student-profile endpoints."""

    url = '/api/auth/students/profile/'

    def test_mentor_cannot_list_student_profiles(self, api_client, mentor_user):
        api_client.force_authenticate(user=mentor_user)
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_student_can_access_own_profile_list(self, api_client, student_user):
        api_client.force_authenticate(user=student_user)
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_anonymous_user_cannot_access_student_profiles(self, api_client):
        response = api_client.get(self.url)
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestIsOwnerOrMentorOrAdmin:
    """
    Regression guard: this permission previously raised AttributeError because
    obj.student/obj.mentor are already User foreign keys, not profile objects
    with a `.user` attribute. These tests fail loudly if that pattern comes back.
    """

    def _request(self, user):
        request = APIRequestFactory().get('/x')
        request.user = user
        return request

    def test_owner_is_granted_object_permission(self, student_user):
        match_request = MatchRequest.objects.create(student=student_user)
        permission = IsOwnerOrMentorOrAdmin()

        result = permission.has_object_permission(
            self._request(student_user), None, match_request,
        )
        assert result is True

    def test_non_owner_is_denied_object_permission(self, student_user, other_student_user):
        match_request = MatchRequest.objects.create(student=student_user)
        permission = IsOwnerOrMentorOrAdmin()

        result = permission.has_object_permission(
            self._request(other_student_user), None, match_request,
        )
        assert result is False

    def test_admin_is_granted_object_permission(self, student_user, db):
        admin = User.objects.create_user(
            username='permadmin', email='permadmin@test.com',
            password='TestPass123', role=User.Role.ADMIN,
        )
        match_request = MatchRequest.objects.create(student=student_user)
        permission = IsOwnerOrMentorOrAdmin()

        result = permission.has_object_permission(
            self._request(admin), None, match_request,
        )
        assert result is True