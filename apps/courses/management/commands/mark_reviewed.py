"""
Mark a course as content reviewed so its students can be certified.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.courses.models import Course


class Command(BaseCommand):
    help = 'Mark a course as content reviewed, making it eligible for certificates.'

    def add_arguments(self, parser):
        parser.add_argument(
            'course',
            help='Course id, or career slug and module number (e.g. "cyber 2").',
        )
        parser.add_argument(
            'module_number',
            nargs='?',
            default=None,
            help='Module number, when the first argument is a career slug.',
        )

    def handle(self, *args, **options):
        course = self._resolve(options['course'], options['module_number'])
        if course is None:
            raise CommandError('No matching course found.')

        if course.content_reviewed:
            self.stdout.write(self.style.WARNING(
                f'Course {course.pk} "{course.title}" is already marked reviewed.'
            ))
            return

        course.content_reviewed = True
        course.save(update_fields=['content_reviewed'])
        self.stdout.write(self.style.SUCCESS(
            f'Course {course.pk} "{course.title}" is now marked reviewed.'
        ))

    def _resolve(self, identifier, module_number):
        if module_number is not None:
            return Course.objects.filter(
                career__slug=identifier,
                module_number=module_number,
            ).first()

        if identifier.isdigit():
            return Course.objects.filter(pk=int(identifier)).first()

        raise CommandError(
            f'"{identifier}" is neither a numeric course id nor a career slug. '
            'Pass a course id, or a career slug followed by a module number.'
        )
