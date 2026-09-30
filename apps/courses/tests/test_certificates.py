import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.careers.models import Career
from apps.courses.models import Course, Lesson, Enrollment, LessonProgress, Certificate


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def career(db):
    return Career.objects.create(
        slug='cyber',
        name='Cybersecurity',
        icon='X',
        tag='Fast growing',
        color='#FF6B6B',
        description='Protect systems from attacks.',
        order=2,
        is_active=True,
    )


@pytest.fixture
def student(db):
    return User.objects.create_user(
        username='ada',
        email='ada@example.com',
        password='pw12345678',
        first_name='Ada',
        last_name='Lovelace',
    )


@pytest.fixture
def other_student(db):
    return User.objects.create_user(
        username='bob',
        email='bob@example.com',
        password='pw12345678',
        first_name='Bob',
        last_name='Smith',
    )


@pytest.fixture
def reviewed_course(career):
    course = Course.objects.create(
        career=career,
        title='Network Security Fundamentals',
        description='Core network security concepts.',
        module_number=1,
        duration_minutes=95,
        order=1,
        is_published=True,
        content_reviewed=True,
    )

    Lesson.objects.create(
        course=course,
        title='Routing',
        order=1,
        duration_minutes=45,
        is_published=True,
        quiz_question='Which layer routes?',
        quiz_options=['Data Link', 'Network'],
        quiz_correct_index=1,
        quiz_feedback='The Network Layer routes.',
    )
    Lesson.objects.create(
        course=course,
        title='Firewalls',
        order=2,
        duration_minutes=50,
        is_published=True,
        quiz_question='What is a DMZ?',
        quiz_options=['Isolated host zone', 'Backup router'],
        quiz_correct_index=0,
        quiz_feedback='A DMZ isolates public services.',
    )

    return course


@pytest.fixture
def enrollment(student, reviewed_course):
    return Enrollment.objects.create(student=student, course=reviewed_course)


def complete_all(enrollment, correct=True, skip_quizzes=False):
    for lesson in enrollment.course.lessons.filter(is_published=True):
        progress = LessonProgress.objects.create(enrollment=enrollment, lesson=lesson)
        if lesson.has_quiz and not skip_quizzes:
            index = lesson.quiz_correct_index if correct else (lesson.quiz_correct_index + 1) % 2
            progress.submit_quiz(index)
        else:
            progress.mark_complete()
    enrollment.refresh_from_db()
    return enrollment


def issue_url(course):
    return f'/api/courses/{course.id}/certificate/'


