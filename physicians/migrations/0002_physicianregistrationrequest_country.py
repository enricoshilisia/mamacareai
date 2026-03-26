from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('physicians', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='physicianregistrationrequest',
            name='country',
            field=models.CharField(default='Kenya', max_length=100),
        ),
    ]
