import hashlib
import hmac
import json
import logging
from urllib.error import HTTPError, URLError
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.careers.models import Career
from apps.courses.models import Course, Enrollment, Lesson
from apps.payments.models import Subscription

INITIALIZE_URL = '/api/payments/initialize/'
VERIFY_URL = '/api/payments/verify/'
STATUS_URL = '/api/payments/status/'
WEBHOOK_URL = '/api/payments/webhook/'

SECRET_KEY = 'sk_test_mock_key'
AMOUNT = 500000
SUBSCRIPTION_DAYS = 30
FREE_LESSONS = 2

SETTINGS = {
    'PAYSTACK_SECRET_KEY': SECRET_KEY,
    'SUBSCRIPTION_AMOUNT_KOBO': str(AMOUNT),
    'SUBSCRIPTION_DAYS': str(SUBSCRIPTION_DAYS),
    'FREE_LESSONS_PER_COURSE': str(FREE_LESSONS),
    'FRONTEND_BASE_URL': 'https://frontend.test',
}


def fake_config(key, **kwargs):
    return SETTINGS.get(key, kwargs.get('default', ''))


def signed_headers(raw_body, secret=SECRET_KEY):
    digest = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha512).hexdigest()
    return {'HTTP_X_PAYSTACK_SIGNATURE': digest}


def success_transaction(reference, amount=AMOUNT, status_value='success', currency='NGN'):
    return {
        'status': True,
        'message': 'Authorization URL created',
        'data': {
            'id': 302961,
            'reference': reference,
            'status': status_value,
            'amount': amount,
            'currency': currency,
            'gateway': 'bank',
            'gateway_response': 'Successful',
            'paid_at': '2026-09-30T02:11:04.000Z',
        },
    }


def fake_urlopen(body):
    class FakeResponse:
        def __init__(self, payload):
            self.payload = json.dumps(payload).encode('utf-8')

        def read(self):
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    return lambda req, timeout=None: FakeResponse(body)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def student(db):
    return User.objects.create_user(
        username='paystudent', email='paystudent@test.com',
        password='TestPass123', role=User.Role.STUDENT,
    )


@pytest.fixture
def course(db):
    career = Career.objects.create(
        slug='paid-career', name='Paid Career', icon='💳',
        tag='Test', color='#FF6B6B', description='Test career.', is_active=True,
    )
    course = Course.objects.create(
        career=career, title='Paid Course', description='Locked lessons.',
        module_number=1, order=1, is_published=True,
    )
    for order in range(1, 4):
        Lesson.objects.create(
            course=course,
            title=f'Lesson {order}',
            content_html=f'<p>Secret body {order}</p>',
            order=order,
            is_published=True,
            quiz_question=f'Question {order}',
            quiz_options=['Wrong', 'Right'],
            quiz_correct_index=1,
            quiz_feedback=f'Feedback {order}',
        )
    return course


@pytest.fixture
def enrollment(student, course):
    return Enrollment.objects.create(student=student, course=course)


def activate(student, days=SUBSCRIPTION_DAYS):
    return Subscription.objects.create(
        user=student,
        reference='acadbot-test-active',
        amount=AMOUNT,
        status=Subscription.Status.ACTIVE,
        paid_at=timezone.now(),
        expires_at=timezone.now() + timedelta(days=days),
    )


INITIALIZE_RESPONSE = {
    'status': True,
    'data': {
        'authorization_url': 'https://checkout.paystack.test/abc',
        'access_code': 'test_access_code',
        'reference': 'ignored',
    },
}


def initialize(client):
    with patch('apps.payments.services.config', side_effect=fake_config), \
            patch('apps.payments.services.urlopen', fake_urlopen(INITIALIZE_RESPONSE)):
        return client.post(INITIALIZE_URL, {}, format='json')


@pytest.mark.django_db
def test_initialize_requires_login(api_client):
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.post(INITIALIZE_URL, {}, format='json')
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.django_db
def test_initialize_returns_url_and_server_reference(api_client, student):
    api_client.force_authenticate(user=student)
    response = initialize(api_client)

    assert response.status_code == status.HTTP_200_OK
    data = response.data['data']
    assert data['authorization_url'] == 'https://checkout.paystack.test/abc'
    assert data['reference'].startswith('acadbot-')

    subscription = Subscription.objects.get(reference=data['reference'])
    assert subscription.user == student
    assert subscription.status == Subscription.Status.PENDING
    assert subscription.amount == AMOUNT


