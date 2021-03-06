# Generated by Django 2.1 on 2019-02-28 20:18

import datetime
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import mptt.fields
import re
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('pykol', '0027_private_storage'),
    ]

    operations = [
        migrations.CreateModel(
            name='Compte',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100)),
                ('categorie', models.SmallIntegerField(choices=[(0, 'compte de dépenses'), (1, "compte d'actifs"), (2, 'compte de revenus'), (3, 'compte de dettes'), (4, 'compte de fonds propres')], verbose_name='type de compte')),
                ('lft', models.PositiveIntegerField(db_index=True, editable=False)),
                ('rght', models.PositiveIntegerField(db_index=True, editable=False)),
                ('tree_id', models.PositiveIntegerField(db_index=True, editable=False)),
                ('level', models.PositiveIntegerField(db_index=True, editable=False)),
                ('parent', mptt.fields.TreeForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sous_comptes', to='pykol.Compte')),
                ('gestionnaires', models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL)),
                ('decouvert_autorise',models.BooleanField(default=False, help_text="Ce champ indique si le compte peut être à découvert. Dans ce cas, on peut limiter le nombre d'heures du découvert en donnant des valeurs non nulles aux durées à découvert autorisées.", verbose_name='découvert autorisé')),
                ('decouvert_duree', models.DurationField(blank=True, null=True, verbose_name='durée à découvert autorisée', help_text="Lorsque le découvert est autorisé sur ce compte, ce champ donne une limite sur le nombre d'heures comptabilisées négativement. Par exemple, si ce champ vaut 3h, le solde du compte devra toujours être supérieur ou égal à -3h.")),
                ('decouvert_duree_interrogation', models.DurationField(blank=True, null=True, verbose_name="durée d'interrogation à découvert autorisée")),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Lettrage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(default=django.utils.timezone.now)),
                ('mode', models.PositiveSmallIntegerField(choices=[(0, 'partiel'), (1, 'total')], default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Mouvement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(default=django.utils.timezone.now)),
                ('motif', models.CharField(max_length=100)),
                ('etat', models.SmallIntegerField(choices=[(0, 'brouillon'), (1, 'validé')], default=0, verbose_name='état')),
                ('annee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pykol.Annee')),
                ('colle', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pykol.Colle')),
            ],
        ),
        migrations.CreateModel(
            name='MouvementLigne',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('taux', models.PositiveSmallIntegerField(blank=True, null=True, choices=[(1, '1è année - Moins de 20 étudiants'), (2, '1è année - Entre 21 et 35 étudiants'), (3, '1è année - Plus de 35 étudiants'), (4, '2è année - Moins de 20 étudiants'), (5, '2è année - Entre 21 et 35 étudiants'), (6, '2è année - Plus de 35 étudiants')], verbose_name='taux')),
                ('duree_interrogation', models.DurationField(default=datetime.timedelta, verbose_name="durée d'interrogation")),
                ('duree', models.DurationField(default=datetime.timedelta, verbose_name="nombre d'heures")),
                ('motif', models.CharField(max_length=100, blank=True)),
                ('compte', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lignes', to='pykol.Compte')),
                ('lettrage', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lignes', to='pykol.Lettrage')),
                ('mouvement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lignes', to='pykol.Mouvement')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='academie',
            name='departements',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator(re.compile('^\\d+(?:,\\d+)*\\Z'), code='invalid', message='Enter only digits separated by commas.')], verbose_name='départements'),
        ),
    ]
