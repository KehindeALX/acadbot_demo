"""
Settings for running the automated test suite.

Inherits from development settings but strips out debug_toolbar, since its
middleware assumes its URLs are registered (which only happens when
settings.DEBUG is True at URL-resolution time) and test runners force
DEBUG=False. Keeping it active here would 500 every request.
"""
from .development import *  # noqa: F401,F403

DEBUG = False

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'debug_toolbar']
MIDDLEWARE = [mw for mw in MIDDLEWARE if 'debug_toolbar' not in mw]

# Explicitly disable debug toolbar test check
DEBUG_TOOLBAR_CONFIG = {
    'IS_RUNNING_TESTS': True,
    'SHOW_TOOLBAR_CALLBACK': lambda request: False,
}

ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']