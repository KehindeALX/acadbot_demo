"""
Management command to seed all demo data in one go.
Runs: seed_careers, seed_courses, seed_mentors
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Seed all demo data: careers, courses, and mentors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        clear = options['clear']

        self.stdout.write(self.style.NOTICE('=' * 60))
        self.stdout.write(self.style.NOTICE('SEEDING DEMO DATA'))
        self.stdout.write(self.style.NOTICE('=' * 60))

        # 1. Seed careers (must run first - other commands depend on Career objects)
        self.stdout.write(self.style.NOTICE('\n[1/3] Seeding careers...'))
        if clear:
            call_command('seed_careers', '--clear', stdout=self.stdout, stderr=self.stderr)
        else:
            call_command('seed_careers', stdout=self.stdout, stderr=self.stderr)

        # 2. Seed courses (depends on careers)
        self.stdout.write(self.style.NOTICE('\n[2/3] Seeding courses...'))
        if clear:
            call_command('seed_courses', '--clear', stdout=self.stdout, stderr=self.stderr)
        else:
            call_command('seed_courses', stdout=self.stdout, stderr=self.stderr)

        # 3. Seed mentors (depends on careers)
        self.stdout.write(self.style.NOTICE('\n[3/3] Seeding mentors...'))
        if clear:
            call_command('seed_mentors', '--clear', stdout=self.stdout, stderr=self.stderr)
        else:
            call_command('seed_mentors', stdout=self.stdout, stderr=self.stderr)

        self.stdout.write(self.style.NOTICE('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('ALL DEMO DATA SEEDED SUCCESSFULLY'))
        self.stdout.write(self.style.NOTICE('=' * 60))