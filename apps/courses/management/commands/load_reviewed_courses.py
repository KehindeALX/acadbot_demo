import json
import os

from django.core.management.base import BaseCommand, CommandError

from apps.careers.models import Career
from apps.courses.drafting import content_courses_dir, validate_draft
from apps.courses.models import Course, Lesson


class Command(BaseCommand):
    help = 'Load courses from content/courses that a human has marked reviewed'

    def handle(self, *args, **options):
        directory = content_courses_dir()
        if not os.path.isdir(directory):
            raise CommandError(f'No content directory at {directory}. Run draft_course first.')

        filenames = sorted(f for f in os.listdir(directory) if f.endswith('.json'))
        if not filenames:
            self.stdout.write('No draft files found.')
            return

        created = 0
        updated = 0
        skipped = 0
        waiting = []

        for filename in filenames:
            path = os.path.join(directory, filename)
            slug = os.path.splitext(filename)[0]

            try:
                with open(path, encoding='utf-8') as handle:
                    data = json.load(handle)
            except json.JSONDecodeError as exc:
                self.stderr.write(f'  {filename}: invalid JSON ({exc.msg}). Skipped.')
                skipped += 1
                continue

            if not isinstance(data, dict) or not data.get('reviewed'):
                waiting.append(filename)
                continue

            if validate_draft(data):
                self.stderr.write(f'  {filename}: does not match the course structure. Skipped.')
                skipped += 1
                continue

            try:
                career = Career.objects.get(slug=slug)
            except Career.DoesNotExist:
                self.stderr.write(f'  {filename}: no career with slug "{slug}". Skipped.')
                skipped += 1
                continue

            was_created, course_created, lesson_created, lesson_updated = self.load_course(career, data)
            if course_created:
                created += 1
                self.stdout.write(f'  Created course: {career.name} - Module {data["module_number"]}: {data["title"]}')
            elif was_created:
                updated += 1
                self.stdout.write(f'  Updated course: {career.name} - Module {data["module_number"]}: {data["title"]}')
            else:
                skipped += 1
                self.stdout.write(f'  Unchanged course: {career.name} - Module {data["module_number"]}: {data["title"]}')

            self.stdout.write(
                f'    {lesson_created} lesson(s) created, {lesson_updated} updated'
            )

        self.stdout.write(self.style.SUCCESS(f'Created: {created}  Updated: {updated}  Skipped: {skipped}'))

        if waiting:
            self.stdout.write(self.style.WARNING(f'{len(waiting)} file(s) waiting for review:'))
            for filename in waiting:
                self.stdout.write(f'  - {filename}')

    def load_course(self, career, data):
        course_defaults = {
            'title': data['title'],
            'description': data['description'],
            'duration_minutes': data['duration_minutes'],
            'is_published': True,
            'content_reviewed': True,
        }
        course, created = Course.objects.update_or_create(
            career=career,
            module_number=data['module_number'],
            order=data['order'],
            defaults=course_defaults,
        )

        lesson_created = 0
        lesson_updated = 0

        for lesson_data in data['lessons']:
            fields = {
                key: value
                for key, value in lesson_data.items()
                if key != 'order'
            }
            fields['is_published'] = True
            _, was_created = Lesson.objects.update_or_create(
                course=course,
                order=lesson_data['order'],
                defaults=fields,
            )
            if was_created:
                lesson_created += 1
            else:
                lesson_updated += 1

        return created, created, lesson_created, lesson_updated
