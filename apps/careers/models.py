"""
Models for the Careers app - career paths, skills, roadmaps, interview questions.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class Career(models.Model):

    slug = models.SlugField(_('slug'), unique=True, max_length=50)
    name = models.CharField(_('name'), max_length=100)
    icon = models.CharField(_('icon'), max_length=10, help_text='Emoji icon')
    tag = models.CharField(_('tag'), max_length=50, help_text='Short tagline')
    color = models.CharField(_('color'), max_length=7, help_text='Hex color code')
    description = models.TextField(_('description'), blank=True)
    order = models.PositiveIntegerField(_('order'), default=0)
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'careers'
        verbose_name = _('career')
        verbose_name_plural = _('careers')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class CareerSkill(models.Model):
    """
    Skills required for a career path.
    """

    career = models.ForeignKey(
        Career,
        on_delete=models.CASCADE,
        related_name='skills',
        verbose_name=_('career'),
    )
    name = models.CharField(_('name'), max_length=200)
    order = models.PositiveIntegerField(_('order'), default=0)
    is_core = models.BooleanField(_('core skill'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        db_table = 'career_skills'
        verbose_name = _('career skill')
        verbose_name_plural = _('career skills')
        ordering = ['career', 'order', 'name']

    def __str__(self):
        return f'{self.career.name} - {self.name}'


class RoadmapStage(models.Model):
    """
    Stages in a career roadmap.
    """

    career = models.ForeignKey(
        Career,
        on_delete=models.CASCADE,
        related_name='roadmap_stages',
        verbose_name=_('career'),
    )
    title = models.CharField(_('title'), max_length=200)
    description = models.TextField(_('description'))
    order = models.PositiveIntegerField(_('order'), default=0)
    estimated_weeks = models.PositiveIntegerField(_('estimated weeks'), default=0)
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        db_table = 'roadmap_stages'
        verbose_name = _('roadmap stage')
        verbose_name_plural = _('roadmap stages')
        ordering = ['career', 'order']

    def __str__(self):
        return f'{self.career.name} - Stage {self.order}: {self.title}'


class InterviewQuestion(models.Model):
    """
    Interview questions for a career path.
    """

    class Difficulty(models.TextChoices):
        EASY = 'EASY', _('Easy')
        MEDIUM = 'MEDIUM', _('Medium')
        HARD = 'HARD', _('Hard')

    career = models.ForeignKey(
        Career,
        on_delete=models.CASCADE,
        related_name='interview_questions',
        verbose_name=_('career'),
    )
    question = models.TextField(_('question'))
    order = models.PositiveIntegerField(_('order'), default=0)
    difficulty = models.CharField(
        _('difficulty'),
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM,
    )
    is_active = models.BooleanField(_('active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        db_table = 'interview_questions'
        verbose_name = _('interview question')
        verbose_name_plural = _('interview questions')
        ordering = ['career', 'order']

    def __str__(self):
        return f'{self.career.name} - Q{self.order}: {self.question[:50]}...'