@pytest.mark.django_db
def test_initialize_amount_comes_from_settings_not_client(api_client, student):
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config), \
            patch('apps.payments.services.urlopen', fake_urlopen({
                'status': True,
                'data': {'authorization_url': 'https://checkout.paystack.test/abc'},
            })):
        response = api_client.post(INITIALIZE_URL, {'amount': 1}, format='json')

    subscription = Subscription.objects.get(reference=response.data['data']['reference'])
    assert subscription.amount == AMOUNT


@pytest.mark.django_db
def test_initialize_sends_the_return_page_as_callback(api_client, student):
    api_client.force_authenticate(user=student)
    sent = {}

    def capture(req, timeout=None):
        sent.update(json.loads(req.data.decode('utf-8')))
        return fake_urlopen(INITIALIZE_RESPONSE)(req, timeout)

    with patch('apps.payments.services.config', side_effect=fake_config), \
            patch('apps.payments.services.urlopen', capture):
        api_client.post(INITIALIZE_URL, {}, format='json')

    assert sent['callback_url'] == 'https://frontend.test/payment-return.html'


@pytest.mark.django_db
def test_initialize_references_are_unique(api_client, student):
    api_client.force_authenticate(user=student)
    first = initialize(api_client).data['data']['reference']
    second = initialize(api_client).data['data']['reference']
    assert first != second


@pytest.mark.django_db
def test_initialize_without_secret_returns_503(api_client, student):
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=lambda key, **kw: ''):
        response = api_client.post(INITIALIZE_URL, {}, format='json')

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert Subscription.objects.count() == 0


@pytest.mark.django_db
def test_verify_activates_access(api_client, student):
    api_client.force_authenticate(user=student)
    reference = initialize(api_client).data['data']['reference']

    with patch('apps.payments.services.config', side_effect=fake_config), \
            patch('apps.payments.services.urlopen', fake_urlopen(success_transaction(reference))):
        response = api_client.get(f'{VERIFY_URL}?reference={reference}')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['data']['active'] is True

    subscription = Subscription.objects.get(reference=reference)
    assert subscription.status == Subscription.Status.ACTIVE
    assert subscription.paid_at is not None

    expected = subscription.paid_at + timedelta(days=SUBSCRIPTION_DAYS)
    assert abs((subscription.expires_at - expected).total_seconds()) < 5


@pytest.mark.django_db
def test_verify_accepts_real_paystack_verify_shape(api_client, student):
    api_client.force_authenticate(user=student)
    reference = initialize(api_client).data['data']['reference']

    body = {
        'status': True,
        'message': 'Verification successful',
        'data': {
            'id': 302961,
            'reference': reference,
            'status': 'success',
            'amount': AMOUNT,
            'currency': 'NGN',
            'gateway': 'bank',
            'gateway_response': 'Successful',
            'paid_at': '2026-09-30T02:11:04.000Z',
        },
    }

    with patch('apps.payments.services.config', side_effect=fake_config), \
            patch('apps.payments.services.urlopen', fake_urlopen(body)):
        response = api_client.get(f'{VERIFY_URL}?reference={reference}')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['data']['active'] is True
    assert Subscription.objects.get(reference=reference).status == Subscription.Status.ACTIVE


@pytest.mark.django_db
def test_verify_rejects_non_naira_transaction(api_client, student):
    api_client.force_authenticate(user=student)
    reference = initialize(api_client).data['data']['reference']

    with patch('apps.payments.services.config', side_effect=fake_config), \
            patch('apps.payments.services.urlopen', fake_urlopen(success_transaction(reference, currency='USD'))):
        response = api_client.get(f'{VERIFY_URL}?reference={reference}')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['data']['active'] is False
    assert Subscription.objects.get(reference=reference).status == Subscription.Status.FAILED


@pytest.mark.django_db
def test_verify_rejects_amount_mismatch(api_client, student):
    api_client.force_authenticate(user=student)
    reference = initialize(api_client).data['data']['reference']

    with patch('apps.payments.services.config', side_effect=fake_config), \
            patch('apps.payments.services.urlopen', fake_urlopen(success_transaction(reference, amount=100))):
        response = api_client.get(f'{VERIFY_URL}?reference={reference}')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['data']['active'] is False
    assert Subscription.objects.get(reference=reference).status == Subscription.Status.FAILED


