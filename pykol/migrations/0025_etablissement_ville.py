# Generated by Django 2.1 on 2019-03-31 16:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pykol', '0024_ects'),
    ]

    operations = [
        migrations.AddField(
            model_name='etablissement',
            name='ville',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
