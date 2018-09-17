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
from collections import defaultdict, OrderedDict

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.contrib import messages

from pykol.models.base import Classe
from pykol.models.colles import Creneau, Colle
from pykol.forms.colloscope import CreneauSalleFormSet, \
		CreneauSansClasseFormSet, \
		ColleForm, ColleSupprimerForm

@login_required
def colloscope_home(request):
	return render(request, 'pykol/base.html')

@login_required
def colle_creer(request, slug):
	"""Créer une colle dans une classe donnée"""
	classe = get_object_or_404(Classe, slug=slug)

	# On vérifie à priori que l'utilisateur a le droit de créer une
	# colle dans la classe. Pour l'instant, il n'y a aucun moyen de
	# tester si ce droit est accordé uniquement pour sa matière.
	if not request.user.has_perm('pykol.add_colle', classe):
		raise PermissionDenied

	if request.method == 'POST':
		form = ColleForm(request.POST, classe=classe)
		if form.is_valid():
			colle = Colle(
				classe=classe,
				enseignement=form.cleaned_data['enseignement_dote']['enseignement'],
				colles_ens=form.cleaned_data['enseignement_dote']['collesenseignement'],
				mode=form.cleaned_data['mode'],
				creneau=form.cleaned_data['creneau'],
				semaine=form.cleaned_data['semaine'],
				groupe=form.cleaned_data['trinome']
			)
			# Le calcul de durée dépend du mode d'interrogation. Pour
			# une colle notée, on laisse la durée par défaut. Pour une
			# colle en mode TD, on prend la durée indiquée dans le
			# formulaire si elle est indiquée.
			if form.cleaned_data['mode'] == Colle.MODE_TD and \
					form.cleaned_data.get('duree'):
				colle.duree = form.cleaned_data['duree']

			# La matière est connue, à ce niveau du code, on vérifie que
			# l'utilisateur peut effectivement créer la colle.
			if not request.user.has_perm('pykol.add_colle', colle):
				raise PermissionDenied

			colle.save()

			etudiants = form.cleaned_data['etudiants'] or \
				form.cleaned_data['trinome'].etudiants
			horaire = form.cleaned_data['horaire'] or \
				form.cleaned_data['semaine'].horaire_creneau(
					form.cleaned_data['creneau'])
			colle.ajout_details(horaire=horaire,
				colleur=form.cleaned_data['colleur'],
				etudiants=etudiants.all(),
				salle=form.cleaned_data['salle'])

			return redirect('colloscope', slug=classe.slug)
	else:
		form = ColleForm(classe=classe)

	return render(request, 'pykol/colles/cree_colle.html',
			context={
				'classe': classe,
				'form': form,
			})

@login_required
def colle_supprimer(request, pk):
	"""Supprimer une colle"""
	colle = get_object_or_404(Colle, pk=pk)
	if not request.user.has_perm('pykol.delete_colle', colle):
		raise PermissionDenied

	classe = colle.classe
	if request.method == 'POST':
		form = ColleSupprimerForm(request.POST, instance=colle)
		if form.is_valid():
			if colle.etat in (Colle.ETAT_ANNULEE,
					Colle.ETAT_BROUILLON, Colle.ETAT_PREVUE):
				colle.delete()
			else:
				messages.error(request, "Vous ne pouvez pas supprimer "
						"une colle qui a été notée ou relevée.")

			return redirect('colloscope', slug=classe.slug)
		else:
			return redirect('colle_detail', pk=colle.pk)

	form = ColleSupprimerForm(instance=colle)
	return render(request, 'pykol/colles/supprimer.html',
			context={
				'colle': colle,
			})

@login_required
def creneaux(request, slug):
	"""Liste des créneaux de colles pour une classe"""
	classe = get_object_or_404(Classe, slug=slug)

	# On vérifie à priori que l'utilisateur possède la permission
	# d'ajouter un créneau (sans savoir pour le moment si cette
	# permission est restreinte à une matière ou non).
	if not request.user.has_perm('pykol.add_creneau', classe):
		raise PermissionDenied

	creneaux_qs = Creneau.objects.filter(classe=classe).order_by(
			'enseignement', 'colleur', 'jour', 'debut')

	if request.method == 'POST':
		formset = CreneauSansClasseFormSet(request.POST, queryset=creneaux_qs,
					form_kwargs={'classe': classe})

		if formset.is_valid():
			creneaux = formset.save(commit=False)
			for creneau in creneaux:
				creneau.classe = classe
				# On vérifie que l'utilisateur a le droit de créer ce
				# créneau.
				# TODO signaler l'erreur en cas de refus
				if request.user.has_perm('pykol.add_creneau', creneau):
					creneau.save()
			for creneau in formset.deleted_objects:
				# On vérifie que l'utilisateur a le droit de supprimer
				# ce créneau.
				# TODO signaler l'erreur en cas de refus
				if request.user.has_perm('pykol.delete_creneau', creneau):
					creneau.save()
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
	# On trie par nom de colleur, puis par colleur pour départager les
	# homonymes.
	creneaux_qs = Creneau.objects.order_by('colleur__last_name',
			'colleur__first_name', 'colleur', 'jour', 'debut')

	if request.method == 'POST':
		formset = CreneauSalleFormSet(request.POST, queryset=creneaux_qs)

		if formset.is_valid():
			formset.save()

	else:
		formset = CreneauSalleFormSet(queryset=creneaux_qs)

	return render(request, 'pykol/direction/creneau_list.html',
			context={'formset': formset})

@login_required
def creneau_supprimer(request, pk):
	"""Suppression d'un créneau de colle"""
	creneau = get_object_or_404(Creneau, pk=pk)
	if not request.user.has_perm('pykol.delete_creneau', creneau):
		raise PermissionDenied

	# TODO implémenter cette vue
	pass