def test_unreviewed_course_is_refused(api_client, student, career, enrollment, reviewed_course):
    reviewed_course.content_reviewed = False
    reviewed_course.save(update_fields=['content_reviewed'])
    complete_all(enrollment)

    api_client.force_authenticate(student)
    response = api_client.post(issue_url(reviewed_course), {}, format='json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Certificate.objects.count() == 0
    assert any('reviewed' in b for b in response.data['error']['blockers'])


def test_incomplete_course_is_refused(api_client, student, reviewed_course, enrollment):
    LessonProgress.objects.create(
        enrollment=enrollment,
        lesson=reviewed_course.lessons.first(),
    )

    api_client.force_authenticate(student)
    response = api_client.post(issue_url(reviewed_course), {}, format='json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Certificate.objects.count() == 0
    assert any('Complete all' in b for b in response.data['error']['blockers'])


def test_low_score_is_refused(api_client, student, reviewed_course, enrollment):
    complete_all(enrollment, correct=False)

    api_client.force_authenticate(student)
    response = api_client.post(issue_url(reviewed_course), {}, format='json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Certificate.objects.count() == 0
    assert any('average quiz score' in b for b in response.data['error']['blockers'])


def test_eligible_student_issues_certificate(api_client, student, reviewed_course, enrollment):
    complete_all(enrollment)

    api_client.force_authenticate(student)
    response = api_client.post(issue_url(reviewed_course), {}, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    assert Certificate.objects.count() == 1

    certificate = Certificate.objects.get()
    assert certificate.user == student
    assert certificate.course == reviewed_course
    assert certificate.score == 100
    assert len(certificate.code) == 16


def test_skipped_quizzes_are_blocked(api_client, student, reviewed_course, enrollment):
    complete_all(enrollment, skip_quizzes=True)

    api_client.force_authenticate(student)
    response = api_client.post(issue_url(reviewed_course), {}, format='json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Certificate.objects.count() == 0
    assert any('2 course quizzes' in b for b in response.data['error']['blockers'])


def test_retry_does_not_raise_the_score(api_client, student, reviewed_course, enrollment):
    lessons = list(reviewed_course.lessons.filter(is_published=True))
    for lesson in lessons:
        progress = LessonProgress.objects.create(enrollment=enrollment, lesson=lesson)
        progress.submit_quiz(lesson.quiz_correct_index)
    enrollment.refresh_from_db()

    assert enrollment.quiz_average() == 100

    first = enrollment.lesson_progress.get(lesson=lessons[0])
    first.submit_quiz((lessons[0].quiz_correct_index + 1) % 2)
    enrollment.refresh_from_db()

    assert first.quiz_correct is False
    assert first.first_quiz_correct is True
    assert enrollment.quiz_average() == 100

    api_client.force_authenticate(student)
    response = api_client.post(issue_url(reviewed_course), {}, format='json')

    assert response.status_code == status.HTTP_201_CREATED
    assert Certificate.objects.get().score == 100


def test_one_correct_out_of_four_is_blocked(api_client, student, career):
    course = Course.objects.create(
        career=career, title='Four Question Course', description='Four quizzes.',
        module_number=2, order=1, is_published=True, content_reviewed=True,
    )
    for order in range(1, 5):
        Lesson.objects.create(
            course=course, title=f'Lesson {order}', order=order,
            duration_minutes=10, is_published=True,
            quiz_question=f'Question {order}',
            quiz_options=['Wrong', 'Right'],
            quiz_correct_index=1,
            quiz_feedback=f'Feedback {order}',
        )

    enrollment = Enrollment.objects.create(student=student, course=course)
    lessons = list(course.lessons.filter(is_published=True))
    for lesson in lessons:
        progress = LessonProgress.objects.create(enrollment=enrollment, lesson=lesson)
        progress.submit_quiz(1 if lesson is lessons[0] else 0)
    enrollment.refresh_from_db()

    assert enrollment.quiz_average() == 25

    api_client.force_authenticate(student)
    response = api_client.post(issue_url(course), {}, format='json')

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert Certificate.objects.count() == 0
    assert any('25%' in b for b in response.data['error']['blockers'])


def test_issue_is_idempotent(api_client, student, reviewed_course, enrollment):
    complete_all(enrollment)

    api_client.force_authenticate(student)
    first = api_client.post(issue_url(reviewed_course), {}, format='json')
    second = api_client.post(issue_url(reviewed_course), {}, format='json')

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_200_OK
    assert Certificate.objects.count() == 1
    assert first.data['data']['code'] == second.data['data']['code']


def test_issue_requires_login(api_client, db, reviewed_course):
    response = api_client.post(issue_url(reviewed_course), {}, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_list_returns_only_my_certificates(
    api_client, student, other_student, reviewed_course, enrollment
):
    complete_all(enrollment)
    api_client.force_authenticate(student)
    api_client.post(issue_url(reviewed_course), {}, format='json')

    Certificate.objects.create(user=other_student, course=reviewed_course, score=90)

    api_client.force_authenticate(student)
    response = api_client.get('/api/certificates/')

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['data']) == 1
    assert response.data['data'][0]['holder_name'] == 'Ada Lovelace'


def test_owner_can_download_pdf(api_client, student, reviewed_course, enrollment):
    complete_all(enrollment)
    api_client.force_authenticate(student)
    api_client.post(issue_url(reviewed_course), {}, format='json')
    code = Certificate.objects.get().code

    api_client.force_authenticate(student)
    response = api_client.get(f'/api/certificates/{code}/pdf/')

    assert response.status_code == status.HTTP_200_OK
    assert response['Content-Type'] == 'application/pdf'
    assert response.content[:5] == b'%PDF-'


def test_other_student_cannot_download_pdf(
    api_client, student, other_student, reviewed_course, enrollment
):
    complete_all(enrollment)
    api_client.force_authenticate(student)
    api_client.post(issue_url(reviewed_course), {}, format='json')
    code = Certificate.objects.get().code

    api_client.force_authenticate(other_student)
    response = api_client.get(f'/api/certificates/{code}/pdf/')

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_pdf_requires_login(api_client, db, student, reviewed_course, enrollment):
    complete_all(enrollment)
    api_client.force_authenticate(student)
    api_client.post(issue_url(reviewed_course), {}, format='json')
    code = Certificate.objects.get().code

    api_client.logout()
    response = api_client.get(f'/api/certificates/{code}/pdf/')

    assert response.status_code in (
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_403_FORBIDDEN,
    )


def test_verify_is_public_and_leaks_nothing_private(
    api_client, db, student, reviewed_course, enrollment
):
    complete_all(enrollment)
    api_client.force_authenticate(student)
    api_client.post(issue_url(reviewed_course), {}, format='json')
    code = Certificate.objects.get().code

    api_client.logout()
    response = api_client.get(f'/api/certificates/verify/{code}/')

    assert response.status_code == status.HTTP_200_OK

    data = response.data['data']
    assert data['holder_name'] == 'Ada Lovelace'
    assert data['course_title'] == 'Network Security Fundamentals'
    assert data['valid'] is True

    body = response.content.decode()
    assert student.email not in body
    assert 'ada@example.com' not in body
    assert student.username not in body
    for forbidden in ('email', 'username', 'user_id', 'password'):
        assert forbidden not in data


def test_verify_unknown_code_is_404(api_client, db):
    response = api_client.get('/api/certificates/verify/NOPE/')
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_mark_reviewed_sets_flag(reviewed_course):
    from django.core.management import call_command

    reviewed_course.content_reviewed = False
    reviewed_course.save(update_fields=['content_reviewed'])

    call_command('mark_reviewed', str(reviewed_course.id))

    reviewed_course.refresh_from_db()
    assert reviewed_course.content_reviewed is True
