from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class GuideUsage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='guide_usage',
        verbose_name=_('user'),
    )
    prompt_tokens = models.PositiveIntegerField(_('prompt tokens'), default=0)
    completion_tokens = models.PositiveIntegerField(_('completion tokens'), default=0)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        db_table = 'guide_usage'
        verbose_name = _('guide usage')
        verbose_name_plural = _('guide usage')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} — {self.created_at:%Y-%m-%d %H:%M}'
