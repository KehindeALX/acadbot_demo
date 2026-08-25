"""
Models for the Progress app - skill assessments, milestones, and learning paths.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone


class SkillAssessment(models.Model):

    class Level(models.IntegerChoices):
        NOVICE = 1, _('Novice')
        BEGINNER = 2, _('Beginner')
        INTERMEDIATE = 3, _('Intermediate')
        ADVANCED = 4, _('Advanced')
        EXPERT = 5, _('Expert')

    class AssessmentType(models.TextChoices):
        SELF = 'SELF', _('Self Assessment')
        MENTOR = 'MENTOR', _('Mentor Assessment')
        PEER = 'PEER', _('Peer Assessment')
        AUTO = 'AUTO', _('Automated Assessment')

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='skill_assessments',
        verbose_name=_('student'),
    )
    career_skill = models.ForeignKey(
        'careers.CareerSkill',
        on_delete=models.CASCADE,
        related_name='assessments',
        verbose_name=_('career skill'),
    )
    self_rated_level = models.IntegerField(
        _('self rated level'),
        choices=Level.choices,
        null=True,
        blank=True,
    )
    assessed_level = models.IntegerField(
        _('assessed level'),
        choices=Level.choices,
        null=True,
        blank=True,
    )
    assessment_type = models.CharField(
        _('assessment type'),
        max_length=20,
        choices=AssessmentType.choices,
        default=AssessmentType.SELF,
    )
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assessments_given',
        verbose_name=_('assessed by'),
    )
    evidence = models.TextField(_('evidence'), blank=True)
    notes = models.TextField(_('notes'), blank=True)
    assessed_at = models.DateTimeField(_('assessed at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'skill_assessments'
        verbose_name = _('skill assessment')
        verbose_name_plural = _('skill assessments')
        ordering = ['-assessed_at']
        unique_together = ['student', 'career_skill', 'assessment_type']
        indexes = [
            models.Index(fields=['student', 'career_skill']),
            models.Index(fields=['assessed_at']),
        ]

    def __str__(self):
        return f'{self.student.email} - {self.career_skill.name}: {self.get_assessed_level_display() or "Not assessed"}'

    @property
    def level_display(self):
        level = self.assessed_level or self.self_rated_level
        if level:
            return self.Level(level).label
        return 'Not assessed'

    @property
    def is_assessed(self):
        return self.assessed_level is not None


class Milestone(models.Model):

    class MilestoneType(models.TextChoices):
        SKILL = 'SKILL', _('Skill Milestone')
        COURSE = 'COURSE', _('Course Completion')
        SESSION = 'SESSION', _('Session Completed')
        CERTIFICATION = 'CERTIFICATION', _('Certification')
        PROJECT = 'PROJECT', _('Project Completed')
        MATCH = 'MATCH', _('Mentor Matched')
        CUSTOM = 'CUSTOM', _('Custom Milestone')

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='milestones',
        verbose_name=_('student'),
    )
    career = models.ForeignKey(
        'careers.Career',
        on_delete=models.CASCADE,
        related_name='milestones',
        verbose_name=_('career'),
        null=True,
        blank=True,
    )
    title = models.CharField(_('title'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    milestone_type = models.CharField(
        _('milestone type'),
        max_length=20,
        choices=MilestoneType.choices,
        default=MilestoneType.CUSTOM,
    )
    achieved_at = models.DateTimeField(_('achieved at'), default=timezone.now)
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    is_public = models.BooleanField(_('public'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        db_table = 'milestones'
        verbose_name = _('milestone')
        verbose_name_plural = _('milestones')
        ordering = ['-achieved_at']
        indexes = [
            models.Index(fields=['student', 'career']),
            models.Index(fields=['milestone_type']),
        ]

    def __str__(self):
        return f'{self.student.email} - {self.title} ({self.get_milestone_type_display()})'


class LearningPath(models.Model):

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_path',
        verbose_name=_('student'),
    )
    career = models.ForeignKey(
        'careers.Career',
        on_delete=models.CASCADE,
        related_name='learning_paths',
        verbose_name=_('career'),
    )
    current_stage = models.ForeignKey(
        'careers.RoadmapStage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='learning_path_students',
        verbose_name=_('current stage'),
    )
    started_at = models.DateTimeField(_('started at'), auto_now_add=True)
    target_completion_date = models.DateField(_('target completion date'), null=True, blank=True)
    is_active = models.BooleanField(_('active'), default=True)
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'learning_paths'
        verbose_name = _('learning path')
        verbose_name_plural = _('learning paths')
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.student.email} - {self.career.name} Learning Path'

    def get_progress_percent(self):
        """Calculate overall progress percentage."""
        if not self.current_stage:
            return 0

        total_stages = self.career.roadmap_stages.count()
        if total_stages == 0:
            return 0

        completed_stages = self.career.roadmap_stages.filter(order__lt=self.current_stage.order).count()
        return round((completed_stages / total_stages) * 100, 1)

    def get_next_stage(self):
        """Get the next roadmap stage."""
        if not self.current_stage:
            return self.career.roadmap_stages.order_by('order').first()

        return self.career.roadmap_stages.filter(order__gt=self.current_stage.order).order_by('order').first()

    def advance_stage(self, new_stage):
        """Advance to a new stage."""
        self.current_stage = new_stage
        if not self.get_next_stage():
            self.is_active = False
            self.completed_at = timezone.now()
        self.save(update_fields=['current_stage', 'is_active', 'completed_at', 'updated_at'])

    @property
    def completed_stages_count(self):
        if not self.current_stage:
            return 0
        return self.career.roadmap_stages.filter(order__lt=self.current_stage.order).count()

    @property
    def total_stages_count(self):
        return self.career.roadmap_stages.count()


class ProgressSnapshot(models.Model):

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='progress_snapshots',
        verbose_name=_('student'),
    )
    career = models.ForeignKey(
        'careers.Career',
        on_delete=models.CASCADE,
        related_name='progress_snapshots',
        verbose_name=_('career'),
    )
    # Aggregated metrics
    courses_completed = models.PositiveIntegerField(default=0)
    courses_in_progress = models.PositiveIntegerField(default=0)
    lessons_completed = models.PositiveIntegerField(default=0)
    total_lesson_time_minutes = models.PositiveIntegerField(default=0)
    sessions_completed = models.PositiveIntegerField(default=0)
    total_session_minutes = models.PositiveIntegerField(default=0)
    skills_assessed = models.PositiveIntegerField(default=0)
    average_skill_level = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    milestones_achieved = models.PositiveIntegerField(default=0)
    learning_path_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    snapshot_date = models.DateField(_('snapshot date'), default=timezone.now)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        db_table = 'progress_snapshots'
        verbose_name = _('progress snapshot')
        verbose_name_plural = _('progress snapshots')
        ordering = ['-snapshot_date']
        unique_together = ['student', 'career', 'snapshot_date']

    def __str__(self):
        return f'{self.student.email} - {self.career.name} ({self.snapshot_date})'