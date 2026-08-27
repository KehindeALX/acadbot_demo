"""
Management command to seed the 8 career paths with skills, roadmap stages, and interview questions.
"""
from django.core.management.base import BaseCommand
from apps.careers.models import Career, CareerSkill, RoadmapStage, InterviewQuestion


CAREER_DATA = [
    {
        'slug': 'data',
        'name': 'Data Analysis',
        'icon': '📊',
        'tag': 'High demand',
        'color': '#D4AF37',
        'description': 'Learn to collect, clean, analyze, and visualize data to drive business decisions.',
        'order': 1,
        'skills': [
            'Microsoft Excel / Google Sheets',
            'SQL & Database Querying',
            'Python for Data Analysis',
            'Data Visualization (Power BI / Tableau)',
            'Statistical Thinking',
        ],
        'roadmap': [
            {'title': 'Foundation', 'description': 'Learn Excel, SQL, and basic statistics. Understand how data is structured.', 'estimated_weeks': 4},
            {'title': 'Core Skills', 'description': 'Master Python (Pandas, NumPy), data cleaning, and exploratory analysis.', 'estimated_weeks': 6},
            {'title': 'Visualization', 'description': 'Build dashboards in Power BI or Tableau. Tell stories with data.', 'estimated_weeks': 4},
            {'title': 'Certification', 'description': 'Earn MSA Data Analysis Certification. Build 2 portfolio projects.', 'estimated_weeks': 4},
            {'title': 'Placement', 'description': 'Apply to roles via MSA Job Board. Interview prep with Abia.', 'estimated_weeks': 4},
        ],
        'interview_questions': [
            'Tell me about a time you used data to solve a problem.',
            'How do you handle missing or inconsistent data?',
            'Walk me through a dashboard you have built.',
            'What is the difference between correlation and causation?',
            'How would you explain your findings to a non-technical manager?',
        ],
    },
    {
        'slug': 'cyber',
        'name': 'Cybersecurity',
        'icon': '🔐',
        'tag': 'Fast growing',
        'color': '#FF6B6B',
        'description': 'Protect systems, networks, and data from digital attacks.',
        'order': 2,
        'skills': [
            'Networking Fundamentals',
            'Operating Systems (Linux/Windows)',
            'Ethical Hacking Basics',
            'Security Frameworks (NIST, ISO 27001)',
            'Incident Response',
        ],
        'roadmap': [
            {'title': 'Foundation', 'description': 'Understand networking, operating systems, and how attacks happen.', 'estimated_weeks': 4},
            {'title': 'Core Skills', 'description': 'Learn ethical hacking, penetration testing, and security tools like Wireshark, Kali Linux.', 'estimated_weeks': 6},
            {'title': 'Specialization', 'description': 'Choose a track: SOC Analyst, Pen Tester, or GRC (Governance, Risk, Compliance).', 'estimated_weeks': 4},
            {'title': 'Certification', 'description': 'Pursue CompTIA Security+ or CEH. MSA Cybersecurity Certification available.', 'estimated_weeks': 4},
            {'title': 'Placement', 'description': 'Apply to security roles. Practice with Abia on technical interview scenarios.', 'estimated_weeks': 4},
        ],
        'interview_questions': [
            'What is the difference between a virus and a worm?',
            'How would you respond to a phishing attack on an organization?',
            'Explain the CIA triad.',
            'What tools do you use for vulnerability scanning?',
            'How do you stay updated with the latest security threats?',
        ],
    },
    {
        'slug': 'software',
        'name': 'Software Dev',
        'icon': '💻',
        'tag': 'Top paying',
        'color': '#00C9B1',
        'description': 'Build web applications, APIs, and full-stack solutions.',
        'order': 3,
        'skills': [
            'HTML, CSS & JavaScript',
            'React or Vue.js',
            'Backend (Node.js / Python)',
            'Databases (SQL & NoSQL)',
            'Git & Version Control',
        ],
        'roadmap': [
            {'title': 'Frontend', 'description': 'Master HTML, CSS, and JavaScript. Build responsive websites.', 'estimated_weeks': 4},
            {'title': 'Framework', 'description': 'Learn React.js. Build interactive applications and SPAs.', 'estimated_weeks': 6},
            {'title': 'Backend', 'description': 'Learn Node.js or Python/Django. Understand APIs and databases.', 'estimated_weeks': 6},
            {'title': 'Full Stack', 'description': 'Connect frontend and backend. Deploy apps to cloud platforms.', 'estimated_weeks': 4},
            {'title': 'Placement', 'description': 'Build 3 portfolio projects. MSA certifies and connects you to employers.', 'estimated_weeks': 4},
        ],
        'interview_questions': [
            'What is the difference between REST and GraphQL?',
            'Explain how you would build a login system.',
            'What is version control and why is it important?',
            'How do you debug a problem in your code?',
            'Describe a project you built from scratch.',
        ],
    },
    {
        'slug': 'ai',
        'name': 'AI & Machine Learning',
        'icon': '🤖',
        'tag': 'Future-proof',
        'color': '#9B59B6',
        'description': 'Build intelligent systems with machine learning and deep learning.',
        'order': 4,
        'skills': [
            'Python Programming',
            'Mathematics (Linear Algebra, Statistics)',
            'Machine Learning Algorithms',
            'Deep Learning (TensorFlow/PyTorch)',
            'Prompt Engineering & LLMs',
        ],
        'roadmap': [
            {'title': 'Python & Math', 'description': 'Strong Python skills + linear algebra and statistics are your foundation.', 'estimated_weeks': 6},
            {'title': 'ML Fundamentals', 'description': 'Supervised, unsupervised learning. Scikit-learn. Model evaluation.', 'estimated_weeks': 6},
            {'title': 'Deep Learning', 'description': 'Neural networks, CNNs, RNNs. TensorFlow or PyTorch.', 'estimated_weeks': 6},
            {'title': 'LLMs & Agents', 'description': 'Work with large language models, prompt engineering, and agentic AI systems.', 'estimated_weeks': 4},
            {'title': 'Placement', 'description': 'MSA AI Certification + portfolio of projects = job-ready.', 'estimated_weeks': 4},
        ],
        'interview_questions': [
            'What is the difference between supervised and unsupervised learning?',
            'How do you handle overfitting in a model?',
            'Explain what a neural network is in simple terms.',
            'What experience do you have with large language models?',
            'How would you evaluate whether an AI model is performing well?',
        ],
    },
    {
        'slug': 'uiux',
        'name': 'UI/UX Design',
        'icon': '🎨',
        'tag': 'Creative + tech',
        'color': '#E91E8C',
        'description': 'Design beautiful, usable digital experiences.',
        'order': 5,
        'skills': [
            'Figma & Design Tools',
            'User Research Methods',
            'Wireframing & Prototyping',
            'Design Systems',
            'Usability Testing',
        ],
        'roadmap': [
            {'title': 'Design Basics', 'description': 'Learn design principles, typography, color theory, and visual hierarchy.', 'estimated_weeks': 4},
            {'title': 'Figma', 'description': 'Master Figma for wireframes, mockups, and interactive prototypes.', 'estimated_weeks': 4},
            {'title': 'UX Process', 'description': 'User research, personas, user journeys, and usability testing.', 'estimated_weeks': 6},
            {'title': 'Design Systems', 'description': 'Build and maintain component libraries. Work with developers.', 'estimated_weeks': 4},
            {'title': 'Placement', 'description': 'Portfolio of 3 case studies. MSA connects you with product teams.', 'estimated_weeks': 4},
        ],
        'interview_questions': [
            'Walk me through your design process from research to delivery.',
            'How do you handle feedback from developers or stakeholders?',
            'What is the difference between UI and UX?',
            'Show me a case study of a problem you solved with design.',
            'How do you design for users with limited digital literacy?',
        ],
    },
    {
        'slug': 'product',
        'name': 'Product Management',
        'icon': '🗺️',
        'tag': 'Leadership path',
        'color': '#FF9800',
        'description': 'Lead product strategy, roadmap, and cross-functional teams.',
        'order': 6,
        'skills': [
            'Product Strategy & Roadmapping',
            'User Story Writing',
            'Data-Driven Decision Making',
            'Stakeholder Management',
            'Agile & Scrum Methodologies',
        ],
        'roadmap': [
            {'title': 'PM Basics', 'description': 'Understand the product lifecycle, user personas, and how to define problems.', 'estimated_weeks': 4},
            {'title': 'Frameworks', 'description': 'Learn Agile, Scrum, and OKRs. Write user stories and PRDs.', 'estimated_weeks': 4},
            {'title': 'Data & Analytics', 'description': 'Use data to make product decisions. Learn basic SQL and analytics tools.', 'estimated_weeks': 4},
            {'title': 'Leadership', 'description': 'Manage cross-functional teams. Communicate vision to engineers and designers.', 'estimated_weeks': 6},
            {'title': 'Placement', 'description': 'MSA PM Certification + case study portfolio = product career.', 'estimated_weeks': 4},
        ],
        'interview_questions': [
            'How do you prioritize features when everything seems urgent?',
            'Tell me about a product you love and what you would improve.',
            'How do you gather user requirements?',
            'Describe a time you made a data-driven product decision.',
            'How do you work with engineers and designers?',
        ],
    },
    {
        'slug': 'digital',
        'name': 'Digital Marketing',
        'icon': '📱',
        'tag': 'Business impact',
        'color': '#2196F3',
        'description': 'Drive growth through digital channels and data-driven campaigns.',
        'order': 7,
        'skills': [
            'SEO & Content Strategy',
            'Social Media Marketing',
            'Google & Meta Ads',
            'Email Marketing',
            'Analytics (GA4)',
        ],
        'roadmap': [
            {'title': 'Foundations', 'description': 'Understand the digital marketing funnel, buyer personas, and content strategy.', 'estimated_weeks': 4},
            {'title': 'Channels', 'description': 'Master SEO, social media, email marketing, and paid ads.', 'estimated_weeks': 6},
            {'title': 'Analytics', 'description': 'Use Google Analytics 4, Meta Insights, and UTM tracking to measure results.', 'estimated_weeks': 4},
            {'title': 'Campaigns', 'description': 'Plan and run end-to-end marketing campaigns with clear KPIs.', 'estimated_weeks': 4},
            {'title': 'Placement', 'description': 'MSA Digital Marketing Certification + portfolio campaigns = hired.', 'estimated_weeks': 4},
        ],
        'interview_questions': [
            'How would you grow a brand from zero on social media?',
            'What metrics do you track to measure campaign success?',
            'How do you approach SEO for a new website?',
            'Describe a campaign you ran and its results.',
            'What tools do you use for digital marketing?',
        ],
    },
    {
        'slug': 'cloud',
        'name': 'Cloud Computing',
        'icon': '☁️',
        'tag': 'Infrastructure',
        'color': '#00BCD4',
        'description': 'Build and manage scalable cloud infrastructure.',
        'order': 8,
        'skills': [
            'Cloud Fundamentals (AWS/Azure/GCP)',
            'Networking in the Cloud',
            'Infrastructure as Code',
            'DevOps & CI/CD',
            'Cloud Security',
        ],
        'roadmap': [
            {'title': 'Cloud Basics', 'description': 'Understand cloud concepts: IaaS, PaaS, SaaS. Choose AWS, Azure, or GCP.', 'estimated_weeks': 4},
            {'title': 'Core Services', 'description': 'Learn compute, storage, networking, and databases in your chosen cloud.', 'estimated_weeks': 6},
            {'title': 'DevOps', 'description': 'CI/CD pipelines, Docker, Kubernetes, and Infrastructure as Code (Terraform).', 'estimated_weeks': 6},
            {'title': 'Security', 'description': 'Cloud security best practices, IAM, compliance, and monitoring.', 'estimated_weeks': 4},
            {'title': 'Certification', 'description': 'AWS Cloud Practitioner or Azure Fundamentals. MSA supports your prep.', 'estimated_weeks': 4},
        ],
        'interview_questions': [
            'What is the difference between IaaS, PaaS, and SaaS?',
            'How do you secure a cloud environment?',
            'Explain what a VPC is and why it matters.',
            'What is Infrastructure as Code and why use it?',
            'How would you reduce cloud costs for a startup?',
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed the database with 8 career paths, skills, roadmap stages, and interview questions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing career data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing career data...')
            Career.objects.all().delete()

        created_count = 0
        updated_count = 0

        for career_data in CAREER_DATA:
            skills_data = career_data.pop('skills')
            roadmap_data = career_data.pop('roadmap')
            questions_data = career_data.pop('interview_questions')

            career, created = Career.objects.update_or_create(
                slug=career_data['slug'],
                defaults=career_data,
            )

            if created:
                created_count += 1
                self.stdout.write(f'Created career: {career.name}')
            else:
                updated_count += 1
                self.stdout.write(f'Updated career: {career.name}')

            # Create skills
            for order, skill_name in enumerate(skills_data):
                CareerSkill.objects.update_or_create(
                    career=career,
                    name=skill_name,
                    defaults={'order': order, 'is_core': True},
                )

            # Create roadmap stages
            for order, stage_data in enumerate(roadmap_data):
                RoadmapStage.objects.update_or_create(
                    career=career,
                    order=order + 1,
                    defaults={
                        'title': stage_data['title'],
                        'description': stage_data['description'],
                        'estimated_weeks': stage_data['estimated_weeks'],
                    },
                )

            # Create interview questions
            for order, question_text in enumerate(questions_data):
                InterviewQuestion.objects.update_or_create(
                    career=career,
                    order=order + 1,
                    defaults={
                        'question': question_text,
                        'difficulty': 'MEDIUM',
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully seeded careers: {created_count} created, {updated_count} updated'
            )
        )