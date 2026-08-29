"""
Custom exception handling for consistent error responses.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging
import traceback

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent error format.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Customize the error response format
        error_data = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': get_error_message(response.data),
                'details': response.data if isinstance(response.data, dict) else None,
            }
        }
        response.data = error_data
        return response

    # Log unhandled exceptions
    logger.error(f'Unhandled exception: {exc}', exc_info=True, extra={'context': context})

    # TEMPORARY DEBUG (remove after root cause found): surface the real error
    # only when DEBUG or DJANGO_DEBUG_EXCEPTIONS is enabled. Inert in production.
    debug_detail = None
    if settings.DEBUG or getattr(settings, 'DEBUG_EXCEPTIONS', False):
        debug_detail = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    # Return a generic 500 error for unhandled exceptions
    return Response(
        {
            'success': False,
            'error': {
                'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': 'An unexpected error occurred. Please try again later.',
                'details': debug_detail,
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def get_error_message(data):
    """
    Extract a human-readable error message from DRF error data.
    """
    if isinstance(data, dict):
        # Handle field-specific errors
        if 'detail' in data:
            return str(data['detail'])
        # Handle validation errors
        for field, errors in data.items():
            if isinstance(errors, list) and errors:
                return f'{field}: {errors[0]}'
            elif isinstance(errors, str):
                return f'{field}: {errors}'
        return 'Validation error'
    elif isinstance(data, list) and data:
        return str(data[0])
    return str(data) if data else 'An error occurred'