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
from django.forms import formset_factory
from django.contrib import messages

from pykol.models.base import Classe
from pykol.models.colles import Semaine, CollesReglages, Creneau, Colle
from pykol.forms.colloscope import CreneauFormSet, \
		CreneauSansClasseFormSet, \
		TrinomeForm, ColleForm, ColleSupprimerForm

@login_required
def colloscope_home(request):
	return render(request, 'pykol/base.html')

@login_required
def colloscope(request, slug):
	"""
	Affichage du colloscope complet d'une classe
	"""
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.view_colloscope', classe):
		raise PermissionDenied

	semaines = classe.semaine_set.order_by('debut')
	creneaux = classe.creneau_set.order_by('matiere', 'jour', 'debut')
	colles = classe.colle_set.all()

	colloscope = defaultdict(OrderedDict)
	for creneau in creneaux:
		colloscope[creneau.matiere][creneau] = OrderedDict([
				(semaine, []) for semaine in semaines])

	autres_colles = []
	for colle in colles:
		if colle.creneau is not None and colle.semaine is not None:
			colloscope[colle.matiere][colle.creneau][colle.semaine].append(colle)
		else:
			autres_colles.append(colle)

	perm_creation = request.user.has_perm('pykol.add_colle', classe)
	# La conversion de colloscope en dict est obligatoire, car les
	# gabarits Django ne peuvent pas itérer sur les defaultdict
	# facilement : l'appel colloscope.items est d'abord converti en
	# colloscope['items'] et non en colloscope.items().
	return render(request, 'pykol/colles/colloscope.html',
			context={
				'classe': classe,
				'semaines': semaines,
				'colloscope': dict(colloscope),
				'perm_creation': perm_creation,
				'autres_colles': autres_colles,
				})

@login_required
def trinomes(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.change_colloscope', classe):
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
			return redirect('colloscope_trinomes', slug=classe.slug)
	else:
		formset = TrinomeFormSet(initial=initial,
				form_kwargs={'queryset': etudiants})

	return render(request, 'pykol/colles/trinomes.html',
			context={'formset': formset,
				'classe': classe,})

@login_required
def create_trinome(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.change_colloscope', classe):
		raise PermissionDenied

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
			colleenseignement = form.cleaned_data['enseignement']
			colle = Colle(
				creneau=form.cleaned_data['creneau'],
				semaine=form.cleaned_data['semaine'],
				classe=classe,
				matiere=colleenseignement.enseignement.matiere,
				groupe=form.cleaned_data['trinome'],
				duree=colleenseignement.duree,
				mode=form.cleaned_data['mode'])

			# La matière est connue, on vérifie que l'utilisateur peut
			# effectivement créer la colle.
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
	if not request.user.has_perm('pykol.delete_colle', colle.classe):
		raise PermissionDenied

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

	creneaux_qs = Creneau.objects.filter(classe=classe).order_by('matiere',
			'colleur', 'jour', 'debut')

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
	creneau = get_object_or_404(Creneau, pk=pk)
	if not request.user.has_perm('pykol.delete_creneau', creneau):
		raise PermissionDenied

	# TODO implémenter cette vue
	pass
