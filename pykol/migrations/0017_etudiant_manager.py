# Generated by Django 2.1 on 2018-11-11 06:40

from django.db import migrations, models
import pykol.models.base.utilisateurs


class Migration(migrations.Migration):

    dependencies = [
        ('pykol', '0016_releve_etat_asie'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='etudiant',
            managers=[
                ('objects', pykol.models.base.utilisateurs.EtudiantManager()),
            ],
        ),
    ]

