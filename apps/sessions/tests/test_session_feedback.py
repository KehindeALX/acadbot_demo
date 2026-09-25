"""
Tests for the session feedback permissions.

Feedback must only be writable by the two people on the session (the student
and the mentor) or an admin, so a student cannot attach a rating to a session
they have no part in.
"""
import pytest
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient

from django.utils import timezone

from apps.accounts.models import User, StudentProfile, MentorProfile
from apps.matching.models import MatchRequest, Match
from apps.sessions.models import Session, SessionFeedback


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def session_student(db):
    user = User.objects.create_user(
        username='fbstudent', email='fbstudent@test.com',
        password='TestPass123', role=User.Role.STUDENT,
    )
    StudentProfile.objects.create(user=user)
    return user


@pytest.fixture
def session_mentor(db):
    user = User.objects.create_user(
        username='fbmentor', email='fbmentor@test.com',
        password='TestPass123', role=User.Role.MENTOR,
    )
    MentorProfile.objects.create(user=user)
    return user


@pytest.fixture
def unrelated_student(db):
    user = User.objects.create_user(
        username='fboutsider', email='fboutsider@test.com',
        password='TestPass123', role=User.Role.STUDENT,
    )
    StudentProfile.objects.create(user=user)
    return user


@pytest.fixture
def live_session(session_student, session_mentor):
    match_request = MatchRequest.objects.create(student=session_student)
    match = Match.objects.create(
        match_request=match_request,
        student=session_student,
        mentor=session_mentor,
        status=Match.Status.ACTIVE,
    )
    return Session.objects.create(
        match=match,
        student=session_student,
        mentor=session_mentor,
        scheduled_at=timezone.now() + timedelta(days=1),
        status=Session.Status.COMPLETED,
    )


def feedback_url(session):
    return f'/api/sessions/{session.id}/feedback/'


def feedback_payload():
    return {
        'feedback_type': Session.FeedbackType.STUDENT,
        'rating': 5,
        'strengths': 'Clear explanations.',
    }


@pytest.mark.django_db
class TestSessionFeedbackPermissions:
    """Only session participants or an admin may create feedback."""

    def test_non_participant_cannot_create_feedback(self, api_client, live_session, unrelated_student):
        """A student with no part in the session is blocked from rating it."""
        api_client.force_authenticate(user=unrelated_student)

        response = api_client.post(feedback_url(live_session), feedback_payload(), format='json')

        assert response.status_code in (
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        )
        assert SessionFeedback.objects.filter(session=live_session).count() == 0

    def test_participant_can_create_feedback(self, api_client, live_session, session_student):
        """The student on the session can still leave feedback."""
        api_client.force_authenticate(user=session_student)

        response = api_client.post(feedback_url(live_session), feedback_payload(), format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert SessionFeedback.objects.filter(session=live_session, author=session_student).count() == 1
