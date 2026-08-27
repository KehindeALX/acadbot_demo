"""
Tests for authentication endpoints: register, login, logout, me.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User, StudentProfile, MentorProfile


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def student_user(db):
    user = User.objects.create_user(
        username='existingstudent',
        email='existingstudent@test.com',
        password='TestPass123',
        role=User.Role.STUDENT,
    )
    StudentProfile.objects.create(user=user)
    return user


@pytest.mark.django_db
class TestRegistration:
    url = '/api/auth/register/'

    def valid_payload(self, **overrides):
        payload = {
            'username': 'newstudent',
            'email': 'newstudent@test.com',
            'password': 'TestPass123',
            'password_confirm': 'TestPass123',
            'role': User.Role.STUDENT,
            'first_name': 'New',
            'last_name': 'Student',
        }
        payload.update(overrides)
        return payload

    def test_register_student_creates_user_and_profile(self, api_client):
        response = api_client.post(self.url, self.valid_payload(), format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True

        user = User.objects.get(email='newstudent@test.com')
        assert user.role == User.Role.STUDENT
        assert user.check_password('TestPass123')
        assert StudentProfile.objects.filter(user=user).exists()

    def test_register_mentor_creates_user_and_profile(self, api_client):
        payload = self.valid_payload(
            username='newmentor',
            email='newmentor@test.com',
            role=User.Role.MENTOR,
        )
        response = api_client.post(self.url, payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email='newmentor@test.com')
        assert user.role == User.Role.MENTOR
        assert MentorProfile.objects.filter(user=user).exists()
        assert not StudentProfile.objects.filter(user=user).exists()

    def test_register_password_mismatch_returns_400(self, api_client):
        payload = self.valid_payload(password_confirm='SomethingElse123')
        response = api_client.post(self.url, payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
        assert 'password_confirm' in response.data['error']['details']
        assert not User.objects.filter(email='newstudent@test.com').exists()

    def test_register_duplicate_email_returns_400(self, api_client, student_user):
        payload = self.valid_payload(email=student_user.email, username='differentusername')
        response = api_client.post(self.url, payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in response.data['error']['details']

    def test_register_duplicate_username_returns_400(self, api_client, student_user):
        payload = self.valid_payload(username=student_user.username, email='different@test.com')
        response = api_client.post(self.url, payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'username' in response.data['error']['details']

    def test_register_password_too_short_returns_400(self, api_client):
        payload = self.valid_payload(password='short', password_confirm='short')
        response = api_client.post(self.url, payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data['error']['details']


@pytest.mark.django_db
class TestLogin:
    url = '/api/auth/login/'

    def test_login_with_valid_credentials_succeeds(self, api_client, student_user):
        response = api_client.post(
            self.url,
            {'email': student_user.email, 'password': 'TestPass123'},
            format='json',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['email'] == student_user.email

    def test_login_with_wrong_password_returns_400(self, api_client, student_user):
        response = api_client.post(
            self.url,
            {'email': student_user.email, 'password': 'WrongPassword'},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_with_unknown_email_returns_400(self, api_client):
        response = api_client.post(
            self.url,
            {'email': 'doesnotexist@test.com', 'password': 'TestPass123'},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_actually_establishes_session(self, api_client, student_user):
        """A logged-in user should be able to hit an IsAuthenticated endpoint afterward."""
        api_client.post(
            self.url,
            {'email': student_user.email, 'password': 'TestPass123'},
            format='json',
        )
        response = api_client.get('/api/auth/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['email'] == student_user.email


@pytest.mark.django_db
class TestMeAndLogout:
    def test_me_rejects_anonymous_user(self, api_client):
        response = api_client.get('/api/auth/me/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_me_returns_authenticated_user_data(self, api_client, student_user):
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/auth/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['email'] == student_user.email
        assert response.data['data']['role'] == User.Role.STUDENT

    def test_logout_rejects_anonymous_user(self, api_client):
        response = api_client.post('/api/auth/logout/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_logout_ends_the_session(self, api_client, student_user):
        api_client.post(
            '/api/auth/login/',
            {'email': student_user.email, 'password': 'TestPass123'},
            format='json',
        )
        logout_response = api_client.post('/api/auth/logout/')
        assert logout_response.status_code == status.HTTP_200_OK

        me_response = api_client.get('/api/auth/me/')
        assert me_response.status_code == status.HTTP_403_FORBIDDEN