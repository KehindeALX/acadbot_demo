import json
import os
from urllib.error import HTTPError

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.careers.models import Career
from apps.courses.models import Course, Lesson


def make_lesson(order=1, correct_index=0):
    return {
        'title': f'Lesson {order}',
        'content_html': f'<p>Body of lesson {order}.</p>',
        'order': order,
        'duration_minutes': 45,
        'quiz_question': f'Question {order}?',
        'quiz_options': ['A', 'B', 'C', 'D'],
        'quiz_correct_index': correct_index,
        'quiz_feedback': 'Because A is correct.',
    }


def make_course(reviewed=None, module_number=1, order=1, title='A Drafted Course'):
    course = {
        'title': title,
        'description': 'A short description.',
        'module_number': module_number,
        'duration_minutes': 180,
        'order': order,
        'lessons': [make_lesson(index) for index in range(1, 5)],
    }
    if reviewed is not None:
        course['reviewed'] = reviewed
    return course


@pytest.fixture
def career(db):
    return Career.objects.create(
        slug='data', name='Data Analysis', icon='📊', tag='Numbers',
        color='#1f2937', order=1,
    )


@pytest.fixture
def content_dir(tmp_path, settings, monkeypatch):
    import apps.courses.drafting as drafting

    target = tmp_path / 'courses'
    target.mkdir()
    monkeypatch.setattr(drafting, 'CONTENT_COURSES_DIR', str(target))
    return target


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setattr(
        'apps.courses.management.commands.draft_course.api_credentials',
        lambda: ('sk-test', 'vendor/some-model'),
    )


def fake_openrouter(reply):
    return lambda api_key, model, messages: (reply, {'completion_tokens': 10})


def run_draft(slug, reply):
    from unittest.mock import patch

    with patch('apps.guide.views.call_openrouter', fake_openrouter(reply)):
        call_command('draft_course', slug)


@pytest.mark.django_db
def test_valid_draft_writes_file(career, content_dir, credentials):
    run_draft('data', json.dumps(make_course()))

    path = content_dir / 'data.json'
    assert path.exists()

    written = json.loads(path.read_text(encoding='utf-8'))
    assert written['reviewed'] is False
    assert written['title'] == 'A Drafted Course'
    assert len(written['lessons']) == 4
    assert written['lessons'][0]['quiz_correct_index'] == 0
    assert Course.objects.count() == 0


@pytest.mark.django_db
def test_invalid_json_writes_nothing(career, content_dir):
    with pytest.raises(CommandError):
        run_draft('data', 'this is not json at all')

    assert not (content_dir / 'data.json').exists()
    assert os.listdir(content_dir) == []


@pytest.mark.django_db
def test_invalid_structure_is_not_written(career, content_dir):
    broken = make_course()
    broken['lessons'][1]['quiz_options'] = ['A', 'B']

    with pytest.raises(CommandError):
        run_draft('data', json.dumps(broken))

    assert not (content_dir / 'data.json').exists()


@pytest.mark.django_db
def test_bad_json_is_repaired_on_second_attempt(career, content_dir, credentials):
    from unittest.mock import patch

    good = json.dumps(make_course())
    replies = ['nope, not json', good]
    calls = []

    def fake_call(api_key, model, messages):
        calls.append(messages)
        return replies[len(calls) - 1], {'completion_tokens': 10}

    with patch('apps.guide.views.call_openrouter', fake_call):
        call_command('draft_course', 'data')

    assert len(calls) == 2
    assert 'failed validation' in calls[1][-1]['content']
    assert (content_dir / 'data.json').exists()


@pytest.mark.django_db
def test_rate_limit_stops_cleanly_without_writing(career, content_dir, credentials, monkeypatch):
    from unittest.mock import patch

    monkeypatch.setattr(
        'apps.courses.management.commands.draft_course.RATE_LIMIT_WAIT_SECONDS', 0,
    )

    def always_limited(api_key, model, messages):
        raise HTTPError('url', 429, 'Too Many Requests', {}, None)

    with patch('apps.guide.views.call_openrouter', always_limited):
        with pytest.raises(CommandError, match='rate limited'):
            call_command('draft_course', 'data')

    assert not (content_dir / 'data.json').exists()


@pytest.mark.django_db
def test_rate_limit_retries_twice(career, content_dir, credentials, monkeypatch):
    from unittest.mock import patch

    monkeypatch.setattr(
        'apps.courses.management.commands.draft_course.RATE_LIMIT_WAIT_SECONDS', 0,
    )

    attempts = []

    def limited_then_ok(api_key, model, messages):
        attempts.append(1)
        if len(attempts) <= 2:
            raise HTTPError('url', 429, 'Too Many Requests', {}, None)
        return json.dumps(make_course()), {'completion_tokens': 10}

    with patch('apps.guide.views.call_openrouter', limited_then_ok):
        call_command('draft_course', 'data')

    assert len(attempts) == 3
    assert (content_dir / 'data.json').exists()


@pytest.mark.django_db
def test_unknown_career_fails_cleanly(content_dir):
    with pytest.raises(CommandError, match='No active career'):
        call_command('draft_course', 'does-not-exist')


@pytest.mark.django_db
def test_loader_skips_unreviewed_files(career, content_dir):
    (content_dir / 'data.json').write_text(json.dumps(make_course(reviewed=False)), encoding='utf-8')

    call_command('load_reviewed_courses')

    assert Course.objects.count() == 0


@pytest.mark.django_db
def test_loader_loads_reviewed_file(career, content_dir):
    (content_dir / 'data.json').write_text(json.dumps(make_course(reviewed=True)), encoding='utf-8')

    call_command('load_reviewed_courses')

    course = Course.objects.get()
    assert course.career == career
    assert course.title == 'A Drafted Course'
    assert course.is_published is True
    assert course.lessons.count() == 4

    lesson = course.lessons.order_by('order').first()
    assert lesson.quiz_options == ['A', 'B', 'C', 'D']
    assert lesson.quiz_correct_index == 0
    assert lesson.quiz_feedback == 'Because A is correct.'
    assert lesson.is_published is True


@pytest.mark.django_db
def test_loader_is_idempotent(career, content_dir):
    (content_dir / 'data.json').write_text(json.dumps(make_course(reviewed=True)), encoding='utf-8')

    call_command('load_reviewed_courses')
    call_command('load_reviewed_courses')

    assert Course.objects.count() == 1
    assert Lesson.objects.count() == 4


@pytest.mark.django_db
def test_loader_updates_changed_content(career, content_dir):
    (content_dir / 'data.json').write_text(json.dumps(make_course(reviewed=True)), encoding='utf-8')
    call_command('load_reviewed_courses')

    revised = make_course(reviewed=True, title='A Revised Course')
    revised['lessons'][0]['content_html'] = '<p>Rewritten body.</p>'
    (content_dir / 'data.json').write_text(json.dumps(revised), encoding='utf-8')
    call_command('load_reviewed_courses')

    course = Course.objects.get()
    assert course.title == 'A Revised Course'
    assert course.lessons.count() == 4
    assert course.lessons.order_by('order').first().content_html == '<p>Rewritten body.</p>'


@pytest.mark.django_db
def test_loader_reports_counts_and_waiting(career, content_dir, capsys):
    (content_dir / 'data.json').write_text(json.dumps(make_course(reviewed=True)), encoding='utf-8')
    (content_dir / 'software.json').write_text(json.dumps(make_course(reviewed=False)), encoding='utf-8')

    call_command('load_reviewed_courses')

    out = capsys.readouterr().out
    assert 'Created: 1' in out
    assert 'software.json' in out
    assert 'waiting for review' in out
