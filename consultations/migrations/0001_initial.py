import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("chat",       "0001_initial"),
        ("mothers",    "0002_mother_is_doctor"),
        ("physicians", "0003_physician_user_registrationrequest_user"),
    ]

    operations = [
        migrations.CreateModel(
            name="Consultation",
            fields=[
                ("id",         models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("symptoms",   models.TextField(help_text="Summary of symptoms from AI assessment")),
                ("severity",   models.CharField(choices=[("mild","Mild"),("moderate","Moderate"),("severe","Severe"),("critical","Critical")], max_length=10)),
                ("specialist", models.CharField(blank=True, max_length=30, help_text="e.g. pediatrician")),
                ("ai_summary", models.TextField(blank=True, help_text="AI clinical summary generated on accept")),
                ("status",     models.CharField(choices=[("pending","Pending"),("accepted","Accepted"),("declined","Declined"),("completed","Completed")], default="pending", max_length=10)),
                ("mother_lat", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("mother_lon", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("mother",     models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="consultations", to=settings.AUTH_USER_MODEL)),
                ("physician",  models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="consultations", to="physicians.physician")),
                ("child",      models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="consultations", to="mothers.child")),
                ("conversation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="consultations", to="chat.conversation")),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Consultation", "verbose_name_plural": "Consultations"},
        ),
        migrations.CreateModel(
            name="ConsultationMessage",
            fields=[
                ("id",          models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("sender_type", models.CharField(choices=[("mother","Mother"),("doctor","Doctor")], max_length=10)),
                ("content",     models.TextField()),
                ("created_at",  models.DateTimeField(auto_now_add=True)),
                ("consultation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="consultations.consultation")),
            ],
            options={"ordering": ["created_at"], "verbose_name": "Consultation Message", "verbose_name_plural": "Consultation Messages"},
        ),
    ]
