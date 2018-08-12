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

"""Édition des groupes de colles."""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.forms import formset_factory
from django.contrib import messages

from pykol.models.base import Classe
from pykol.forms.colloscope import TrinomeForm

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
			with transaction.atomic():
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

	return render(request, 'pykol/colloscope/trinomes.html',
			context={'formset': formset,
				'classe': classe,})

@login_required
def create_trinome(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.change_colloscope', classe):
		raise PermissionDenied

	# TODO vue à implémenter

	return render(request, 'pykol/base.html')

