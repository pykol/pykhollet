# -*- coding: utf-8

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2018 Florian Hatat
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Vues de manipulation des semaines de colles."""

from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction, models
from django.core.exceptions import PermissionDenied

from pykol.models.base import Classe
from pykol.models.colles import Semaine, CollesReglages
from pykol.forms.colloscope import SemaineFormSet, \
		SemaineNumeroGenerateurForm

@login_required
def semaines(request, slug):
	"""
	Vue qui permet de créer la liste des semaines de colle pour une
	classe donnée.

	Au lieu de saisir toutes les semaines une à une, cette vue propose
	la liste de l'ensemble des semaines (démarrant les lundis) de
	l'année scolaire en cours. Le professeur en charge du colloscope
	peut alors sélectionner celles qui figureront effectivement dans le
	colloscope de la classe. Il peut numéroter les semaines manuellement
	ou bien fournir un format pour générer automatiquement les numéros.
	"""
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.change_colloscope', classe):
		raise PermissionDenied

	try:
		colles_reglages = CollesReglages.objects.get(classe=classe)
	except CollesReglages.DoesNotExist:
		colles_reglages = CollesReglages(classe=classe)
		colles_reglages.save()

	formset_prefix = "semaines"

	if request.method == 'POST':
		formset = SemaineFormSet(request.POST, prefix=formset_prefix,
					form_kwargs={'classe': classe})
		genform = SemaineNumeroGenerateurForm(request.POST,
				instance=colles_reglages, prefix="gen")


		genform.save()

		if genform.is_valid() and genform.cleaned_data['numeros_auto']:
			formset.full_clean()
			new_formset_data = {}

			id_colle = 0

			for id_semaine, form in enumerate(formset.forms):
				for field in ('debut', 'fin', 'est_colle'):
					new_formset_data['{prefix}-{id_semaine}-{field}'.format(
						prefix=formset_prefix,
						id_semaine=id_semaine,
						field=field)] = form.cleaned_data.get(field)

				if form.cleaned_data.get('semaine'):
					new_formset_data['{prefix}-{id_semaine}-{field}'.format(
						prefix=formset_prefix,
						id_semaine=id_semaine,
						field='semaine')] = form.cleaned_data.get('semaine').pk

				if form.cleaned_data['est_colle']:
					new_formset_data['{prefix}-{id_semaine}-{field}'.format(
						prefix=formset_prefix,
						id_semaine=id_semaine,
						field='numero')] = \
							genform.cleaned_data['numeros_format'].format(
							numero=id_colle + 1,
							quinzaine=id_colle // 2 + 1,
							parite=(id_colle + 1) % 2,
							parite_alpha='AB'[id_colle % 2])

					id_colle += 1

			for field in ('TOTAL_FORMS', 'INITIAL_FORMS',
					'MAX_NUM_FORMS',):
				field_name = '{prefix}-{field}'.format(prefix=formset_prefix,
						field=field)
				new_formset_data[field_name] = formset.data[field_name]

			# On ne remplace le formset que si le générateur a réussi à
			# compléter les semaines manquantes
			formset = SemaineFormSet(new_formset_data,
					prefix=formset_prefix,
					form_kwargs={'classe': classe})

		if formset.is_valid():
			with transaction.atomic():
				for id_semaine, data in enumerate(formset.cleaned_data):
					if data['semaine']:
						if data['est_colle']:
							semaine = data['semaine']
							semaine.debut = data['debut']
							semaine.fin = data['fin']
							semaine.numero = data['numero']
							semaine.save()
						else:
							data['semaine'].delete()

					elif data['est_colle']:
						Semaine(debut=data['debut'],
								fin=data['fin'],
								numero=data['numero'],
								classe=classe).save()

			return redirect('colloscope_semaines', classe.slug)

	else:
		# Calcul des semaines de toute l'année
		toutes_semaines = []

		# Générateur pour itérer tous les lundis de l'année
		def lundirange():
			annee = classe.annee
			lundi = annee.debut - timedelta(days=annee.debut.weekday())
			while lundi < annee.fin:
				if not annee.est_vacances(lundi):
					yield lundi
				lundi += timedelta(days=7)

		# On récupère déjà la liste des semaines existantes
		toutes_semaines = list(Semaine.objects.filter(classe=classe).annotate(
			semaine=models.F('pk'), est_colle=models.Value(True,
				output_field=models.BooleanField()),
			).values('debut', 'fin', 'est_colle', 'numero', 'semaine'))

		# On prévoit des semaines vides si l'utilisateur souhaite les
		# cocher, pour les lundis qui manquent.
		lundis_existants = set([s['debut'] for s in toutes_semaines])

		for lundi in lundirange():
			if lundi in lundis_existants:
				continue
			toutes_semaines.append({
				'debut': lundi,
				'fin': lundi + timedelta(days=6),
				'est_colle': False,
				'numero': None,
			})

		toutes_semaines.sort(key=lambda s: s['debut'])

		formset = SemaineFormSet(initial=toutes_semaines,
				prefix=formset_prefix,
				form_kwargs={'classe': classe})
		genform = SemaineNumeroGenerateurForm(
				instance=colles_reglages,
				prefix="gen")

	return render(request, 'pykol/colloscope/semaines.html',
			context={
				'classe': classe,
				'formset': formset,
				'genform': genform,
				})

