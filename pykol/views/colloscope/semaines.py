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
from django.db import transaction
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

		formset_data = formset.data.copy()

		genform.save()

		if genform.is_valid() and genform.cleaned_data['numeros_auto']:
			formset.full_clean()

			id_colle = 0

			for id_semaine, form in enumerate(formset.forms):
				for field in ('debut', 'fin', 'est_colle',):
					formset_data['semaines-{}-{}'.format(id_semaine,
						field)] = form.cleaned_data.get(field)

				if form.cleaned_data['est_colle']:
					formset_data['semaines-{}-numero'.format(id_semaine)] = \
							genform.cleaned_data['numeros_format'].format(
							numero=id_colle + 1,
							quinzaine=id_colle // 2 + 1,
							parite=(id_colle + 1) % 2,
							parite_alpha='AB'[id_colle % 2])

					id_colle += 1

			for field in ('TOTAL_FORMS', 'INITIAL_FORMS',
					'MAX_NUM_FORMS',):
				field_name = '{}-{}'.format(formset_prefix, field)
				formset_data[field_name] = formset.data[field_name]

			# On ne remplace le formset que si le générateur a réussi à
			# compléter les semaines manquantes
			new_formset = SemaineFormSet(formset_data,
					prefix=formset_prefix,
					form_kwargs={'classe': classe})
			if new_formset.is_valid():
				formset = new_formset

		if formset.is_valid():
			with transaction.atomic():
				for id_semaine, data in enumerate(formset.cleaned_data):
					if not data['est_colle']:
						formset_data['{}-{}-numero'.format(formset_prefix,
							id_semaine)] = None

					if data['semaine'] and not data['est_colle']:
						formset_data['{}-{}-semaine'.format(formset_prefix,
							id_semaine)] = None
						data['semaine'].delete()

					if not data['semaine'] and data['est_colle']:
						semaine = Semaine(debut=data['debut'],
								fin=data['fin'],
								numero=data['numero'],
								classe=classe)
						semaine.save()
						formset_data['{}-{}-semaine'.format(formset_prefix,
							id_semaine)] = semaine.pk

					if data['semaine'] and data['est_colle']:
						semaine = data['semaine']
						semaine.debut = data['debut']
						semaine.fin = data['fin']
						semaine.numero = data['numero']
						semaine.save()

			formset = SemaineFormSet(formset_data,
					prefix=formset_prefix,
					form_kwargs={'classe': classe})

	else:
		annee = classe.annee
		# Calcul des semaines de toute l'année
		lundi = annee.debut - timedelta(days=annee.debut.weekday())
		toutes_semaines = []
		while lundi < annee.fin:
			try:
				semaine = Semaine.objects.get(classe=classe, debut=lundi)
				toutes_semaines.append({
					'debut': semaine.debut,
					'fin': semaine.fin,
					'est_colle': True,
					'numero': semaine.numero,
					'semaine': semaine,
					})
			except Semaine.DoesNotExist:
				toutes_semaines.append({
					'debut': lundi,
					'fin': lundi + timedelta(days=6),
					'est_colle': False,
					'numero': None,
					})
			lundi += timedelta(days=7)
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

