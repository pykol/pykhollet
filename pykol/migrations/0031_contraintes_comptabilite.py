# -*- coding: utf-8 -*-

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

	dependencies = [
		('pykol', '0030_peupler_init_comptabilite'),
	]

	operations = [
		migrations.AlterField(
			model_name='academie',
			name='compte_dotation',
			field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rectorat', to='pykol.Compte'),
		),
		migrations.AlterField(
			model_name='academie',
			name='compte_paiement',
			field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='asie', to='pykol.Compte'),
		),
		migrations.AlterField(
			model_name='etablissement',
			name='compte_colles',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='etablissement_dotation', to='pykol.Compte'),
			preserve_default=False,
		),
		migrations.AlterField(
			model_name='etablissement',
			name='compte_releves',
			field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='etablissement_releves', to='pykol.Compte'),
			preserve_default=False,
		),
		migrations.AlterField(
			model_name='classe',
			name='compte_colles',
			field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='pykol.Compte'),
			preserve_default=False,
		),
        migrations.AlterField(
            model_name='collesenseignement',
            name='compte_colles',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='pykol.Compte'),
            preserve_default=False,
        ),
		migrations.AlterField(
			model_name='professeur',
			name='compte_effectue',
			field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='professeur_effectue', to='pykol.Compte'),
			preserve_default=False,
		),
		migrations.AlterField(
			model_name='professeur',
			name='compte_prevu',
			field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='professeur_prevues', to='pykol.Compte'),
			preserve_default=False,
		),
		migrations.AlterField(
			model_name='collereleve',
			name='compte_colles',
			field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='pykol.Compte'),
			preserve_default=False,
		),
		migrations.AlterField(
			model_name='collereleveligne',
			name='mouvement_ligne',
			field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='pykol.MouvementLigne'),
			preserve_default=False,
		),
	]
