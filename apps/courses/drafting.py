import os

from decouple import config
from django.conf import settings

CONTENT_COURSES_DIR = os.path.join(settings.BASE_DIR, 'content', 'courses')

COURSE_KEYS = {'title', 'description', 'module_number', 'duration_minutes', 'order', 'lessons'}
LESSON_KEYS = {
    'title', 'content_html', 'order', 'duration_minutes',
    'quiz_question', 'quiz_options', 'quiz_correct_index', 'quiz_feedback',
}

LESSONS_PER_COURSE = 4
LESSON_DURATION_MINUTES = 45
COURSE_DURATION_MINUTES = LESSONS_PER_COURSE * LESSON_DURATION_MINUTES
QUIZ_OPTION_COUNT = 4
DRAFT_MAX_TOKENS = 8000

DRAFT_SYSTEM_PROMPT = """You write one course for More Success Academy, an African EdTech platform.

You are given a career path and must produce a single course as a JSON object. The JSON must have exactly these keys:

{
  "title": string,
  "description": string,
  "module_number": integer,
  "duration_minutes": integer,
  "order": integer,
  "lessons": [
    {
      "title": string,
      "content_html": string,
      "order": integer,
      "duration_minutes": integer,
      "quiz_question": string,
      "quiz_options": [string, string, string, string],
      "quiz_correct_index": integer,
      "quiz_feedback": string
    }
  ]
}

Rules for the content:
- Beginner friendly. Assume the learner is starting from zero.
- Use Nigerian and African context where it helps, for example local examples, currency, or job market realities.
- Factual only. Never invent tools, software versions, statistics, laws, regulations, prices or URLs.
- Only name a tool, command, package or API that you are certain exists. If you are not certain, describe the concept without naming it.
- Every lesson has exactly one quiz question, with exactly four options and exactly one correct answer. quiz_correct_index is the zero-based position of that correct option, between 0 and 3.
- quiz_feedback is one short sentence explaining why the correct answer is correct.
- content_html is simple HTML made only of <p> and <strong> tags. No headings, lists, code blocks, links, images or attributes.
- Plain language. Short sentences. No jargon without a plain explanation.

Output rules:
- Reply with the JSON object only. No markdown fences, no commentary before or after.
- Produce exactly {lessons_per_course} lessons, with lesson order running 1, 2, 3 up to {lessons_per_course}.
- module_number, order and duration_minutes are given to you in the request. Echo them back unchanged."""


def content_courses_dir():
    return CONTENT_COURSES_DIR


def draft_file_path(career_slug):
    return os.path.join(CONTENT_COURSES_DIR, f'{career_slug}.json')


def strip_code_fence(text):
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = cleaned.split('\n', 1)[1] if '\n' in cleaned else cleaned
        if cleaned.rstrip().endswith('```'):
            cleaned = cleaned.rstrip()[:-3]
    return cleaned.strip()


def validate_draft(data, lessons_per_course=LESSONS_PER_COURSE):
    if not isinstance(data, dict):
        return 'The response was not a JSON object.'

    missing = COURSE_KEYS - set(data)
    if missing:
        return f'Missing course keys: {", ".join(sorted(missing))}.'

    extra = set(data) - COURSE_KEYS - {'reviewed'}
    if extra:
        return f'Unexpected course keys: {", ".join(sorted(extra))}.'

    for field in ('title', 'description'):
        if not isinstance(data[field], str) or not data[field].strip():
            return f'Course {field} must be a non-empty string.'

    for field in ('module_number', 'duration_minutes', 'order'):
        if not isinstance(data[field], int) or isinstance(data[field], bool):
            return f'Course {field} must be an integer.'

    lessons = data['lessons']
    if not isinstance(lessons, list):
        return 'Course lessons must be a list.'
    if len(lessons) != lessons_per_course:
        return f'Expected {lessons_per_course} lessons, got {len(lessons)}.'

    for position, lesson in enumerate(lessons, start=1):
        if not isinstance(lesson, dict):
            return f'Lesson {position} was not a JSON object.'

        missing = LESSON_KEYS - set(lesson)
        if missing:
            return f'Lesson {position} is missing keys: {", ".join(sorted(missing))}.'

        extra = set(lesson) - LESSON_KEYS
        if extra:
            return f'Lesson {position} has unexpected keys: {", ".join(sorted(extra))}.'

        for field in ('title', 'content_html', 'quiz_question', 'quiz_feedback'):
            if not isinstance(lesson[field], str) or not lesson[field].strip():
                return f'Lesson {position} field {field} must be a non-empty string.'

        for field in ('order', 'duration_minutes'):
            if not isinstance(lesson[field], int) or isinstance(lesson[field], bool):
                return f'Lesson {position} field {field} must be an integer.'

        options = lesson['quiz_options']
        if not isinstance(options, list) or len(options) != QUIZ_OPTION_COUNT:
            return f'Lesson {position} needs exactly {QUIZ_OPTION_COUNT} quiz options, got {len(options) if isinstance(options, list) else 0}.'
        if not all(isinstance(option, str) and option.strip() for option in options):
            return f'Lesson {position} has an empty quiz option.'

        correct = lesson['quiz_correct_index']
        if not isinstance(correct, int) or isinstance(correct, bool):
            return f'Lesson {position} quiz_correct_index must be an integer.'
        if not 0 <= correct < QUIZ_OPTION_COUNT:
            return f'Lesson {position} quiz_correct_index must be between 0 and {QUIZ_OPTION_COUNT - 1}.'

    return None


def read_draft_file(path):
    import json

    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def api_credentials():
    return config('OPENROUTER_API_KEY', default=''), config('OPENROUTER_MODEL', default='')
