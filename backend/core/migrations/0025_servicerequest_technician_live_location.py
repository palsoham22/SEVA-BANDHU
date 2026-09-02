from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_chatconversation_chatmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='servicerequest',
            name='technician_latitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='servicerequest',
            name='technician_longitude',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='servicerequest',
            name='technician_location_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
