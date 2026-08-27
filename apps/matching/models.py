"""
Models for the Matching app - match requests and matches.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class MatchRequest(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        MATCHED = 'MATCHED', _('Matched')
        REJECTED = 'REJECTED', _('Rejected')
        CANCELLED = 'CANCELLED', _('Cancelled')

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='match_requests',
        verbose_name=_('student'),
    )
    preferred_careers = models.ManyToManyField(
        'careers.Career',
        related_name='match_requests',
        verbose_name=_('preferred careers'),
        blank=True,
    )
    preferred_schedule = models.JSONField(_('preferred schedule'), default=dict, blank=True)
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    notes = models.TextField(_('notes'), blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    matched_at = models.DateTimeField(_('matched at'), null=True, blank=True)

    class Meta:
        db_table = 'match_requests'
        verbose_name = _('match request')
        verbose_name_plural = _('match requests')
        ordering = ['-created_at']

    def __str__(self):
        return f'Match request by {self.student.email} ({self.get_status_display()})'

    def is_pending(self):
        return self.status == self.Status.PENDING


class Match(models.Model):

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')  # Awaiting mentor acceptance
        ACTIVE = 'ACTIVE', _('Active')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')

    match_request = models.ForeignKey(
        MatchRequest,
        on_delete=models.CASCADE,
        related_name='matches',
        verbose_name=_('match request'),
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matches_as_student',
        verbose_name=_('student'),
    )
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matches_as_mentor',
        verbose_name=_('mentor'),
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    compatibility_score = models.DecimalField(
        _('compatibility score'),
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    accepted_at = models.DateTimeField(_('accepted at'), null=True, blank=True)
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)

    class Meta:
        db_table = 'matches'
        verbose_name = _('match')
        verbose_name_plural = _('matches')
        ordering = ['-created_at']

    def __str__(self):
        return f'Match: {self.student.email} ↔ {self.mentor.email} ({self.get_status_display()})'

    def accept(self):
        """Accept the match (mentor only)."""
        from django.utils import timezone
        self.status = self.Status.ACTIVE
        self.accepted_at = timezone.now()
        self.save(update_fields=['status', 'accepted_at', 'updated_at'])
        # Update match request status
        self.match_request.status = MatchRequest.Status.MATCHED
        self.match_request.matched_at = timezone.now()
        self.match_request.save(update_fields=['status', 'matched_at', 'updated_at'])

    def decline(self):
        """Decline the match (mentor only)."""
        from django.utils import timezone
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status', 'updated_at'])
        # Reset match request status
        self.match_request.status = MatchRequest.Status.PENDING
        self.match_request.save(update_fields=['status', 'updated_at'])


class MentorMatch(models.Model):

    match_request = models.ForeignKey(
        MatchRequest,
        on_delete=models.CASCADE,
        related_name='suggested_mentors',
        verbose_name=_('match request'),
    )
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='suggested_matches',
        verbose_name=_('mentor'),
    )
    compatibility_score = models.DecimalField(
        _('compatibility score'),
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    is_accepted = models.BooleanField(_('accepted'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        db_table = 'mentor_matches'
        verbose_name = _('mentor match suggestion')
        verbose_name_plural = _('mentor match suggestions')
        ordering = ['-compatibility_score']
        unique_together = ['match_request', 'mentor']

    def __str__(self):
        return f'Suggestion: {self.mentor.email} for {self.match_request.student.email}'
