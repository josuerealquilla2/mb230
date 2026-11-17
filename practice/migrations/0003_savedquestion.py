from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("practice", "0002_user_accounts_and_progress"),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_by", to="practice.question")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_questions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["question__pdf_order"]},
        ),
        migrations.AddConstraint(
            model_name="savedquestion",
            constraint=models.UniqueConstraint(fields=("user", "question"), name="uq_saved_question_user"),
        ),
    ]
