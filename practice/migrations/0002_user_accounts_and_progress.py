import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("practice", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="translations",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="practicesession",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="practice_sessions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="practicesession",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.CreateModel(
            name="UserPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "theme",
                    models.CharField(
                        choices=[("system", "System"), ("light", "Light"), ("dark", "Dark")],
                        default="system",
                        max_length=12,
                    ),
                ),
                ("show_translation", models.BooleanField(default=True)),
                ("default_session_size", models.PositiveSmallIntegerField(default=463)),
                ("onboarding_completed", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="preferences",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
