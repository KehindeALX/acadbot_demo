import hashlib
import hmac
import json
import logging
import secrets
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from decouple import config
from django.utils import timezone

from .models import Subscription

logger = logging.getLogger(__name__)

PAYSTACK_API_URL = 'https://api.paystack.co'
PAYSTACK_INITIALIZE_URL = f'{PAYSTACK_API_URL}/transaction/initialize'
PAYSTACK_VERIFY_URL = PAYSTACK_API_URL + '/transaction/verify/{}'
PAYSTACK_TIMEOUT = 30
PENDING_TRANSACTION_STATUSES = ('pending', 'queued', 'ongoing')


def get_secret_key():
    return config('PAYSTACK_SECRET_KEY', default='').strip().strip('"\'')


def get_amount_kobo():
    try:
        return int(config('SUBSCRIPTION_AMOUNT_KOBO', default=500000))
    except ValueError:
        return 500000


def get_subscription_days():
    try:
        return int(config('SUBSCRIPTION_DAYS', default=30))
    except ValueError:
        return 30


def get_free_lessons():
    try:
        return int(config('FREE_LESSONS_PER_COURSE', default=2))
    except ValueError:
        return 2


def build_reference():
    return f'acadbot-{secrets.token_hex(10)}'


def amount_in_naira(amount_kobo):
    return f'{amount_kobo / 100:.2f}'


def call_paystack(url, payload=None, method='POST'):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'MSA-AcadBot/1.0',
        'Authorization': f'Bearer {get_secret_key()}',
    }
    data = json.dumps(payload).encode('utf-8') if payload is not None else None

    req = Request(url, data=data, headers=headers, method=method)

    with urlopen(req, timeout=PAYSTACK_TIMEOUT) as response:
        return json.loads(response.read().decode('utf-8'))


def initialize_transaction(user, email, reference, amount_kobo):
    payload = {
        'email': email,
        'amount': amount_kobo,
        'reference': reference,
        'callback_url': f'{callback_base_url()}/payment-return.html',
    }
    body = call_paystack(PAYSTACK_INITIALIZE_URL, payload)
    return body['data']['authorization_url'], body


def verify_transaction(reference):
    body = call_paystack(PAYSTACK_VERIFY_URL.format(reference), method='GET')
    return body.get('data') or {}


def callback_base_url():
    return config('FRONTEND_BASE_URL', default='https://app.moresuccessacademy.com.ng').rstrip('/')


def valid_signature(raw_body, signature):
    secret = get_secret_key()
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(digest, signature)


def transaction_succeeded(transaction):
    if transaction.get('status') != 'success':
        return False

    currency = transaction.get('currency')
    return currency is None or currency == 'NGN'


def transaction_pending(transaction):
    return str(transaction.get('status') or '').lower() in PENDING_TRANSACTION_STATUSES


def activate(subscription, paid_at=None):
    subscription.status = Subscription.Status.ACTIVE
    subscription.paid_at = paid_at or timezone.now()
    subscription.expires_at = subscription.paid_at + timedelta(days=get_subscription_days())
    subscription.save(update_fields=['status', 'paid_at', 'expires_at', 'updated_at'])
    return subscription


def apply_transaction(subscription, transaction):
    if subscription.status == Subscription.Status.ACTIVE and subscription.paid_at:
        return subscription

    if not transaction_succeeded(transaction):
        subscription.status = Subscription.Status.FAILED
        subscription.save(update_fields=['status', 'updated_at'])
        return subscription

    if int(transaction.get('amount') or 0) != subscription.amount:
        subscription.status = Subscription.Status.FAILED
        subscription.save(update_fields=['status', 'updated_at'])
        logger.warning('Subscription %s rejected: amount mismatch', subscription.reference)
        return subscription

    return activate(subscription)


def active_subscription(user):
    return Subscription.objects.filter(
        user=user,
        status=Subscription.Status.ACTIVE,
        expires_at__gt=timezone.now(),
    ).order_by('-expires_at').first()


def has_active_access(user):
    return active_subscription(user) is not None


def is_lesson_locked(lesson):
    siblings = lesson.course.lessons.filter(is_published=True)
    position = siblings.filter(order__lt=lesson.order).count() + 1
    return position > get_free_lessons()
