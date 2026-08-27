"""
WSGI config for AcadBot project.
"""
import os
from django.core.wsgi import get_wsgi_application

# Use production settings by default, allow override via env var
env = os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings.production')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', env)

application = get_wsgi_application()