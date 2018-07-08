# -*- coding: utf-8 -*-

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

"""
Vues pour aider à la conception du colloscope, en plaçant les colles en
suivant une permutation circulaire des créneaux.
"""

from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages

from pykol.models.base import Classe
from pykol.models.colles import Roulement, RoulementLigne
from pykol.forms.colloscope import RoulementLigneFormSet, \
		RoulementGraineFormSet, RoulementApplicationForm, \
		RoulementApplication

@login_required
def roulement_creer(request, slug):
	classe = get_object_or_404(Classe, slug=slug)

	if not request.user.has_perm('pykol.add_colle', classe):
		raise PermissionDenied

	roulement = Roulement(classe=classe)
	roulement.save()

	return redirect('roulement_editer', roulement.pk)

@login_required
def roulement_editer(request, pk):
	roulement = get_object_or_404(Roulement, pk=pk)
	if not request.user.has_perm('pykol.add_colle', roulement.classe):
		raise PermissionDenied

	if request.method == 'POST':
		formset = RoulementLigneFormSet(request.POST,
				instance=roulement)
		if formset.is_valid():
			formset.save()

			messages.success(request, "Modifications enregistrées")
			return redirect('roulement_editer', pk)

	else:
		formset = RoulementLigneFormSet(instance=roulement)

	return render(request, 'pykol/colloscope/roulement_edit.html',
			context={
				'roulement': roulement,
				'formset': formset,
				})

@login_required
def roulement_application_creer(request, pk):
	roulement = get_object_or_404(Roulement, pk=pk)
	if not request.user.has_perm('pykol.add_colle', roulement.classe):
		raise PermissionDenied

	app = RoulementApplication(roulement=roulement)
	app.save()

	return redirect('roulement_application_editer', app.pk)

@login_required
def roulement_application_editer(request, pk):
	appli = get_object_or_404(RoulementApplication, pk=pk)
	if not request.user.has_perm('pykol.add_colle', appli.roulement.classe):
		raise PermissionDenied

	if request.method == 'POST':
		form = RoulementApplicationForm(request.POST, instance=appli,
				prefix='appli')
		formset = RoulementGraineFormSet(request.POST, instance=appli,
				prefix='graines')

		if form.is_valid() and formset.is_valid():
			form.save()
			formset.save()

			return redirect('colloscope', appli.roulement.classe.slug)
	else:
		form = RoulementApplicationForm(instance=appli,
				prefix='appli')
		formset = RoulementGraineFormSet(instance=appli,
				prefix='graines')


	return render(request,
			'pykol/colloscope/roulement_application_edit.html',
			context={
				'appli': appli,
				'form': form,
				'formset': formset,
				})

@login_required
def roulement_generer_colles(request, pk):
	roulement = get_object_or_404(Roulement, pk=pk)
	if not request.user.has_perm('pykol.add_colle', roulement.classe):
		raise PermissionDenied

	roulement_lignes = roulement.lignes.all()
	total_lignes = len(roulement_lignes)

	nb_colles = 0

	for graine in roulement.graines.all():
		semaines = list(graine.semaines.order_by('debut'))
		total_semaines = len(semaines)

		for graineligne in graine.lignes.all():
			trinome = graineligne.trinome
			ordre_debut = graineligne.decalage
			for ligne in roulement_lignes:
				ordre_ligne = ligne.ordre
				creneau = ligne.creneau
				for id_semaine in range(ordre_debut + ordre_ligne,
						total_semaines, total_lignes):
					creneau.update_or_create_colle(semaines[id_semaine],
							trinome)
					nb_colles += 1

	messages.success(request, "{} colles ont été générées".format(nb_colles))

	return redirect('colloscope', roulement.classe.slug)
