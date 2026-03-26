from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mothers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mother',
            name='is_doctor',
            field=models.BooleanField(default=False),
        ),
    ]
