import copy
import json
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.guide.models import GuideUsage

ANALYZE_URL = '/api/guide/speakpro/analyze/'
FEEDBACK_URL = '/api/guide/speakpro/feedback/'

SETTINGS = {
    'OPENROUTER_API_KEY': 'sk-test',
    'OPENROUTER_MODEL': 'vendor/some-model',
    'GUIDE_DAILY_LIMIT': '5',
    'GUIDE_GLOBAL_DAILY_LIMIT': '40',
    'GUIDE_MAX_TOKENS': '500',
}

ANALYZE_PAYLOAD = {
    'skills': 'Data analysis and Excel reporting',
    'project': 'I built a stock card report for a pharmacy in Aba',
    'goal': 'Land an analyst role in Lagos',
}

FEEDBACK_PAYLOAD = {
    'answers': [
        {'question': 'What did you build?', 'answer': 'A stock report for a pharmacy.'},
        {'question': 'Why does it matter?', 'answer': 'They stopped losing stock.'},
        {'question': 'What would you change?', 'answer': 'I would automate the refresh.'},
    ],
}

ANALYZE_REPLY = {
    'summary': 'You know the work but you skip the reason it matters.',
    'dimensions': [
        {'name': 'Clarity', 'score': 3, 'note': 'Short sentences, but the result is missing.'},
        {'name': 'Structure', 'score': 2, 'note': 'No opening, middle and close.'},
        {'name': 'Vocabulary', 'score': 4, 'note': 'You use the right trade words.'},
        {'name': 'Confidence', 'score': 2, 'note': 'Hedging words soften your claims.'},
        {'name': 'Audience awareness', 'score': 3, 'note': 'Some detail is too technical.'},
    ],
    'gaps': ['You never say what changed', 'No numbers', 'Technical terms go unexplained'],
    'questions': [
        'Explain the stock report to a manager who does not use Excel.',
        'What did the pharmacy save by having it?',
        'What would you improve if you built it again?',
    ],
    'pitch': {
        'headline': 'I turn messy pharmacy stock data into weekly reports',
        'one_liner': 'I built a weekly stock report that cut expired stock for a pharmacy in Aba.',
        'points': ['Built and run in one week', 'Cut expired stock', 'Plain reports a manager reads'],
    },
}

FEEDBACK_REPLY = {
    'overall': 'You were clear and specific. The answers just need a reason attached.',
    'strengths': ['You gave a real example', 'Plain language'],
    'improve': ['Say what changed because of you', 'Start with the outcome'],
    'rewrites': [
        {'question': 'What did you build?', 'better_answer': 'A weekly stock report the manager reads in one minute.'},
        {'question': 'Why does it matter?', 'better_answer': 'They cut expired stock because they saw it early.'},
        {'question': 'What would you change?', 'better_answer': 'I would automate the refresh so it runs itself.'},
    ],
}


def fake_config(key, **kwargs):
    return SETTINGS.get(key, kwargs.get('default', ''))


def fake_config_without_key(key, **kwargs):
    if key == 'OPENROUTER_API_KEY':
        return ''
    return SETTINGS.get(key, kwargs.get('default', ''))


def fake_urlopen(content):
    class FakeResponse:
        def __init__(self, payload):
            self.payload = json.dumps({
                'choices': [{'message': {'role': 'assistant', 'content': content}}],
                'usage': {'prompt_tokens': 200, 'completion_tokens': 90},
            }).encode('utf-8')

        def read(self):
            return self.payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    return lambda req, timeout=None: FakeResponse(content)


@contextmanager
def openrouter(reply_fn, config_fn=fake_config):
    with patch('apps.guide.views.config', side_effect=config_fn), \
            patch('apps.guide.speakpro_views.config', side_effect=config_fn), \
            patch('apps.guide.views.urlopen', reply_fn):
        yield


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def student_user(db):
    return User.objects.create_user(
        username='speakstudent', email='speakstudent@test.com',
        password='TestPass123', role=User.Role.STUDENT,
    )


def call_api(reply_fn, url, client, payload):
    with openrouter(reply_fn):
        return client.post(url, payload, format='json')


def post_analyze(client, payload=None):
    return call_api(fake_urlopen(json.dumps(ANALYZE_REPLY)), ANALYZE_URL, client, payload or ANALYZE_PAYLOAD)


