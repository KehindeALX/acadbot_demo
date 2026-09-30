from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0002_course_content_reviewed_certificate'),
    ]

    operations = [
        migrations.AddField(
            model_name='lessonprogress',
            name='first_quiz_correct',
            field=models.BooleanField(blank=True, null=True, verbose_name='first quiz correct'),
        ),
    ]
