import json
import os
import time
from urllib.error import HTTPError

from django.core.management.base import BaseCommand, CommandError

from apps.careers.models import Career
from apps.courses.drafting import (
    COURSE_DURATION_MINUTES,
    DRAFT_MAX_TOKENS,
    DRAFT_SYSTEM_PROMPT,
    LESSON_DURATION_MINUTES,
    LESSONS_PER_COURSE,
    api_credentials,
    content_courses_dir,
    draft_file_path,
    strip_code_fence,
    validate_draft,
)

MAX_ATTEMPTS = 2
MAX_RATE_LIMIT_RETRIES = 2
RATE_LIMIT_WAIT_SECONDS = 60


class override_max_tokens:
    def __init__(self, value):
        import apps.guide.views as guide_views

        self.module = guide_views
        self.original = guide_views.get_max_tokens
        self.value = value

    def __enter__(self):
        self.module.get_max_tokens = lambda: self.value

    def __exit__(self, *args):
        self.module.get_max_tokens = self.original
        return False


class Command(BaseCommand):
    help = 'Draft one course for a career with AI and write it to content/courses for human review'

    def add_arguments(self, parser):
        parser.add_argument('career_slug', type=str)

    def handle(self, *args, **options):
        slug = options['career_slug']

        try:
            career = Career.objects.get(slug=slug, is_active=True)
        except Career.DoesNotExist:
            raise CommandError(f'No active career found with slug "{slug}".')

        api_key, model = api_credentials()
        if not api_key or not model:
            raise CommandError(
                'OPENROUTER_API_KEY and OPENROUTER_MODEL must be set in your environment before drafting.'
            )

        module_number = self.next_module_number(career)
        order = self.next_order(career, module_number)
        prompt = self.build_prompt(career, module_number, order, COURSE_DURATION_MINUTES)

        self.stdout.write(f'Drafting a course for {career.name} (module {module_number}, order {order})...')

        course = self.request_course(api_key, model, prompt)

        error = None
        parsed = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            parsed, error = self.parse_and_validate(course)
            if error is None:
                break
            self.stderr.write(f'Attempt {attempt} failed validation: {error}')
            if attempt < MAX_ATTEMPTS:
                self.stdout.write('Asking the model to correct the JSON...')
                course = self.request_course(api_key, model, self.repair_prompt(course, error))

        if error is not None:
            raise CommandError(
                f'The model did not return a valid course after {MAX_ATTEMPTS} attempts: {error}\n'
                f'No file was written. Fix the prompt or try again later.'
            )

        parsed['reviewed'] = False

        os.makedirs(content_courses_dir(), exist_ok=True)
        path = draft_file_path(slug)
        with open(path, 'w', encoding='utf-8') as file_handle:
            json.dump(parsed, file_handle, indent=2, ensure_ascii=False)
            file_handle.write('\n')

        self.stdout.write(self.style.SUCCESS(f'Wrote draft to {path}'))
        self.stdout.write(
            f'Reviewed is false. Read {path}, check every fact, then set reviewed to true and run load_reviewed_courses.'
        )

    def next_module_number(self, career):
        latest = career.courses.order_by('-module_number').values_list('module_number', flat=True).first()
        return (latest or 0) + 1

    def next_order(self, career, module_number):
        latest = (
            career.courses.filter(module_number=module_number)
            .order_by('-order')
            .values_list('order', flat=True)
            .first()
        )
        return (latest or 0) + 1

    def build_prompt(self, career, module_number, order, course_duration):
        lesson_lines = '\n'.join(
            f'  Lesson {index}: order {index}, duration_minutes {LESSON_DURATION_MINUTES}'
            for index in range(1, LESSONS_PER_COURSE + 1)
        )
        return (
            f'Career path: {career.name}\n'
            f'Career summary: {career.description}\n'
            f'Key skills for this path: {", ".join(str(skill) for skill in self.skill_names(career))}\n\n'
            f'Set module_number to {module_number}, order to {order} and duration_minutes to {course_duration}.\n'
            f'Produce {LESSONS_PER_COURSE} lessons:\n{lesson_lines}\n\n'
            'Reply with the JSON object only.'
        )

    def skill_names(self, career):
        skills = getattr(career, 'skills', None)
        if skills is None:
            return []
        return [getattr(skill, 'name', str(skill)) for skill in skills.all()]

    def repair_prompt(self, course, error):
        return (
            f'The JSON you returned failed validation: {error}\n\n'
            f'Re-send the whole course object, corrected so it passes. '
            f'Reuse the same content but fix the structure. JSON only, no fences.\n\n'
            f'Your previous response was:\n{course[:2000]}'
        )

    def request_course(self, api_key, model, prompt):
        from apps.guide.views import call_openrouter

        messages = [
            {
                'role': 'system',
                'content': DRAFT_SYSTEM_PROMPT.replace(
                    '{lessons_per_course}', str(LESSONS_PER_COURSE),
                ),
            },
            {'role': 'user', 'content': prompt},
        ]

        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                with override_max_tokens(DRAFT_MAX_TOKENS):
                    reply, usage = call_openrouter(api_key, model, messages)
                self.stdout.write(
                    f'Replied using {usage.get("completion_tokens", 0)} completion tokens.'
                )
                return reply
            except HTTPError as exc:
                if exc.code != 429:
                    raise CommandError(f'OpenRouter returned HTTP {exc.code}. No file was written.')
                if attempt == MAX_RATE_LIMIT_RETRIES:
                    raise CommandError(
                        f'OpenRouter rate limited this request {MAX_RATE_LIMIT_RETRIES + 1} times. '
                        f'Stopping without writing a file. Try again later.'
                    )
                self.stdout.write(
                    f'Rate limited by OpenRouter. Waiting {RATE_LIMIT_WAIT_SECONDS}s then retrying '
                    f'({attempt + 1} of {MAX_RATE_LIMIT_RETRIES})...'
                )
                time.sleep(RATE_LIMIT_WAIT_SECONDS)

    def parse_and_validate(self, raw):
        text = strip_code_fence(raw)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            return None, f'the response was not valid JSON ({exc.msg} at line {exc.lineno}).'

        error = validate_draft(data, LESSONS_PER_COURSE)
        if error:
            return None, error
        return data, None
