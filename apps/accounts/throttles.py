"""
Rate limiting for the authentication endpoints.

register and login are throttled to 5 requests/minute *per client IP*
(SimpleRateThrottle keys on the remote address for anonymous requests, which
every register/login is). The per-scope rates live in
settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].

NOTE: rates are resolved at request time (not frozen at import) so the test
suite can relax them via config/settings/test.py and rate-limit tests can
tighten them with override_settings.
"""
from django.core.exceptions import ImproperlyConfigured
from rest_framework.settings import api_settings
from rest_framework.throttling import SimpleRateThrottle


class _AuthRateThrottle(SimpleRateThrottle):
    """
    Base throttle for auth endpoints.

    SimpleRateThrottle reads its rate from the THROTTLE_RATES class attribute,
    which is frozen at import time. Overriding get_rate() resolves the rate from
    the live settings instead, so DEFAULT_THROTTLE_RATES changes take effect
    without a process restart.
    """

    scope = None

    def get_rate(self):
        try:
            return api_settings.DEFAULT_THROTTLE_RATES[self.scope]
        except KeyError:
            raise ImproperlyConfigured(
                f"No default throttle rate set for the '{self.scope}' scope"
            ) from None

    def get_cache_key(self, request, view):
        """
        Bucket by client IP. SimpleRateThrottle deliberately raises
        NotImplementedError for get_cache_key -- subclasses must supply the
        key. register/login are always anonymous requests, so the remote
        address (get_ident) is the only meaningful ident.
        """
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }


class RegisterRateThrottle(_AuthRateThrottle):
    """Limit registration attempts to 5/min per client IP."""

    scope = 'register'


class LoginRateThrottle(_AuthRateThrottle):
    """Limit login attempts to 5/min per client IP."""

    scope = 'login'