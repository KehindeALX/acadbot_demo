import json
import logging
from urllib.error import HTTPError, URLError

from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Subscription

logger = logging.getLogger(__name__)

UPSTREAM_ERRORS = (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, IndexError, TypeError)


def error_response(code, message):
    return Response(
        {
            'success': False,
            'error': {
                'code': code,
                'message': message,
                'details': None,
            },
        },
        status=code,
    )


@extend_schema(request=None, responses={200: dict})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initialize_payment(request):
    secret_key = services.get_secret_key()
    if not secret_key:
        return error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            'Payments are being set up and are not available right now. Please try again later.',
        )

    amount = services.get_amount_kobo()
    reference = services.build_reference()

    subscription = Subscription.objects.create(
        user=request.user,
        reference=reference,
        amount=amount,
    )

    try:
        authorization_url, body = services.initialize_transaction(
            request.user, request.user.email, reference, amount,
        )
    except UPSTREAM_ERRORS as exc:
        subscription.status = Subscription.Status.FAILED
        subscription.save(update_fields=['status', 'updated_at'])
        logger.warning('Paystack initialize failed: %s', type(exc).__name__)
        return error_response(
            status.HTTP_502_BAD_GATEWAY,
            'We could not start the payment right now. Please try again in a moment.',
        )

    return Response({
        'success': True,
        'data': {
            'authorization_url': authorization_url,
            'reference': reference,
            'amount': amount,
            'amount_display': services.amount_in_naira(amount),
            'access_code': (body.get('data') or {}).get('access_code'),
        },
    })


@extend_schema(responses={200: dict})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    reference = request.query_params.get('reference')
    if not reference:
        return error_response(status.HTTP_400_BAD_REQUEST, 'A payment reference is required.')

    subscription = Subscription.objects.filter(
        user=request.user,
        reference=reference,
    ).first()

    if not subscription:
        return error_response(status.HTTP_404_NOT_FOUND, 'We could not find that payment for your account.')

    if not services.get_secret_key():
        return error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            'Payments are being set up and are not available right now. Please try again later.',
        )

    try:
        transaction = services.verify_transaction(reference)
    except UPSTREAM_ERRORS as exc:
        logger.warning('Paystack verify failed: %s', type(exc).__name__)
        return error_response(
            status.HTTP_502_BAD_GATEWAY,
            'We could not confirm the payment just now. Please try again in a moment.',
        )

    if not transaction:
        return error_response(
            status.HTTP_400_BAD_REQUEST,
            'That payment is still being processed. Please try again in a moment.',
        )

    if services.transaction_pending(transaction):
        return payment_state_response(subscription, pending=True)

    services.apply_transaction(subscription, transaction)
    subscription.refresh_from_db()

    return payment_state_response(subscription)


@extend_schema(responses={200: dict})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status(request):
    return payment_state_response(services.active_subscription(request.user))


def payment_state_response(subscription, pending=False):
    active = (
        subscription is not None
        and subscription.status == Subscription.Status.ACTIVE
        and subscription.expires_at is not None
        and subscription.expires_at > timezone.now()
    )
    return Response({
        'success': True,
        'data': {
            'active': active,
            'pending': pending,
            'expires_at': subscription.expires_at if active else None,
            'status': subscription.status if subscription else Subscription.Status.EXPIRED,
            'reference': subscription.reference if active else None,
        },
    })


@method_decorator(csrf_exempt, name='dispatch')
class PaystackWebhook(APIView):

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        raw_body = request.body
        signature = request.headers.get('x-paystack-signature', '')

        if not services.valid_signature(raw_body, signature):
            return Response({'status': False}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = json.loads(raw_body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return Response({'status': False}, status=status.HTTP_400_BAD_REQUEST)

        data = payload.get('data') or {}
        reference = data.get('reference')
        if not reference:
            return Response({'status': False}, status=status.HTTP_400_BAD_REQUEST)

        if data.get('status') != 'success':
            return Response({'status': True})

        subscription = Subscription.objects.filter(reference=reference).first()
        if not subscription:
            return Response({'status': True})

        transaction = {
            'reference': reference,
            'status': data.get('status'),
            'amount': data.get('amount'),
            'currency': data.get('currency'),
        }
        services.apply_transaction(subscription, transaction)

        return Response({'status': True})