def post_feedback(client, payload=None):
    return call_api(fake_urlopen(json.dumps(FEEDBACK_REPLY)), FEEDBACK_URL, client, payload or FEEDBACK_PAYLOAD)


@pytest.mark.django_db
def test_unauthenticated_is_rejected(api_client):
    assert api_client.post(ANALYZE_URL, ANALYZE_PAYLOAD, format='json').status_code in (
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN,
    )
    assert api_client.post(FEEDBACK_URL, FEEDBACK_PAYLOAD, format='json').status_code in (
        status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN,
    )


@pytest.mark.django_db
def test_analyze_rejects_blank_fields(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    response = api_client.post(
        ANALYZE_URL,
        {'skills': '  ', 'project': 'x', 'goal': 'y'},
        format='json',
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_analyze_rejects_oversized_skills(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    response = api_client.post(
        ANALYZE_URL,
        {**ANALYZE_PAYLOAD, 'skills': 'a' * 401},
        format='json',
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_feedback_rejects_two_answers(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    response = api_client.post(
        FEEDBACK_URL,
        {'answers': FEEDBACK_PAYLOAD['answers'][:2]},
        format='json',
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_feedback_rejects_four_answers(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    answers = FEEDBACK_PAYLOAD['answers'] + [
        {'question': 'Extra?', 'answer': 'No.'},
    ]
    response = api_client.post(FEEDBACK_URL, {'answers': answers}, format='json')
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_missing_key_returns_503(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    with openrouter(fake_urlopen('{}'), config_fn=fake_config_without_key):
        response = api_client.post(ANALYZE_URL, ANALYZE_PAYLOAD, format='json')
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


@pytest.mark.django_db
def test_analyze_daily_limit_returns_429(api_client, student_user):
    for _ in range(5):
        GuideUsage.objects.create(user=student_user, prompt_tokens=10, completion_tokens=5)

    api_client.force_authenticate(user=student_user)
    response = post_analyze(api_client)

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert GuideUsage.objects.count() == 5


@pytest.mark.django_db
def test_analyze_global_limit_returns_429(api_client, student_user):
    other = User.objects.create_user(
        username='otherspeak', email='otherspeak@test.com',
        password='TestPass123', role=User.Role.STUDENT,
    )
    for _ in range(4):
        GuideUsage.objects.create(user=student_user, prompt_tokens=10, completion_tokens=5)
    for _ in range(36):
        GuideUsage.objects.create(user=other, prompt_tokens=10, completion_tokens=5)

    api_client.force_authenticate(user=student_user)
    response = post_analyze(api_client)

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert 'resting' in response.data['error']['message']


@pytest.mark.django_db
def test_analyze_returns_validated_structure_and_saves_usage(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    response = post_analyze(api_client)

    assert response.status_code == status.HTTP_200_OK

    data = response.data
    assert isinstance(data['summary'], str) and data['summary']
    assert [item['name'] for item in data['dimensions']] == [
        'Clarity', 'Structure', 'Vocabulary', 'Confidence', 'Audience awareness',
    ]
    assert all(1 <= item['score'] <= 5 for item in data['dimensions'])
    assert len(data['questions']) == 3
    assert len(data['pitch']['points']) == 3

    usage = GuideUsage.objects.get(user=student_user)
    assert usage.prompt_tokens == 200
    assert usage.completion_tokens == 90


@pytest.mark.django_db
def test_feedback_returns_validated_structure_and_saves_usage(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    response = post_feedback(api_client)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['rewrites']) == 3
    assert response.data['overall']
    assert GuideUsage.objects.count() == 1


@pytest.mark.django_db
def test_analyze_strips_code_fence(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    fenced = f'```json\n{json.dumps(ANALYZE_REPLY)}\n```'
    response = call_api(fake_urlopen(fenced), ANALYZE_URL, api_client, ANALYZE_PAYLOAD)
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_invalid_json_twice_returns_502(api_client, student_user):
    calls = []

    def counting(req, timeout=None):
        calls.append(req)
        return fake_urlopen('not json')({'data': 'x'})

    api_client.force_authenticate(user=student_user)
    with openrouter(counting):
        response = api_client.post(ANALYZE_URL, ANALYZE_PAYLOAD, format='json')

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert len(calls) == 2
    assert 'not json' not in json.dumps(response.data)


@pytest.mark.django_db
def test_wrong_shape_twice_returns_502(api_client, student_user):
    bad = json.dumps({'summary': 'fine', 'dimensions': []})
    api_client.force_authenticate(user=student_user)
    response = call_api(fake_urlopen(bad), ANALYZE_URL, api_client, ANALYZE_PAYLOAD)
    assert response.status_code == status.HTTP_502_BAD_GATEWAY


@pytest.mark.django_db
def test_shuffled_dimensions_are_sorted_into_order(api_client, student_user):
    reply = copy.deepcopy(ANALYZE_REPLY)
    reply['dimensions'] = list(reversed(reply['dimensions']))

    api_client.force_authenticate(user=student_user)
    response = call_api(fake_urlopen(json.dumps(reply)), ANALYZE_URL, api_client, ANALYZE_PAYLOAD)

    assert response.status_code == status.HTTP_200_OK
    assert [item['name'] for item in response.data['dimensions']] == [
        'Clarity', 'Structure', 'Vocabulary', 'Confidence', 'Audience awareness',
    ]


@pytest.mark.django_db
def test_four_gaps_are_cut_to_three(api_client, student_user):
    reply = copy.deepcopy(ANALYZE_REPLY)
    reply['gaps'] = ANALYZE_REPLY['gaps'] + ['You never name the client']

    api_client.force_authenticate(user=student_user)
    response = call_api(fake_urlopen(json.dumps(reply)), ANALYZE_URL, api_client, ANALYZE_PAYLOAD)

    assert response.status_code == status.HTTP_200_OK
    assert response.data['gaps'] == ANALYZE_REPLY['gaps']


@pytest.mark.django_db
def test_two_questions_still_fail(api_client, student_user):
    reply = copy.deepcopy(ANALYZE_REPLY)
    reply['questions'] = ANALYZE_REPLY['questions'][:2]

    api_client.force_authenticate(user=student_user)
    response = call_api(fake_urlopen(json.dumps(reply)), ANALYZE_URL, api_client, ANALYZE_PAYLOAD)

    assert response.status_code == status.HTTP_502_BAD_GATEWAY


@pytest.mark.django_db
def test_user_text_never_appears_in_the_system_message(api_client, student_user):
    captured = {}

    def capture(req, timeout=None):
        captured['payload'] = json.loads(req.data.decode('utf-8'))
        return fake_urlopen(json.dumps(ANALYZE_REPLY))({'data': 'x'})

    api_client.force_authenticate(user=student_user)
    with openrouter(capture):
        api_client.post(ANALYZE_URL, ANALYZE_PAYLOAD, format='json')

    messages = captured['payload']['messages']
    system = messages[0]['content']
    assert messages[0]['role'] == 'system'
    assert 'pharmacy in Aba' not in system
    assert 'Lagos' not in system
    assert 'SpeakPro' in system
    assert ANALYZE_PAYLOAD['project'] in messages[1]['content']


@pytest.mark.django_db
def test_upstream_failure_returns_502_without_upstream_text(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    with openrouter(MagicMock(side_effect=URLError('connection refused'))):
        response = api_client.post(ANALYZE_URL, ANALYZE_PAYLOAD, format='json')

    assert response.status_code == status.HTTP_502_BAD_GATEWAY
    assert 'connection refused' not in json.dumps(response.data)
    assert 'sk-test' not in json.dumps(response.data)


@pytest.mark.django_db
def test_max_token_override_does_not_leak_into_other_calls(api_client, student_user):
    api_client.force_authenticate(user=student_user)
    seen = {}

    def capture(req, timeout=None):
        seen['max_tokens'] = json.loads(req.data.decode('utf-8'))['max_tokens']
        return fake_urlopen(json.dumps(ANALYZE_REPLY))({'data': 'x'})

    with openrouter(capture):
        api_client.post(ANALYZE_URL, ANALYZE_PAYLOAD, format='json')

    assert seen['max_tokens'] == 1200

    import apps.guide.views as guide_views
    assert guide_views.get_max_tokens() == 500
