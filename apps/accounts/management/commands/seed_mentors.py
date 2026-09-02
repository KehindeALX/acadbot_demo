"""
Management command to seed mentor users and profiles for Cybersecurity and AI & Machine Learning career paths.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.careers.models import Career
from apps.accounts.models import MentorProfile

User = get_user_model()


MENTOR_DATA = [
    {
        'username': 'sarah.chen',
        'email': 'sarah.chen@acadbot.demo',
        'first_name': 'Sarah',
        'last_name': 'Chen',
        'password': 'MentorPass123!',
        'career_slugs': ['cyber'],
        'hourly_rate': '150.00',
        'bio': (
            'Sarah spent 8 years as a Senior Security Engineer at a Fortune 500 financial services firm, '
            'leading incident response for a 50,000-endpoint environment. She holds CISSP, GCFA, and '
            'OSCP certifications. Her specialty is helping career-changers bridge the gap between theory '
            'and real-world SOC operations.'
        ),
        'availability_data': {
            'timezone': 'America/Los_Angeles',
            'weekly_schedule': {
                'monday': ['18:00-21:00'],
                'wednesday': ['18:00-21:00'],
                'saturday': ['10:00-14:00'],
            },
        },
    },
    {
        'username': 'marcus.rodriguez',
        'email': 'marcus.rodriguez@acadbot.demo',
        'first_name': 'Marcus',
        'last_name': 'Rodriguez',
        'password': 'MentorPass123!',
        'career_slugs': ['cyber'],
        'hourly_rate': '175.00',
        'bio': (
            'Marcus is a former Red Team operator for a Big 4 consulting practice, with deep experience '
            'in adversary emulation, cloud penetration testing (AWS/Azure), and physical security assessments. '
            'He authored several internal tools for automated privilege escalation. He enjoys teaching the '
            '"attacker mindset" to blue teamers and developers alike.'
        ),
        'availability_data': {
            'timezone': 'America/Chicago',
            'weekly_schedule': {
                'tuesday': ['19:00-22:00'],
                'thursday': ['19:00-22:00'],
                'sunday': ['14:00-18:00'],
            },
        },
    },
    {
        'username': 'priya.sharma',
        'email': 'priya.sharma@acadbot.demo',
        'first_name': 'Priya',
        'last_name': 'Sharma',
        'password': 'MentorPass123!',
        'career_slugs': ['cyber', 'ai'],
        'hourly_rate': '200.00',
        'bio': (
            'Priya leads AI Security Research at a major tech company, focusing on adversarial machine learning, '
            'model extraction attacks, and securing ML pipelines. She has published at NeurIPS and Black Hat. '
            'Her unique background spans both offensive security and ML engineering, making her an ideal mentor '
            'for students at the intersection of these fields.'
        ),
        'availability_data': {
            'timezone': 'America/New_York',
            'weekly_schedule': {
                'monday': ['20:00-22:00'],
                'wednesday': ['20:00-22:00'],
                'friday': ['18:00-21:00'],
            },
        },
    },
    {
        'username': 'david.okonkwo',
        'email': 'david.okonkwo@acadbot.demo',
        'first_name': 'David',
        'last_name': 'Okonkwo',
        'password': 'MentorPass123!',
        'career_slugs': ['ai'],
        'hourly_rate': '180.00',
        'bio': (
            'David was a founding ML engineer at a Y Combinator startup that built NLP-powered contract analysis '
            'for legal teams. He scaled their model training infrastructure from single-GPU to distributed '
            'training on Kubernetes. He\'s passionate about MLOps best practices and helping students build '
            'portfolio projects that actually ship to production.'
        ),
        'availability_data': {
            'timezone': 'Europe/London',
            'weekly_schedule': {
                'tuesday': ['18:00-21:00'],
                'thursday': ['18:00-21:00'],
                'saturday': ['09:00-13:00'],
            },
        },
    },
    {
        'username': 'elena.volkova',
        'email': 'elena.volkova@acadbot.demo',
        'first_name': 'Elena',
        'last_name': 'Volkova',
        'password': 'MentorPass123!',
        'career_slugs': ['ai'],
        'hourly_rate': '220.00',
        'bio': (
            'Elena spent 6 years at a leading autonomous vehicle company, working on perception systems '
            '(camera + LiDAR fusion, 3D object detection, sensor calibration). She holds a PhD in Computer '
            'Vision from ETH Zurich. Her mentorship focuses on the rigorous experimental discipline needed '
            'for safety-critical ML systems, not just model accuracy on benchmarks.'
        ),
        'availability_data': {
            'timezone': 'Europe/Berlin',
            'weekly_schedule': {
                'monday': ['17:00-20:00'],
                'wednesday': ['17:00-20:00'],
                'friday': ['15:00-18:00'],
            },
        },
    },
    {
        'username': 'james.miller',
        'email': 'james.miller@acadbot.demo',
        'first_name': 'James',
        'last_name': 'Miller',
        'password': 'MentorPass123!',
        'career_slugs': ['cyber', 'ai'],
        'hourly_rate': '160.00',
        'bio': (
            'James is a Security Architect at a cloud-native cybersecurity startup, designing zero-trust '
            'architectures and ML-powered threat detection systems. He previously built detection logic for '
            'a managed detection and response (MDR) provider. He brings a practitioner\'s perspective on '
            'how ML models actually behave in production security environments—false positives, drift, '
            'and the operational reality of model deployment.'
        ),
        'availability_data': {
            'timezone': 'America/Denver',
            'weekly_schedule': {
                'tuesday': ['17:00-20:00'],
                'thursday': ['17:00-20:00'],
                'saturday': ['10:00-14:00'],
            },
        },
    },
]


class Command(BaseCommand):
    help = 'Seed mentor users and profiles for Cybersecurity and AI & Machine Learning career paths'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing mentor data for these careers before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing mentor data for Cybersecurity and AI & ML...')
            cyber_career = Career.objects.filter(slug='cyber').first()
            ai_career = Career.objects.filter(slug='ai').first()
            if cyber_career or ai_career:
                mentor_users = User.objects.filter(role=User.Role.MENTOR)
                for user in mentor_users:
                    if hasattr(user, 'mentor_profile'):
                        profile = user.mentor_profile
                        careers = list(profile.expertise_careers.all())
                        if any(c.slug in ['cyber', 'ai'] for c in careers):
                            user.delete()

        created_count = 0
        updated_count = 0

        for mentor_data in MENTOR_DATA:
            career_slugs = mentor_data.pop('career_slugs')
            availability_data = mentor_data.pop('availability_data')
            hourly_rate = mentor_data.pop('hourly_rate')
            bio = mentor_data.pop('bio')

            # Create or get user
            user, user_created = User.objects.get_or_create(
                email=mentor_data['email'],
                defaults={
                    **mentor_data,
                    'role': User.Role.MENTOR,
                    'is_verified': True,
                },
            )

            if user_created:
                user.set_password(mentor_data['password'])
                user.save()
                created_count += 1
                self.stdout.write(f'Created mentor user: {user.get_full_name()} ({user.email})')
            else:
                # Update existing user fields
                for key, value in mentor_data.items():
                    setattr(user, key, value)
                user.set_password(mentor_data['password'])
                user.save()
                updated_count += 1
                self.stdout.write(f'Updated mentor user: {user.get_full_name()} ({user.email})')

            # Create or update mentor profile
            profile, profile_created = MentorProfile.objects.get_or_create(
                user=user,
                defaults={
                    'hourly_rate': hourly_rate,
                    'bio': bio,
                    'availability_data': availability_data,
                    'is_verified': True,
                    'is_available': True,
                },
            )

            if not profile_created:
                profile.hourly_rate = hourly_rate
                profile.bio = bio
                profile.availability_data = availability_data
                profile.is_verified = True
                profile.is_available = True
                profile.save()

            # Link expertise careers
            careers = Career.objects.filter(slug__in=career_slugs)
            profile.expertise_careers.set(careers)

            career_names = ', '.join([c.name for c in careers])
            self.stdout.write(f'  Linked to careers: {career_names}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded mentors: {created_count} created, {updated_count} updated'
            )
        )