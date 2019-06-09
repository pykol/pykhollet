# Generated by Django 2.2.1 on 2019-06-09 14:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pykol', '0034_dotation_etablissement'),
    ]

    operations = [
        migrations.AddField(
            model_name='colle',
            name='duree_etudiant',
            field=models.DurationField(blank=True, null=True, verbose_name='durée de passage par étudiant'),
        ),
        migrations.AddField(
            model_name='creneau',
            name='duree_etudiant',
            field=models.DurationField(blank=True, null=True, verbose_name='durée de passage par étudiant'),
        ),
    ]