@pytest.mark.django_db
def test_verify_rejects_failed_transaction(api_client, student):
    api_client.force_authenticate(user=student)
    reference = initialize(api_client).data['data']['reference']

    with patch('apps.payments.services.config', side_effect=fake_config), \
            patch('apps.payments.services.urlopen', fake_urlopen(success_transaction(reference, status_value='failed'))):
        response = api_client.get(f'{VERIFY_URL}?reference={reference}')

    assert response.data['data']['active'] is False
    assert Subscription.objects.get(reference=reference).status == Subscription.Status.FAILED


@pytest.mark.django_db
def test_verify_reports_pending_without_failing_the_subscription(api_client, student):
    api_client.force_authenticate(user=student)
    reference = initialize(api_client).data['data']['reference']

    with patch('apps.payments.services.config', side_effect=fake_config), \
            patch('apps.payments.services.urlopen', fake_urlopen(success_transaction(reference, status_value='pending'))):
        response = api_client.get(f'{VERIFY_URL}?reference={reference}')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['data']['pending'] is True
    assert response.data['data']['active'] is False
    assert Subscription.objects.get(reference=reference).status == Subscription.Status.PENDING


@pytest.mark.django_db
def test_verify_rejects_another_users_reference(api_client, student, db):
    other = User.objects.create_user(
        username='otherstudent', email='other@test.com',
        password='TestPass123', role=User.Role.STUDENT,
    )
    reference = Subscription.objects.create(user=other, reference='acadbot-someone-else', amount=AMOUNT).reference

    api_client.force_authenticate(user=student)
    response = api_client.get(f'{VERIFY_URL}?reference={reference}')

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Subscription.objects.get(reference=reference).status == Subscription.Status.PENDING


@pytest.mark.django_db
def test_verify_requires_reference(api_client, student):
    api_client.force_authenticate(user=student)
    response = api_client.get(VERIFY_URL)
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_webhook_with_valid_signature_activates(api_client, student):
    reference = 'acadbot-webhook-valid'
    Subscription.objects.create(user=student, reference=reference, amount=AMOUNT)

    raw_body = json.dumps({'event': 'charge.success', 'data': {
        'reference': reference, 'status': 'success', 'amount': AMOUNT,
        'currency': 'NGN', 'gateway_response': 'Successful',
    }}).encode('utf-8')

    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.post(
            WEBHOOK_URL, raw_body, content_type='application/json', **signed_headers(raw_body),
        )

    assert response.status_code == status.HTTP_200_OK
    assert Subscription.objects.get(reference=reference).status == Subscription.Status.ACTIVE


@pytest.mark.django_db
def test_webhook_with_invalid_signature_is_rejected(api_client, student):
    reference = 'acadbot-webhook-bad-signature'
    Subscription.objects.create(user=student, reference=reference, amount=AMOUNT)

    raw_body = json.dumps({'event': 'charge.success', 'data': {
        'reference': reference, 'status': 'success', 'amount': AMOUNT,
        'currency': 'NGN', 'gateway_response': 'Successful',
    }}).encode('utf-8')

    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.post(
            WEBHOOK_URL, raw_body, content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE='not-the-right-signature',
        )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert Subscription.objects.get(reference=reference).status == Subscription.Status.PENDING


@pytest.mark.django_db
def test_webhook_without_signature_is_rejected(api_client, student):
    reference = 'acadbot-webhook-no-signature'
    Subscription.objects.create(user=student, reference=reference, amount=AMOUNT)

    raw_body = json.dumps({'data': {'reference': reference, 'status': 'success', 'amount': AMOUNT}}).encode('utf-8')

    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.post(WEBHOOK_URL, raw_body, content_type='application/json')

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert Subscription.objects.get(reference=reference).status == Subscription.Status.PENDING


@pytest.mark.django_db
def test_webhook_is_idempotent(api_client, student):
    reference = 'acadbot-webhook-twice'
    Subscription.objects.create(user=student, reference=reference, amount=AMOUNT)

    raw_body = json.dumps({'data': {'reference': reference, 'status': 'success', 'amount': AMOUNT}}).encode('utf-8')

    with patch('apps.payments.services.config', side_effect=fake_config):
        first = api_client.post(WEBHOOK_URL, raw_body, content_type='application/json', **signed_headers(raw_body))
        first_expiry = Subscription.objects.get(reference=reference).expires_at

        second = api_client.post(WEBHOOK_URL, raw_body, content_type='application/json', **signed_headers(raw_body))

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_200_OK
    assert Subscription.objects.count() == 1

    subscription = Subscription.objects.get(reference=reference)
    assert subscription.status == Subscription.Status.ACTIVE
    assert subscription.expires_at == first_expiry


