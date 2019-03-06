# Generated by Django 2.1 on 2019-02-28 20:48
"""
Intégration de liens vers la comptabilité dans les modèles existants.
"""

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

	dependencies = [
		('pykol', '0024_lien_etablissement'),
	]

	operations = [
		migrations.AddField(
			model_name='academie',
			name='compte_dotation',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rectorat', to='pykol.Compte'),
			preserve_default=False,
		),
		migrations.AddField(
			model_name='academie',
			name='compte_paiement',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='asie', to='pykol.Compte'),
			preserve_default=False,
		),
		migrations.AddField(
			model_name='etablissement',
			name='compte_colles',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='etablissement_dotation', to='pykol.Compte'),
			preserve_default=False,
		),
		migrations.AddField(
			model_name='etablissement',
			name='compte_releves',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='etablissement_releves', to='pykol.Compte'),
			preserve_default=False,
		),
		migrations.AddField(
			model_name='classe',
			name='compte_colles',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pykol.Compte'),
			preserve_default=False,
		),
        migrations.AddField(
            model_name='collesenseignement',
            name='compte_colles',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pykol.Compte'),
            preserve_default=False,
        ),
		migrations.AddField(
			model_name='professeur',
			name='compte_effectue',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='professeur_effectue', to='pykol.Compte'),
			preserve_default=False,
		),
		migrations.AddField(
			model_name='professeur',
			name='compte_prevu',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='professeur_prevues', to='pykol.Compte'),
			preserve_default=False,
		),
        migrations.AlterField(
            model_name='collereleveligne',
            name='taux',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, '1è année - Moins de 20 étudiants'), (2, '1è année - Entre 21 et 35 étudiants'), (3, '1è année - Plus de 35 étudiants'), (4, '2è année - Moins de 20 étudiants'), (5, '2è année - Entre 21 et 35 étudiants'), (6, '2è année - Plus de 35 étudiants')], null=True, verbose_name='taux'),
        ),
		migrations.AddField(
			model_name='collereleve',
			name='compte_colles',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pykol.Compte'),
			preserve_default=False,
		),
		migrations.AddField(
			model_name='collereleveligne',
			name='mouvement_ligne',
			field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pykol.MouvementLigne'),
			preserve_default=False,
		),
	]
