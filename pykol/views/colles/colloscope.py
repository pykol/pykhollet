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

from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.forms import formset_factory
from django.contrib import messages

from pykol.models.base import Classe
from pykol.models.colles import Semaine, CollesReglages, Creneau
from pykol.forms.colloscope import SemaineFormSet, \
		SemaineNumeroGenerateurForm, \
		CreneauFormSet, CreneauSansClasseFormSet, \
		TrinomeForm

@login_required
def colloscope_home(request):
	return render(request, 'pykol/base.html')

@login_required
def colloscope(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	semaines = classe.semaine_set.order_by('debut')
	creneaux = classe.creneau_set.order_by('matiere', 'jour', 'debut')
	return render(request, 'pykol/colles/colloscope.html',
			context={
				'classe': classe,
				'semaines': semaines,
				'creneaux' : creneaux,
				})

@login_required
def trinomes(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.add_colle', classe):
		raise PermissionDenied

	trinomes = classe.trinomes
	etudiants = classe.etudiant_set.order_by('last_name', 'first_name')
	initial = []
	for etudiant in etudiants:
		initial.append({
			'etudiant': etudiant,
			'groupes': ','.join([g[0] for g in
				trinomes.filter(etudiants=etudiant).values_list('nom')]),
			})

	TrinomeFormSet = formset_factory(TrinomeForm, can_delete=False, extra=0,
		can_order=False, max_num=len(etudiants), min_num=len(etudiants))

	if request.method == 'POST':
		formset = TrinomeFormSet(request.POST, form_kwargs={'queryset':
			etudiants}, initial=initial)
		if formset.is_valid():
			# On construit d'abord le dictionnaire qui à chaque trinôme
			# associe la liste des étudiants membres
			trinomes_membres = {}
			for form in formset:
				etudiant = form.cleaned_data['etudiant']
				for groupe in form.cleaned_data['groupes']:
					trinomes_membres.setdefault(groupe, []).append(etudiant)
			# On met ensuite à jour la liste des trinômes
			for groupe in trinomes_membres:
				trinome, _ = trinomes.update_or_create(dans_classe=classe, nom=groupe,
						defaults={})
				trinome.etudiants.set(trinomes_membres[groupe])
				trinome.save()

			messages.success(request, "Les groupes de colles en "
					" {classe} ont été mis à jour.".format(
						classe=classe))
			return redirect('colloscope_trinomes', classe.slug)
	else:
		formset = TrinomeFormSet(initial=initial,
				form_kwargs={'queryset': etudiants})

	return render(request, 'pykol/colles/trinomes.html',
			context={'formset': formset,
				'classe': classe,})

@login_required
def create_trinome(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.add_colle', classe):
		raise PermissionDenied

	return render(request, 'pykol/base.html')

#@object_permission_required(Classe, 'pykol.colloscope.complet', 'slug')
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
	if not request.user.has_perm('pykol.add_colle', classe):
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
						field)] = form.cleaned_data[field]

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

			formset = SemaineFormSet(formset_data,
					prefix=formset_prefix,
					form_kwargs={'classe': classe})

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
				semaine = Semaine.objects.get(debut=lundi)
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

	return render(request, 'pykol/colles/semaines.html',
			context={
				'classe': classe,
				'formset': formset,
				'genform': genform,
				})

@login_required
def colle_creer(request, slug):
	"""Créer une colle dans une classe donnée"""
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.add_colle', classe):
		raise PermissionDenied

	pass

@login_required
def colle_supprimer(request, pk):
	"""Supprimer une colle"""
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.delete_colle', classe):
		raise PermissionDenied

	pass

@login_required
def creneaux(request, slug):
	"""Liste des créneaux de colles pour une classe"""
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.add_colle', classe):
		raise PermissionDenied

	creneaux_qs = Creneau.objects.filter(classe=classe).order_by('matiere',
			'colleur', 'jour', 'debut')

	if request.method == 'POST':
		formset = CreneauSansClasseFormSet(request.POST, queryset=creneaux_qs,
					form_kwargs={'classe': classe})

		if formset.is_valid():
			creneaux = formset.save(commit=False)
			for creneau in creneaux:
				creneau.classe = classe
				creneau.save()
			for creneau in formset.deleted_objects:
				creneau.delete()

			return redirect('colloscope_creneaux', slug=classe.slug)

	else:
		formset = CreneauSansClasseFormSet(queryset=creneaux_qs, form_kwargs={'classe': classe})

	return render(request, 'pykol/colles/creneaux.html', context={
		'classe': classe,
		'formset': formset})

@login_required
@permission_required('pykol.direction')
def creneau_list_direction(request):
	"""Gestion de tous les créneaux de colle par la direction"""
	creneaux_qs = Creneau.objects.order_by('jour', 'colleur', 'debut')

	if request.method == 'POST':
		formset = CreneauFormSet(request.POST, queryset=creneaux_qs)

		if formset.is_valid():
			formset.save()

	else:
		formset = CreneauFormSet(queryset=creneaux_qs)

	return render(request, 'pykol/direction/creneau_list.html',
			context={'formset': formset})

@login_required
def creneau_supprimer(request, pk):
	"""Suppression d'un créneau de colle"""
	if not request.user.has_perm('pykol.delete_creneau', classe):
		raise PermissionDenied

	pass
