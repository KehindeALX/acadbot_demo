"""
Custom User model and profile models for AcadBot.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model using email as the primary identifier.
    Roles: STUDENT, MENTOR, ADMIN
    """

    class Role(models.TextChoices):
        STUDENT = 'STUDENT', _('Student')
        MENTOR = 'MENTOR', _('Mentor')
        ADMIN = 'ADMIN', _('Admin')

    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )
    phone = models.CharField(_('phone number'), max_length=20, blank=True)
    avatar = models.ImageField(_('avatar'), upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(_('bio'), blank=True)
    timezone = models.CharField(_('timezone'), max_length=50, default='UTC')
    is_verified = models.BooleanField(_('verified'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.email} ({self.get_role_display()})'

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_mentor(self):
        return self.role == self.Role.MENTOR

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN

    def get_profile(self):
        """Return the appropriate profile based on role."""
        if self.is_student:
            return getattr(self, 'student_profile', None)
        elif self.is_mentor:
            return getattr(self, 'mentor_profile', None)
        return None


class StudentProfile(models.Model):
    """
    Extended profile for students.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name=_('user'),
    )
    career = models.ForeignKey(
        'careers.Career',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name=_('career'),
    )
    current_stage = models.ForeignKey(
        'careers.RoadmapStage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_students',
        verbose_name=_('current stage'),
    )
    skills_data = models.JSONField(_('skills data'), default=dict, blank=True)
    onboarding_complete = models.BooleanField(_('onboarding complete'), default=False)
    preferred_schedule = models.JSONField(_('preferred schedule'), default=dict, blank=True)
    learning_goals = models.TextField(_('learning goals'), blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'student_profiles'
        verbose_name = _('student profile')
        verbose_name_plural = _('student profiles')

    def __str__(self):
        return f'Student: {self.user.email}'

    @property
    def progress_percentage(self):
        """Calculate overall progress percentage."""
        if not self.career:
            return 0
        total_stages = self.career.roadmap_stages.count()
        if total_stages == 0:
            return 0
        current_order = self.current_stage.order if self.current_stage else 0
        return int((current_order / total_stages) * 100)


class MentorProfile(models.Model):
    """
    Extended profile for mentors.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='mentor_profile',
        verbose_name=_('user'),
    )
    expertise_careers = models.ManyToManyField(
        'careers.Career',
        related_name='mentors',
        verbose_name=_('expertise careers'),
        blank=True,
    )
    hourly_rate = models.DecimalField(_('hourly rate'), max_digits=10, decimal_places=2, default=0)
    availability_data = models.JSONField(_('availability data'), default=dict, blank=True)
    rating = models.DecimalField(_('rating'), max_digits=3, decimal_places=2, default=0)
    total_sessions = models.PositiveIntegerField(_('total sessions'), default=0)
    bio = models.TextField(_('bio'), blank=True)
    is_verified = models.BooleanField(_('verified'), default=False)
    is_available = models.BooleanField(_('available for matching'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'mentor_profiles'
        verbose_name = _('mentor profile')
        verbose_name_plural = _('mentor profiles')

    def __str__(self):
        return f'Mentor: {self.user.email}'

    def update_rating(self):
        """Update mentor rating based on session feedback."""
        from apps.sessions.models import Session
        from django.db.models import Avg

        completed_sessions = Session.objects.filter(
            mentor=self.user,
            status=Session.Status.COMPLETED,
            rating_mentor__isnull=False,
        )
        avg_rating = completed_sessions.aggregate(Avg('rating_mentor'))['rating_mentor__avg']
        if avg_rating:
            self.rating = round(avg_rating, 2)
            self.total_sessions = completed_sessions.count()
            self.save(update_fields=['rating', 'total_sessions'])