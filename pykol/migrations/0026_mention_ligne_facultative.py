# Generated by Django 2.1 on 2019-04-14 13:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pykol', '0025_etablissement_ville'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mention',
            name='grille_lignes',
            field=models.ManyToManyField(blank=True, to='pykol.GrilleLigne'),
        ),
    ]
