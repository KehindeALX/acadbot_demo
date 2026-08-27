from django.apps import AppConfig


class SessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sessions'
    verbose_name = 'Sessions'
    label = 'acadbot_sessions'  # Avoid conflict with Django's built-in sessions app