@pytest.mark.django_db
def test_webhook_rejects_amount_mismatch(api_client, student):
    reference = 'acadbot-webhook-amount'
    Subscription.objects.create(user=student, reference=reference, amount=AMOUNT)

    raw_body = json.dumps({'data': {'reference': reference, 'status': 'success', 'amount': 100,
        'currency': 'NGN', 'gateway_response': 'Successful'}}).encode('utf-8')

    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.post(WEBHOOK_URL, raw_body, content_type='application/json', **signed_headers(raw_body))

    assert response.status_code == status.HTTP_200_OK
    assert Subscription.objects.get(reference=reference).status == Subscription.Status.FAILED


@pytest.mark.django_db
def test_webhook_ignores_unknown_reference(api_client, db):
    raw_body = json.dumps({'data': {'reference': 'acadbot-nope', 'status': 'success', 'amount': AMOUNT}}).encode('utf-8')

    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.post(WEBHOOK_URL, raw_body, content_type='application/json', **signed_headers(raw_body))

    assert response.status_code == status.HTTP_200_OK
    assert Subscription.objects.count() == 0


@pytest.mark.django_db
def test_webhook_does_not_require_csrf_token(api_client, student):
    reference = 'acadbot-webhook-csrf'
    Subscription.objects.create(user=student, reference=reference, amount=AMOUNT)

    raw_body = json.dumps({'data': {'reference': reference, 'status': 'success', 'amount': AMOUNT}}).encode('utf-8')

    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.post(WEBHOOK_URL, raw_body, content_type='application/json', **signed_headers(raw_body))

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_status_inactive_without_subscription(api_client, student):
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.get(STATUS_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data['data']['active'] is False
    assert response.data['data']['expires_at'] is None


@pytest.mark.django_db
def test_status_active_with_subscription(api_client, student):
    subscription = activate(student)
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.get(STATUS_URL)

    assert response.data['data']['active'] is True
    assert response.data['data']['expires_at'] == subscription.expires_at


@pytest.mark.django_db
def test_status_expired_subscription_is_inactive(api_client, student):
    Subscription.objects.create(
        user=student, reference='acadbot-expired', amount=AMOUNT,
        status=Subscription.Status.ACTIVE,
        paid_at=timezone.now() - timedelta(days=60),
        expires_at=timezone.now() - timedelta(days=30),
    )
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.get(STATUS_URL)

    assert response.data['data']['active'] is False


def lesson_url(lesson):
    return f'/api/courses/lessons/{lesson.id}/'


@pytest.mark.django_db
def test_free_lessons_are_open_to_enrolled_student(api_client, student, course, enrollment):
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.get(lesson_url(course.lessons.get(order=1)))

    assert response.status_code == status.HTTP_200_OK
    assert response.data['is_locked'] is False
    assert response.data['content_html'] == '<p>Secret body 1</p>'


@pytest.mark.django_db
def test_locked_lesson_returns_402_with_no_content(api_client, student, course, enrollment):
    locked = course.lessons.get(order=3)
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.get(lesson_url(locked))

    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert response.data['error']['code'] == 402
    assert response.data['error']['message']

    body = json.dumps(response.data)
    assert 'Secret body 3' not in body
    assert 'Question 3' not in body


@pytest.mark.django_db
def test_locked_quiz_submission_returns_402(api_client, student, course, enrollment):
    locked = course.lessons.get(order=3)
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.post(f'{lesson_url(locked)}quiz/', {'answer_index': 1}, format='json')

    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED
    assert 'Correct' not in json.dumps(response.data)
    assert 'Feedback 3' not in json.dumps(response.data)


@pytest.mark.django_db
def test_locked_lesson_complete_returns_402(api_client, student, course, enrollment):
    locked = course.lessons.get(order=3)
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.post(f'{lesson_url(locked)}complete/', {}, format='json')

    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED


@pytest.mark.django_db
def test_access_opens_all_lessons_after_payment(api_client, student, course, enrollment):
    locked = course.lessons.get(order=3)
    activate(student)

    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.get(lesson_url(locked))

    assert response.status_code == status.HTTP_200_OK
    assert response.data['is_locked'] is False
    assert response.data['content_html'] == '<p>Secret body 3</p>'


@pytest.mark.django_db
def test_quiz_submission_works_after_payment(api_client, student, course, enrollment):
    locked = course.lessons.get(order=3)
    activate(student)

    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.post(f'{lesson_url(locked)}quiz/', {'answer_index': 1}, format='json')

    assert response.status_code == status.HTTP_200_OK
    assert response.data['data']['result']['correct'] is True
    assert response.data['data']['result']['correct_index'] == 1


@pytest.mark.django_db
def test_expired_access_locks_lessons_again(api_client, student, course, enrollment):
    Subscription.objects.create(
        user=student, reference='acadbot-gone', amount=AMOUNT,
        status=Subscription.Status.ACTIVE,
        paid_at=timezone.now() - timedelta(days=40),
        expires_at=timezone.now() - timedelta(days=10),
    )
    locked = course.lessons.get(order=3)

    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.get(lesson_url(locked))

    assert response.status_code == status.HTTP_402_PAYMENT_REQUIRED


@pytest.mark.django_db
def test_course_detail_blanks_locked_lesson_content(api_client, student, course, enrollment):
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.get(f'/api/courses/{course.id}/')

    assert response.status_code == status.HTTP_200_OK
    lessons = {lesson['order']: lesson for lesson in response.data['lessons']}

    assert lessons[1]['is_locked'] is False
    assert lessons[1]['content_html'] == '<p>Secret body 1</p>'

    assert lessons[3]['is_locked'] is True
    assert lessons[3]['content_html'] == ''
    assert lessons[3]['has_quiz'] is False
    assert lessons[3]['quiz_question'] == ''
    assert lessons[3]['quiz_options'] == []


@pytest.mark.django_db
def test_anonymous_course_detail_shows_lesson_content(api_client, course):
    with patch('apps.payments.services.config', side_effect=fake_config):
        response = api_client.get(f'/api/courses/{course.id}/')

    assert response.status_code == status.HTTP_200_OK
    lessons = {lesson['order']: lesson for lesson in response.data['lessons']}
    assert lessons[3]['content_html'] == '<p>Secret body 3</p>'


@pytest.mark.django_db
def test_free_lesson_limit_is_configurable(api_client, student, course, enrollment):
    settings = dict(SETTINGS, FREE_LESSONS_PER_COURSE='1')
    api_client.force_authenticate(user=student)

    with patch('apps.payments.services.config', side_effect=lambda key, **kw: settings.get(key, kw.get('default', ''))):
        second = api_client.get(lesson_url(course.lessons.get(order=2)))

    assert second.status_code == status.HTTP_402_PAYMENT_REQUIRED


@pytest.mark.django_db
def test_http_error_401_logs_code_and_body_not_key(api_client, student):
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config), \
         patch('apps.payments.services.urlopen', side_effect=lambda *a, **kw: (_ for _ in ()).throw(HTTPError('https://test', 401, 'Unauthorized', {}, fp=__import__('io').BytesIO(b'{"message":"bad key"}')))), \
         patch('apps.payments.views.logger') as mock_logger:
        response = api_client.post(INITIALIZE_URL, {}, format='json')
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    joined = ' '.join(str(a) for c in mock_logger.warning.call_args_list for a in c.args)
    assert '401' in joined
    assert 'bad key' in joined
    assert SECRET_KEY not in joined


