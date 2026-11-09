from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('control', '0019_runnerjob_runnerchunk'),
    ]

    operations = [
        migrations.AlterField(
            model_name='run',
            name='profile',
            field=models.CharField(choices=[('sensor', 'Sensor'), ('job', 'Job'), ('mailbox', 'Mailbox')], default='sensor', max_length=16),
        ),
    ]
