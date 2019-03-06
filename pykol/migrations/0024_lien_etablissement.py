# Generated by Django 2.1 on 2019-03-02 14:04

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

def rattache_classe_etablissement(apps, schema_editor):
	Etablissement = apps.get_model('pykol', 'Etablissement')
	Classe = apps.get_model('pykol', 'Classe')
	etab = Etablissement.objects.get(numero_uai=settings.PYKOL_UAI_DEFAUT)
	Classe.objects.filter(etablissement__isnull=True).update(etablissement=etab)

def reverse_rattache_classe_etablissement(apps, schema_editor):
	# Il n'y a rien à faire pour inverser la fonction précédente, car la
	# migration supprime tout simplement le champ etablissement des
	# classes.
	pass

def rattache_collereleve_etablissement(apps, schema_editor):
	Etablissement = apps.get_model('pykol', 'Etablissement')
	ColleReleve = apps.get_model('pykol', 'ColleReleve')
	etab = Etablissement.objects.get(numero_uai=settings.PYKOL_UAI_DEFAUT)
	ColleReleve.objects.filter(etablissement__isnull=True).update(etablissement=etab)

def reverse_rattache_collereleve_etablissement(apps, schema_editor):
	# Il n'y a rien à faire pour inverser la fonction précédente, car la
	# migration supprime tout simplement le champ etablissement des
	# collereleves.
	pass

class Migration(migrations.Migration):

	dependencies = [
		('pykol', '0023_comptabilite'),
	]

	operations = [
		migrations.AddField(
			model_name='classe',
			name='etablissement',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pykol.Etablissement'),
			preserve_default=False,
		),
		migrations.RunPython(rattache_classe_etablissement, reverse_rattache_classe_etablissement),
		migrations.AlterField(
			model_name='classe',
			name='etablissement',
			field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pykol.Etablissement'),
			preserve_default=False,
		),

		migrations.AddField(
			model_name='collereleve',
			name='etablissement',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pykol.Etablissement'),
			preserve_default=False,
		),
		migrations.RunPython(rattache_collereleve_etablissement, reverse_rattache_collereleve_etablissement),
		migrations.AlterField(
			model_name='collereleve',
			name='etablissement',
			field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pykol.Etablissement'),
			preserve_default=False,
		),
	]