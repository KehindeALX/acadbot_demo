"""
Tests for auth rate limiting.

register and login are throttled to 5 requests/min *per IP* in production
settings, but the suite-wide settings relax that to 10000/min so unrelated
tests don't 429. These tests force the real 5/min back on with an autouse
override_settings fixture, so they can prove the limit actually binds.
"""
import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.settings import api_settings
from rest_framework.test import APIClient

LOGIN_URL = '/api/auth/login/'
REGISTER_URL = '/api/auth/register/'

TIGHT_RATES = {
    'register': '5/min',
    'login': '5/min',
}


def _reset_api_settings_cache():
    """Make DRF re-read DEFAULT_THROTTLE_RATES from the live Django settings.

    DRF's APISettings resolves the REST_FRAMEWORK dict lazily and caches both
    it (`_user_settings`) and each resolved attribute on first access, so a
    bare override_settings won't take effect once anything has read the rates.
    Clearing both caches makes the next lookup hit the overridden settings --
    and, on teardown, the original relaxed suite rates.
    """
    if hasattr(api_settings, '_user_settings'):
        del api_settings._user_settings
    api_settings._cached_attrs.discard('DEFAULT_THROTTLE_RATES')
    api_settings.__dict__.pop('DEFAULT_THROTTLE_RATES', None)


@pytest.fixture(autouse=True)
def tight_rates():
    """Force the real production rates for the duration of each test here.

    The override starts from the live REST_FRAMEWORK settings and swaps only
    DEFAULT_THROTTLE_RATES, so keys like EXCEPTION_HANDLER stay intact --
    replacing the whole dict would silently drop the custom error handler and
    a throttled response would come back unwrapped (no `success` envelope).
    """
    overridden_rates = dict(api_settings.user_settings)
    overridden_rates['DEFAULT_THROTTLE_RATES'] = TIGHT_RATES
    with override_settings(REST_FRAMEWORK=overridden_rates):
        _reset_api_settings_cache()
        yield
        _reset_api_settings_cache()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def flush_throttle_cache():
    """Reset the throttle cache so one test's bucket counts don't leak into the next."""
    cache.clear()
    yield
    cache.clear()


def post_login(client, email='student@test.com'):
    return client.post(
        LOGIN_URL,
        {'email': email, 'password': 'TestPass123'},
        format='json',
    )


def post_register(client, email):
    username = email.split('@')[0]
    return client.post(
        REGISTER_URL,
        {
            'username': username,
            'email': email,
            'password': 'TestPass123',
            'password_confirm': 'TestPass123',
        },
        format='json',
    )


@pytest.mark.django_db
class TestLoginRateLimit:
    """5 login attempts/min per IP; the 6th is rejected with 429."""

    def test_first_five_attempts_are_not_throttled(self, api_client):
        for _ in range(5):
            response = post_login(api_client)
            # 200 would mean success; 400 is the serializer rejecting the
            # unknown email. Either is fine — the point is it's not a 429.
            assert response.status_code in (
                status.HTTP_200_OK,
                status.HTTP_400_BAD_REQUEST,
            )

    def test_sixth_attempt_is_throttled(self, api_client):
        for _ in range(5):
            post_login(api_client)
        response = post_login(api_client)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        # The custom exception handler must wrap the throttled error in the
        # standard { success, error: { message, details } } envelope so the
        # frontend (formatApiError) can render it cleanly.
        body = response.data
        assert body['success'] is False
        assert body['error']['code'] == status.HTTP_429_TOO_MANY_REQUESTS
        assert 'throttled' in body['error']['message'].lower()
        assert 'throttled' in body['error']['details']['detail'].lower()


@pytest.mark.django_db
class TestRegisterRateLimit:
    """5 registration attempts/min per IP; the 6th is rejected with 429."""

    def test_sixth_attempt_is_throttled(self, api_client):
        for i in range(5):
            assert post_register(api_client, f'user{i}@test.com').status_code == status.HTTP_201_CREATED
        response = post_register(api_client, 'sixth@test.com')
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_login_and_register_have_independent_buckets(self, api_client):
        # Exhausting the register bucket must NOT throttle login.
        for i in range(5):
            post_register(api_client, f'user{i}@test.com')
        assert post_register(api_client, 'sixth@test.com').status_code == status.HTTP_429_TOO_MANY_REQUESTS
        # Login's own 5/min bucket is untouched.
        first = post_login(api_client)
        assert first.status_code in (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST)