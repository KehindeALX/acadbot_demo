"""
Models for the Courses app - courses, lessons, enrollment, progress tracking.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import secrets


class Course(models.Model):

    career = models.ForeignKey(
        'careers.Career',
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name=_('career'),
    )
    title = models.CharField(_('title'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    module_number = models.PositiveIntegerField(_('module number'), default=1)
    duration_minutes = models.PositiveIntegerField(_('duration (minutes)'), default=0)
    order = models.PositiveIntegerField(_('order'), default=0)
    is_published = models.BooleanField(_('published'), default=True)
    content_reviewed = models.BooleanField(_('content reviewed'), default=False)
    thumbnail = models.ImageField(_('thumbnail'), upload_to='course_thumbnails/', blank=True, null=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'courses'
        verbose_name = _('course')
        verbose_name_plural = _('courses')
        ordering = ['career', 'module_number', 'order']
        unique_together = ['career', 'module_number', 'order']

    def __str__(self):
        return f'{self.career.name} - Module {self.module_number}: {self.title}'

    @property
    def lessons_count(self):
        return self.lessons.count()

    @property
    def total_duration_minutes(self):
        return self.lessons.aggregate(total=models.Sum('duration_minutes'))['total'] or 0


class Lesson(models.Model):

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name=_('course'),
    )
    title = models.CharField(_('title'), max_length=200)
    content_html = models.TextField(_('content (HTML)'), blank=True)
    order = models.PositiveIntegerField(_('order'), default=0)
    duration_minutes = models.PositiveIntegerField(_('duration (minutes)'), default=0)
    is_published = models.BooleanField(_('published'), default=True)

    # Quiz fields
    quiz_question = models.TextField(_('quiz question'), blank=True)
    quiz_options = models.JSONField(_('quiz options'), default=list, blank=True)
    quiz_correct_index = models.PositiveIntegerField(_('quiz correct index'), null=True, blank=True)
    quiz_feedback = models.TextField(_('quiz feedback'), blank=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'lessons'
        verbose_name = _('lesson')
        verbose_name_plural = _('lessons')
        ordering = ['course', 'order']
        unique_together = ['course', 'order']

    def __str__(self):
        return f'{self.course.title} - Lesson {self.order}: {self.title}'

    @property
    def has_quiz(self):
        return bool(self.quiz_question and self.quiz_options)


class Enrollment(models.Model):

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        COMPLETED = 'COMPLETED', _('Completed')
        DROPPED = 'DROPPED', _('Dropped')

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name=_('student'),
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name=_('course'),
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    enrolled_at = models.DateTimeField(_('enrolled at'), auto_now_add=True)
    started_at = models.DateTimeField(_('started at'), null=True, blank=True)
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)
    progress_percent = models.PositiveIntegerField(_('progress percent'), default=0)
    last_accessed_at = models.DateTimeField(_('last accessed at'), null=True, blank=True)

    class Meta:
        db_table = 'enrollments'
        verbose_name = _('enrollment')
        verbose_name_plural = _('enrollments')
        ordering = ['-enrolled_at']
        unique_together = ['student', 'course']

    def __str__(self):
        return f'{self.student.email} - {self.course.title} ({self.get_status_display()})'

    def update_progress(self):
        """Update progress percentage based on completed lessons."""
        total_lessons = self.course.lessons.filter(is_published=True).count()
        if total_lessons == 0:
            self.progress_percent = 0
        else:
            completed_lessons = self.lesson_progress.filter(completed_at__isnull=False).count()
            self.progress_percent = int((completed_lessons / total_lessons) * 100)

        if self.progress_percent >= 100 and self.status == self.Status.ACTIVE:
            self.status = self.Status.COMPLETED
            from django.utils import timezone
            self.completed_at = timezone.now()

        self.save(update_fields=['progress_percent', 'status', 'completed_at'])

    def quiz_lessons(self):
        return [lesson for lesson in self.course.lessons.filter(is_published=True) if lesson.has_quiz]

    def quiz_average(self):
        lessons = self.quiz_lessons()
        if not lessons:
            return None
        answers = {
            lp.lesson_id: lp.first_quiz_correct
            for lp in self.lesson_progress.filter(lesson__in=lessons)
        }
        if any(answers.get(lesson.id) is None for lesson in lessons):
            return None
        correct = sum(1 for lesson in lessons if answers[lesson.id])
        return int((correct / len(lessons)) * 100)

    def unanswered_quiz_count(self):
        lessons = self.quiz_lessons()
        answered = set(
            self.lesson_progress.filter(
                lesson__in=lessons,
                first_quiz_correct__isnull=False,
            ).values_list('lesson_id', flat=True)
        )
        return len([lesson for lesson in lessons if lesson.id not in answered])

    def certificate_blockers(self):
        from django.conf import settings as django_settings

        blockers = []

        if not self.course.content_reviewed:
            blockers.append('This course has not been content reviewed yet.')

        total_lessons = self.course.lessons.filter(is_published=True).count()
        if total_lessons == 0:
            blockers.append('This course has no published lessons.')
        else:
            completed = self.lesson_progress.filter(
                completed_at__isnull=False,
                lesson__is_published=True,
            ).count()
            if completed < total_lessons:
                blockers.append(
                    f'Complete all {total_lessons} lessons first '
                    f'({completed} of {total_lessons} done).'
                )

        pass_mark = getattr(django_settings, 'CERT_PASS_MARK', 70)
        unanswered = self.unanswered_quiz_count()
        if unanswered:
            blockers.append(
                f'Answer the remaining {unanswered} course '
                f'{"quiz" if unanswered == 1 else "quizzes"} before claiming a certificate.'
            )

        score = self.quiz_average()
        if score is None:
            if not unanswered:
                blockers.append('Answer the course quizzes before claiming a certificate.')
        elif score < pass_mark:
            blockers.append(
                f'Your average quiz score is {score}%. '
                f'You need at least {pass_mark}%.'
            )

        return blockers


class LessonProgress(models.Model):

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='lesson_progress',
        verbose_name=_('enrollment'),
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='progress_records',
        verbose_name=_('lesson'),
    )
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)
    quiz_answered = models.PositiveIntegerField(_('quiz answered'), null=True, blank=True)
    quiz_correct = models.BooleanField(_('quiz correct'), null=True, blank=True)
    first_quiz_correct = models.BooleanField(_('first quiz correct'), null=True, blank=True)
    time_spent_minutes = models.PositiveIntegerField(_('time spent (minutes)'), default=0)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'lesson_progress'
        verbose_name = _('lesson progress')
        verbose_name_plural = _('lesson progress')
        unique_together = ['enrollment', 'lesson']

    def __str__(self):
        status = 'Completed' if self.completed_at else 'In Progress'
        return f'{self.enrollment.student.email} - {self.lesson.title} ({status})'

    def submit_quiz(self, answer_index):
        """Submit quiz answer and return result."""
        self.quiz_answered = answer_index
        self.quiz_correct = (answer_index == self.lesson.quiz_correct_index)

        if self.first_quiz_correct is None:
            self.first_quiz_correct = self.quiz_correct

        if not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()

        self.save(update_fields=[
            'quiz_answered', 'quiz_correct', 'first_quiz_correct',
            'completed_at', 'updated_at',
        ])

        # Update enrollment progress
        self.enrollment.update_progress()

        return {
            'correct': self.quiz_correct,
            'correct_index': self.lesson.quiz_correct_index,
            'feedback': self.lesson.quiz_feedback,
        }

    def mark_complete(self):
        """Mark lesson as complete."""
        if not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
            self.save(update_fields=['completed_at', 'updated_at'])
            self.enrollment.update_progress()


def _generate_certificate_code():
    return secrets.token_hex(8).upper()


class Certificate(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificates',
        verbose_name=_('user'),
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='certificates',
        verbose_name=_('course'),
    )
    code = models.CharField(_('code'), max_length=32, unique=True, default=_generate_certificate_code)
    issued_at = models.DateTimeField(_('issued at'), auto_now_add=True)
    score = models.PositiveIntegerField(_('score'))

    class Meta:
        db_table = 'certificates'
        verbose_name = _('certificate')
        verbose_name_plural = _('certificates')
        ordering = ['-issued_at']

    def __str__(self):
        return f'{self.user.email} - {self.course.title} ({self.code})'

    @property
    def holder_name(self):
        full_name = f'{self.user.first_name} {self.user.last_name}'.strip()
        return full_name or self.user.username