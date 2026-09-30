import json
import logging
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from decouple import config
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import GuideUsage
from .serializers import GuideChatSerializer

logger = logging.getLogger(__name__)

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
UPSTREAM_TIMEOUT = 30
MAX_MESSAGE_CHARS = 1000
MAX_MESSAGES = 10

ABIA_SYSTEM_PROMPT = """You are Abia, the AI career guide for More Success Academy (MSA), an African EdTech platform.

MSA mission: Train. Certify. Place. Product: AcadBot (AI LMS).

Your role: guide a learner through the career journey they are exploring on the site. Give practical, encouraging, Africa-relevant advice about skills, roadmaps, courses and job interviews. When the learner names a career path, give advice for that path.

Be honest about what you are: an AI guide, not a person, and not a source of live job listings or salary data. Never invent course names, fees, dates or openings that MSA has not published. If you do not know something, say so and suggest where the learner could find out.

CRITICAL: Detect the language the user writes in and ALWAYS respond in that SAME language. Keep responses helpful, concise, and warm. Use emojis sparingly. Never exceed 4 sentences unless showing structured content."""


def get_daily_limit():
    try:
        return int(config('GUIDE_DAILY_LIMIT', default=5))
    except ValueError:
        return 5


def get_global_daily_limit():
    try:
        return int(config('GUIDE_GLOBAL_DAILY_LIMIT', default=40))
    except ValueError:
        return 40


def get_max_tokens():
    try:
        return int(config('GUIDE_MAX_TOKENS', default=500))
    except ValueError:
        return 500


def used_since(since, user=None):
    rows = GuideUsage.objects.filter(created_at__gte=since)
    if user is not None:
        rows = rows.filter(user=user)
    return rows.count()


def used_today(user):
    return used_since(timezone.now() - timedelta(days=1), user)


def call_openrouter(api_key, model, messages):
    payload = json.dumps({
        'model': model,
        'messages': messages,
        'max_tokens': get_max_tokens(),
        'temperature': 0.7,
    }).encode('utf-8')

    req = Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}',
        },
        method='POST',
    )

    with urlopen(req, timeout=UPSTREAM_TIMEOUT) as response:
        body = json.loads(response.read().decode('utf-8'))

    reply = body['choices'][0]['message']['content']
    usage = body.get('usage') or {}
    return reply, usage


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


@extend_schema(request=GuideChatSerializer, responses={200: dict})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def guide_chat(request):
    serializer = GuideChatSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'detail': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    api_key = config('OPENROUTER_API_KEY', default='')
    model = config('OPENROUTER_MODEL', default='')

    if not api_key or not model:
        return error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            'Abia is being set up and is not available right now. Please try again later.',
        )

    if used_today(request.user) >= get_daily_limit():
        return error_response(
            status.HTTP_429_TOO_MANY_REQUESTS,
            'You have used all of today\'s questions to Abia. Come back tomorrow.',
        )

    if used_since(timezone.now() - timedelta(days=1)) >= get_global_daily_limit():
        return error_response(
            status.HTTP_429_TOO_MANY_REQUESTS,
            'Abia is resting for today and will be back tomorrow.',
        )

    messages = [{'role': 'system', 'content': ABIA_SYSTEM_PROMPT}]
    messages.extend(serializer.validated_data['messages'])

    try:
        reply, usage = call_openrouter(api_key, model, messages)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, IndexError) as exc:
        logger.warning('Abia upstream call failed: %s', type(exc).__name__)
        return error_response(
            status.HTTP_502_BAD_GATEWAY,
            'Abia is unavailable right now. Please try again in a moment.',
        )

    GuideUsage.objects.create(
        user=request.user,
        prompt_tokens=usage.get('prompt_tokens') or 0,
        completion_tokens=usage.get('completion_tokens') or 0,
    )

    return Response({'reply': reply})
