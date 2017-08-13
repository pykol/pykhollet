# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-08-03 13:18
from __future__ import unicode_literals

import base.models.etablissement
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0002_auto_20170725_1610'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='enseignement',
            options={'ordering': ['groupe', 'matiere']},
        ),
        migrations.RemoveField(
            model_name='classe',
            name='matieres',
        ),
        migrations.RemoveField(
            model_name='enseignement',
            name='classe',
        ),
        migrations.RemoveField(
            model_name='groupe',
            name='enseignements',
        ),
        migrations.AddField(
            model_name='classe',
            name='enseignements',
            field=models.ManyToManyField(blank=True, to='base.Enseignement'),
        ),
        migrations.AddField(
            model_name='enseignement',
            name='groupe',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='base.Groupe'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='groupe',
            name='slug',
            field=models.SlugField(default=''),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='etablissement',
            name='numero_uai',
            field=models.CharField(max_length=8, primary_key=True, serialize=False, unique=True, validators=[django.core.validators.RegexValidator(message="Un numéro UAI doit être constitué de sept chiffres suivis d'une lettre code", regex='\\d{7,7}[a-zA-Z]'), base.models.etablissement.validateur_lettre23], verbose_name='UAI'),
        ),
        migrations.AlterField(
            model_name='etudiant',
            name='ine',
            field=models.CharField(max_length=11, validators=[django.core.validators.RegexValidator(message="Un numéro INE doit être constitué de dix chiffres suivis d'une lettre code", regex='\\d{10,10}[a-zA-Z]'), base.models.etablissement.validateur_lettre23], verbose_name="INE (numéro d'étudiant)"),
        ),
        migrations.AlterField(
            model_name='etudiant',
            name='options',
            field=models.ManyToManyField(blank=True, to='base.Matiere'),
        ),
        migrations.AlterField(
            model_name='groupe',
            name='etudiants',
            field=models.ManyToManyField(blank=True, to='base.Etudiant', verbose_name='étudiants'),
        ),
    ]
