"""
Models for the Sessions app - session scheduling, availability, and feedback.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone


class Session(models.Model):

    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', _('Scheduled')
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')
        NO_SHOW = 'NO_SHOW', _('No Show')
        RESCHEDULED = 'RESCHEDULED', _('Rescheduled')

    class FeedbackType(models.TextChoices):
        STUDENT = 'STUDENT', _('Student Feedback')
        MENTOR = 'MENTOR', _('Mentor Feedback')

    match = models.ForeignKey(
        'matching.Match',
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('match'),
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessions_as_student',
        verbose_name=_('student'),
    )
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sessions_as_mentor',
        verbose_name=_('mentor'),
    )
    scheduled_at = models.DateTimeField(_('scheduled at'))
    duration_minutes = models.PositiveIntegerField(_('duration (minutes)'), default=60)
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    meeting_link = models.URLField(_('meeting link'), blank=True)
    meeting_id = models.CharField(_('meeting ID'), max_length=100, blank=True)
    notes = models.TextField(_('notes'), blank=True)
    student_notes = models.TextField(_('student notes'), blank=True)
    mentor_notes = models.TextField(_('mentor notes'), blank=True)

    # Feedback
    feedback_student = models.TextField(_('student feedback'), blank=True)
    feedback_mentor = models.TextField(_('mentor feedback'), blank=True)
    rating_student = models.PositiveSmallIntegerField(_('student rating'), null=True, blank=True)
    rating_mentor = models.PositiveSmallIntegerField(_('mentor rating'), null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    started_at = models.DateTimeField(_('started at'), null=True, blank=True)
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)
    cancelled_at = models.DateTimeField(_('cancelled at'), null=True, blank=True)

    class Meta:
        db_table = 'sessions'
        verbose_name = _('session')
        verbose_name_plural = _('sessions')
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['mentor', 'status']),
            models.Index(fields=['scheduled_at', 'status']),
        ]

    def __str__(self):
        return f'Session: {self.student.email} ↔ {self.mentor.email} at {self.scheduled_at}'

    def is_upcoming(self):
        return self.status == self.Status.SCHEDULED and self.scheduled_at > timezone.now()

    def is_past(self):
        return self.scheduled_at < timezone.now() and self.status in [
            self.Status.COMPLETED,
            self.Status.CANCELLED,
            self.Status.NO_SHOW,
        ]

    def can_be_cancelled(self):
        return self.status in [self.Status.SCHEDULED, self.Status.RESCHEDULED]

    def can_be_rescheduled(self):
        return self.status in [self.Status.SCHEDULED, self.Status.RESCHEDULED]

    def mark_started(self):
        """Mark session as started."""
        self.status = self.Status.IN_PROGRESS
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'updated_at'])

    def mark_completed(self):
        """Mark session as completed."""
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])

    def cancel(self, cancelled_by):
        """Cancel the session."""
        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        if cancelled_by == self.student:
            self.student_notes = f'Cancelled by student at {timezone.now()}'
        elif cancelled_by == self.mentor:
            self.mentor_notes = f'Cancelled by mentor at {timezone.now()}'
        self.save(update_fields=['status', 'cancelled_at', 'student_notes', 'mentor_notes', 'updated_at'])


class SessionRecurrence(models.Model):

    class Frequency(models.TextChoices):
        WEEKLY = 'WEEKLY', _('Weekly')
        BIWEEKLY = 'BIWEEKLY', _('Bi-weekly')
        MONTHLY = 'MONTHLY', _('Monthly')

    session = models.OneToOneField(
        Session,
        on_delete=models.CASCADE,
        related_name='recurrence',
        verbose_name=_('session'),
    )
    frequency = models.CharField(
        _('frequency'),
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.WEEKLY,
    )
    end_date = models.DateField(_('end date'))
    occurrences_count = models.PositiveIntegerField(_('occurrences count'), default=0)
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'session_recurrences'
        verbose_name = _('session recurrence')
        verbose_name_plural = _('session recurrences')

    def __str__(self):
        return f'Recurrence for {self.session}: {self.get_frequency_display()} until {self.end_date}'


class Availability(models.Model):

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, _('Monday')
        TUESDAY = 1, _('Tuesday')
        WEDNESDAY = 2, _('Wednesday')
        THURSDAY = 3, _('Thursday')
        FRIDAY = 4, _('Friday')
        SATURDAY = 5, _('Saturday')
        SUNDAY = 6, _('Sunday')

    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availabilities',
        verbose_name=_('mentor'),
    )
    day_of_week = models.IntegerField(
        _('day of week'),
        choices=DayOfWeek.choices,
    )
    start_time = models.TimeField(_('start time'))
    end_time = models.TimeField(_('end time'))
    timezone = models.CharField(_('timezone'), max_length=50, default='UTC')
    is_recurring = models.BooleanField(_('recurring'), default=True)
    specific_date = models.DateField(_('specific date'), null=True, blank=True)
    is_available = models.BooleanField(_('available'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'availabilities'
        verbose_name = _('availability')
        verbose_name_plural = _('availabilities')
        ordering = ['day_of_week', 'start_time']
        unique_together = ['mentor', 'day_of_week', 'start_time', 'specific_date']

    def __str__(self):
        if self.specific_date:
            return f'{self.mentor.email} - {self.specific_date} ({self.start_time}-{self.end_time})'
        return f'{self.mentor.email} - {self.get_day_of_week_display()} ({self.start_time}-{self.end_time})'

    def get_datetime_range(self, base_date=None):
        """Get datetime range for this availability slot."""
        from datetime import datetime, timedelta

        if self.specific_date:
            date = self.specific_date
        else:
            if base_date is None:
                base_date = timezone.now().date()
            # Find next occurrence of this day
            days_ahead = (self.day_of_week - base_date.weekday()) % 7
            date = base_date + timedelta(days=days_ahead)

        start_dt = timezone.make_aware(datetime.combine(date, self.start_time))
        end_dt = timezone.make_aware(datetime.combine(date, self.end_time))
        return start_dt, end_dt


class SessionFeedback(models.Model):

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='detailed_feedback',
        verbose_name=_('session'),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_feedback_given',
        verbose_name=_('author'),
    )
    feedback_type = models.CharField(
        _('feedback type'),
        max_length=20,
        choices=Session.FeedbackType.choices,
    )
    rating = models.PositiveSmallIntegerField(_('rating'), choices=[(i, i) for i in range(1, 6)])
    strengths = models.TextField(_('strengths'), blank=True)
    areas_for_improvement = models.TextField(_('areas for improvement'), blank=True)
    additional_comments = models.TextField(_('additional comments'), blank=True)
    is_shared = models.BooleanField(_('shared with other party'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        db_table = 'session_feedback'
        verbose_name = _('session feedback')
        verbose_name_plural = _('session feedback')
        ordering = ['-created_at']
        unique_together = ['session', 'author', 'feedback_type']

    def __str__(self):
        return f'{self.feedback_type} feedback by {self.author.email} for session {self.session.id}'