"""
End-to-end test for the student enrollment flow:
Register -> Login -> Enroll in Course -> Verify Enrollment
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.careers.models import Career
from apps.courses.models import Course, Lesson, Enrollment


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def cyber_career(db):
    """Create a Cybersecurity career for testing."""
    return Career.objects.create(
        slug='cyber',
        name='Cybersecurity',
        icon='🔐',
        tag='Fast growing',
        color='#FF6B6B',
        description='Protect systems, networks, and data from digital attacks.',
        order=2,
        is_active=True,
    )


@pytest.fixture
def ai_career(db):
    """Create an AI & ML career for testing."""
    return Career.objects.create(
        slug='ai',
        name='AI & Machine Learning',
        icon='🤖',
        tag='Future-proof',
        color='#9B59B6',
        description='Build intelligent systems with machine learning and deep learning.',
        order=4,
        is_active=True,
    )


@pytest.fixture
def cyber_course(cyber_career):
    """Create a Cybersecurity course with lessons including quizzes."""
    course = Course.objects.create(
        career=cyber_career,
        title='Network Security Fundamentals',
        description='Master the core concepts of network security.',
        module_number=1,
        duration_minutes=180,
        order=1,
        is_published=True,
    )

    # Lesson 1: with quiz
    Lesson.objects.create(
        course=course,
        title='Introduction to Network Security',
        content_html='<p>Network security fundamentals...</p>',
        order=1,
        duration_minutes=45,
        is_published=True,
        quiz_question='Which layer handles routing?',
        quiz_options=['Physical', 'Data Link', 'Network', 'Transport'],
        quiz_correct_index=2,
        quiz_feedback='The Network Layer (Layer 3) handles routing.',
    )

    # Lesson 2: with quiz
    Lesson.objects.create(
        course=course,
        title='Firewalls and Segmentation',
        content_html='<p>Firewall concepts...</p>',
        order=2,
        duration_minutes=50,
        is_published=True,
        quiz_question='What is a DMZ for?',
        quiz_options=['Store databases', 'Host public services isolated', 'Connect branches', 'Guest WiFi'],
        quiz_correct_index=1,
        quiz_feedback='DMZ hosts public-facing services isolated from internal network.',
    )

    # Lesson 3: no quiz
    Lesson.objects.create(
        course=course,
        title='Intrusion Detection Systems',
        content_html='<p>IDS/IPS concepts...</p>',
        order=3,
        duration_minutes=45,
        is_published=True,
    )

    return course


@pytest.fixture
def ai_course(ai_career):
    """Create an AI/ML course with lessons including quizzes."""
    course = Course.objects.create(
        career=ai_career,
        title='Python for Machine Learning',
        description='Build a rock-solid foundation in Python for ML.',
        module_number=1,
        duration_minutes=180,
        order=1,
        is_published=True,
    )

    # Lesson 1: with quiz
    Lesson.objects.create(
        course=course,
        title='NumPy Fundamentals',
        content_html='<p>NumPy basics...</p>',
        order=1,
        duration_minutes=45,
        is_published=True,
        quiz_question='Broadcasting (3,4) with (4,)?',
        quiz_options=['Error', 'Added to each row', 'Added to each column', 'Added to each column (transposed)'],
        quiz_correct_index=1,
        quiz_feedback='Broadcasting aligns right-to-left: (4,) -> (1,4) broadcasts across rows.',
    )

    # Lesson 2: no quiz
    Lesson.objects.create(
        course=course,
        title='Pandas Data Manipulation',
        content_html='<p>Pandas basics...</p>',
        order=2,
        duration_minutes=50,
        is_published=True,
    )

    # Lesson 3: with quiz
    Lesson.objects.create(
        course=course,
        title='Scikit-learn Introduction',
        content_html='<p>Sklearn basics...</p>',
        order=3,
        duration_minutes=45,
        is_published=True,
        quiz_question='What does a Pipeline do?',
        quiz_options=[
            'Chains estimators for cross-validation',
            'Auto-selects hyperparameters',
            'Visualizes decision boundaries',
            'Parallelizes training'
        ],
        quiz_correct_index=0,
        quiz_feedback='Pipeline chains transformers + estimator, prevents data leakage in CV.',
    )

    return course


@pytest.mark.django_db
class TestEnrollmentFlow:
    """Test the full student enrollment flow."""

    REGISTER_URL = '/api/auth/register/'
    LOGIN_URL = '/api/auth/login/'
    ME_URL = '/api/auth/me/'
    COURSES_URL = '/api/courses/'
    ENROLL_URL = '/api/courses/{course_id}/enroll/'
    ENROLLMENTS_URL = '/api/courses/enrollments/'

    def valid_student_payload(self, **overrides):
        payload = {
            'username': 'teststudent',
            'email': 'teststudent@example.com',
            'password': 'TestPass123',
            'password_confirm': 'TestPass123',
            'role': User.Role.STUDENT,
            'first_name': 'Test',
            'last_name': 'Student',
        }
        payload.update(overrides)
        return payload

    def test_full_enrollment_flow(self, api_client, cyber_course, ai_course):
        """
        Complete flow:
        1. Register a student
        2. Log in
        3. Verify session works via /me
        4. List available courses
        5. Enroll in a Cybersecurity course
        6. Verify enrollment created with ACTIVE status
        7. Verify enrollment appears in enrollments list
        8. Enroll in an AI/ML course
        9. Verify both enrollments exist
        """

        # ============================================================
        # Step 1: Register a student
        # ============================================================
        register_payload = self.valid_student_payload(
            username='flowstudent',
            email='flowstudent@example.com',
        )
        register_response = api_client.post(self.REGISTER_URL, register_payload, format='json')

        assert register_response.status_code == status.HTTP_201_CREATED, (
            f'Registration failed: {register_response.data}'
        )
        assert register_response.data['success'] is True
        assert register_response.data['data']['email'] == 'flowstudent@example.com'
        assert register_response.data['data']['role'] == User.Role.STUDENT

        # Verify user and profile created
        user = User.objects.get(email='flowstudent@example.com')
        assert user.role == User.Role.STUDENT
        assert user.check_password('TestPass123')
        assert hasattr(user, 'student_profile')

        # ============================================================
        # Step 2: Log in
        # ============================================================
        login_response = api_client.post(
            self.LOGIN_URL,
            {'email': 'flowstudent@example.com', 'password': 'TestPass123'},
            format='json',
        )

        assert login_response.status_code == status.HTTP_200_OK, (
            f'Login failed: {login_response.data}'
        )
        assert login_response.data['success'] is True
        assert login_response.data['data']['email'] == 'flowstudent@example.com'

        # ============================================================
        # Step 3: Verify session works via /me
        # ============================================================
        me_response = api_client.get(self.ME_URL)
        assert me_response.status_code == status.HTTP_200_OK, (
            f'/me failed: {me_response.data}'
        )
        assert me_response.data['success'] is True
        assert me_response.data['data']['email'] == 'flowstudent@example.com'
        assert me_response.data['data']['role'] == User.Role.STUDENT
        assert me_response.data['data']['profile'] is not None
        assert me_response.data['data']['profile']['onboarding_complete'] is False

        # ============================================================
        # Step 4: List available courses (paginated DRF format)
        # ============================================================
        courses_response = api_client.get(self.COURSES_URL)
        assert courses_response.status_code == status.HTTP_200_OK
        # Course list returns standard DRF paginated format
        courses_data = courses_response.data['results']
        assert len(courses_data) == 2  # Our two test courses

        # Verify course structure
        cyber_course_data = next(c for c in courses_data if c['career']['slug'] == 'cyber')
        ai_course_data = next(c for c in courses_data if c['career']['slug'] == 'ai')

        assert cyber_course_data['title'] == 'Network Security Fundamentals'
        assert cyber_course_data['module_number'] == 1
        assert cyber_course_data['lessons_count'] == 3
        assert cyber_course_data['is_published'] is True

        assert ai_course_data['title'] == 'Python for Machine Learning'
        assert ai_course_data['module_number'] == 1
        assert ai_course_data['lessons_count'] == 3
        assert ai_course_data['is_published'] is True

        # ============================================================
        # Step 5: Enroll in Cybersecurity course
        # ============================================================
        enroll_url = self.ENROLL_URL.format(course_id=cyber_course.id)
        enroll_response = api_client.post(enroll_url, format='json')

        assert enroll_response.status_code == status.HTTP_201_CREATED, (
            f'Enrollment failed: {enroll_response.data}'
        )
        assert enroll_response.data['success'] is True
        assert enroll_response.data['message'] == 'Enrolled successfully'

        enroll_data = enroll_response.data['data']
        assert enroll_data['course']['id'] == cyber_course.id
        assert enroll_data['course']['title'] == 'Network Security Fundamentals'
        assert enroll_data['status'] == Enrollment.Status.ACTIVE
        assert enroll_data['progress_percent'] == 0
        assert 'enrolled_at' in enroll_data

        # Verify enrollment in database
        enrollment = Enrollment.objects.get(student=user, course=cyber_course)
        assert enrollment.status == Enrollment.Status.ACTIVE
        assert enrollment.progress_percent == 0

        # ============================================================
        # Step 6: Verify enrollment appears in enrollments list (paginated DRF format)
        # ============================================================
        enrollments_response = api_client.get(self.ENROLLMENTS_URL)
        assert enrollments_response.status_code == status.HTTP_200_OK
        # Enrollment list returns standard DRF paginated format
        enrollments_data = enrollments_response.data['results']
        assert len(enrollments_data) == 1
        assert enrollments_data[0]['id'] == enrollment.id
        assert enrollments_data[0]['course']['id'] == cyber_course.id
        assert enrollments_data[0]['status'] == Enrollment.Status.ACTIVE

        # ============================================================
        # Step 7: Enroll in AI/ML course
        # ============================================================
        enroll_url_2 = self.ENROLL_URL.format(course_id=ai_course.id)
        enroll_response_2 = api_client.post(enroll_url_2, format='json')

        assert enroll_response_2.status_code == status.HTTP_201_CREATED
        assert enroll_response_2.data['success'] is True
        assert enroll_response_2.data['data']['course']['id'] == ai_course.id
        assert enroll_response_2.data['data']['status'] == Enrollment.Status.ACTIVE

        # ============================================================
        # Step 8: Verify both enrollments exist
        # ============================================================
        enrollments_response_2 = api_client.get(self.ENROLLMENTS_URL)
        assert enrollments_response_2.status_code == status.HTTP_200_OK

        enrollments_data_2 = enrollments_response_2.data['results']
        assert len(enrollments_data_2) == 2

        course_ids = {e['course']['id'] for e in enrollments_data_2}
        assert course_ids == {cyber_course.id, ai_course.id}

        # Both should be ACTIVE
        for e in enrollments_data_2:
            assert e['status'] == Enrollment.Status.ACTIVE

    def test_enrollment_idempotent(self, api_client, cyber_course):
        """
        Re-enrolling in the same course should not create duplicate enrollment.
        Should return 200 OK with 'Re-enrolled successfully' message.
        """
        # Register and login
        api_client.post(self.REGISTER_URL, self.valid_student_payload(), format='json')
        api_client.post(self.LOGIN_URL, {'email': 'teststudent@example.com', 'password': 'TestPass123'}, format='json')

        # First enrollment
        enroll_url = self.ENROLL_URL.format(course_id=cyber_course.id)
        response1 = api_client.post(enroll_url, format='json')
        assert response1.status_code == status.HTTP_201_CREATED
        assert response1.data['message'] == 'Enrolled successfully'

        # Second enrollment (same course)
        response2 = api_client.post(enroll_url, format='json')
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data['message'] == 'Re-enrolled successfully'
        assert response2.data['data']['id'] == response1.data['data']['id']

        # Only one enrollment in DB
        assert Enrollment.objects.filter(student__email='teststudent@example.com', course=cyber_course).count() == 1

    def test_enrollment_re_activates_dropped(self, api_client, cyber_course):
        """
        If enrollment was DROPPED, re-enrolling should reactivate it.
        """
        # Register and login
        api_client.post(self.REGISTER_URL, self.valid_student_payload(), format='json')
        api_client.post(self.LOGIN_URL, {'email': 'teststudent@example.com', 'password': 'TestPass123'}, format='json')

        # Create a DROPPED enrollment directly
        user = User.objects.get(email='teststudent@example.com')
        enrollment = Enrollment.objects.create(
            student=user,
            course=cyber_course,
            status=Enrollment.Status.DROPPED,
        )

        # Re-enroll via API
        enroll_url = self.ENROLL_URL.format(course_id=cyber_course.id)
        response = api_client.post(enroll_url, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Re-enrolled successfully'

        enrollment.refresh_from_db()
        assert enrollment.status == Enrollment.Status.ACTIVE

    def test_course_detail_includes_lessons(self, api_client, cyber_course):
        """Course detail endpoint should include lessons with quiz info."""
        detail_url = f'{self.COURSES_URL}{cyber_course.id}/'
        response = api_client.get(detail_url)

        assert response.status_code == status.HTTP_200_OK
        # Course detail returns direct object (no success wrapper)
        course_data = response.data
        assert 'lessons' in course_data
        assert len(course_data['lessons']) == 3

        # Check lesson structure includes quiz fields
        lesson1 = course_data['lessons'][0]
        assert lesson1['title'] == 'Introduction to Network Security'
        assert lesson1['has_quiz'] is True
        assert lesson1['quiz_question'] == 'Which layer handles routing?'
        assert lesson1['quiz_options'] == ['Physical', 'Data Link', 'Network', 'Transport']
        # quiz_correct_index and quiz_feedback NOT included in list view (only detail)

        lesson3 = course_data['lessons'][2]
        assert lesson3['has_quiz'] is False

    def test_lesson_detail_includes_quiz_answer(self, api_client, cyber_course):
        """Lesson detail should include quiz_correct_index and quiz_feedback."""
        lesson = cyber_course.lessons.get(order=1)  # Has quiz
        detail_url = f'/api/courses/lessons/{lesson.id}/'

        # Need to be authenticated as student
        api_client.post(self.REGISTER_URL, self.valid_student_payload(), format='json')
        api_client.post(self.LOGIN_URL, {'email': 'teststudent@example.com', 'password': 'TestPass123'}, format='json')

        response = api_client.get(detail_url)
        assert response.status_code == status.HTTP_200_OK

        # Lesson detail returns direct object (no success/data wrapper)
        lesson_data = response.data
        assert lesson_data['quiz_correct_index'] == 2
        assert lesson_data['quiz_feedback'] == 'The Network Layer (Layer 3) handles routing.'

    def test_unauthenticated_cannot_enroll(self, api_client, cyber_course):
        """Anonymous users cannot enroll."""
        enroll_url = self.ENROLL_URL.format(course_id=cyber_course.id)
        response = api_client.post(enroll_url, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_view_enrollments(self, api_client):
        """Anonymous users cannot view enrollments list."""
        response = api_client.get(self.ENROLLMENTS_URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_course_filter_by_career(self, api_client, cyber_course, ai_course):
        """Courses can be filtered by career slug."""
        response = api_client.get(f'{self.COURSES_URL}?career=cyber')
        assert response.status_code == status.HTTP_200_OK
        # Paginated DRF format
        data = response.data['results']
        assert len(data) == 1
        assert data[0]['career']['slug'] == 'cyber'

        response = api_client.get(f'{self.COURSES_URL}?career=ai')
        assert response.status_code == status.HTTP_200_OK
        data = response.data['results']
        assert len(data) == 1
        assert data[0]['career']['slug'] == 'ai'