@pytest.mark.django_db
def test_urlerror_logs_reason(api_client, student):
    api_client.force_authenticate(user=student)
    with patch('apps.payments.services.config', side_effect=fake_config), \
         patch('apps.payments.services.urlopen', side_effect=lambda *a, **kw: (_ for _ in ()).throw(URLError('connection refused'))), \
         patch('apps.payments.views.logger') as mock_logger:
        response = api_client.post(INITIALIZE_URL, {}, format='json')
    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    joined = ' '.join(str(a) for c in mock_logger.warning.call_args_list for a in c.args)
    assert 'connection refused' in joined


@pytest.mark.django_db
def test_secret_key_stripped_of_spaces_and_quotes(api_client, student):
    dirty = '  "  sk-test  "  '
    clean = dirty.strip().strip(chr(34) + chr(39))
    settings = dict(SETTINGS, PAYSTACK_SECRET_KEY=dirty)
    api_client.force_authenticate(user=student)
    captured = {}
    def capture_urlopen(req, timeout=30):
        captured['auth'] = req.headers.get('Authorization')
        mock_resp = MagicMock()
        mock_resp.read = lambda: b'{"data":{"authorization_url":"x","access_code":"y"}}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda *a: False
        return mock_resp
    with patch('apps.payments.services.config', side_effect=lambda k, **kw: settings.get(k, kw.get('default', ''))), \
         patch('apps.payments.services.urlopen', capture_urlopen):
        response = api_client.post(INITIALIZE_URL, {}, format='json')
    assert response.status_code == status.HTTP_200_OK
    assert captured['auth'] == f'Bearer {clean}'
