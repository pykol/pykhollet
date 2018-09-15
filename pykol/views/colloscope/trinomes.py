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
from django.views.decorators.http import require_POST

from pykol.models.base import Classe, Etudiant, Annee
from pykol.models.colles import Trinome
from pykol.forms.colloscope import TrinomeForm, TrinomeDetailForm

@login_required
def trinomes(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.change_colloscope', classe):
		raise PermissionDenied

	trinomes = classe.trinomes
	etudiants = classe.etudiant_set.order_by('last_name', 'first_name')
	initial = []
	def join_groupes(queryset):
		return ','.join(queryset.filter(etudiants=etudiant).values_list('nom',
			flat=True))
	for etudiant in etudiants:
		qs = trinomes.filter(etudiants=etudiant)
		initial.append({
			'etudiant': etudiant,
			'groupes': join_groupes(qs.filter(periode=Trinome.PERIODE_ANNEE)),
			'groupes_periode_premiere': join_groupes(qs.filter(periode=Trinome.PERIODE_PREMIERE)),
			'groupes_periode_deuxieme': join_groupes(qs.filter(periode=Trinome.PERIODE_DEUXIEME)),
			})

	TrinomeFormSet = formset_factory(TrinomeForm, can_delete=False, extra=0,
		can_order=False, max_num=len(etudiants), min_num=len(etudiants))

	if request.method == 'POST':
		formset = TrinomeFormSet(request.POST, form_kwargs={'queryset':
			etudiants}, initial=initial)
		if formset.is_valid():
			# On construit d'abord le dictionnaire qui à chaque période
			# et à chaque numéro de trinôme associe la liste des
			# étudiants membres
			trinomes_membres = {
				Trinome.PERIODE_ANNEE: {},
				Trinome.PERIODE_PREMIERE: {},
				Trinome.PERIODE_DEUXIEME: {},
			}
			for form in formset:
				etudiant = form.cleaned_data['etudiant']
				for groupe in form.cleaned_data['groupes']:
					trinomes_membres[Trinome.PERIODE_ANNEE].setdefault(groupe, []).append(etudiant)
				for groupe in form.cleaned_data['groupes_periode_premiere']:
					trinomes_membres[Trinome.PERIODE_PREMIERE].setdefault(groupe, []).append(etudiant)
				for groupe in form.cleaned_data['groupes_periode_deuxieme']:
					trinomes_membres[Trinome.PERIODE_DEUXIEME].setdefault(groupe, []).append(etudiant)
			# On met ensuite à jour la liste des trinômes
			with transaction.atomic():
				for periode, membres in trinomes_membres.items():
					for groupe, etudiants in membres.items():
						trinome, _ = trinomes.update_or_create(classe=classe,
								nom=groupe, periode=periode, defaults={})
						trinome.etudiants.set(etudiants)
						trinome.save()

			messages.success(request, "Les groupes de colles en "
					" {classe} ont été mis à jour.".format(
						classe=classe))
			return redirect('colloscope', slug=classe.slug)
	else:
		formset = TrinomeFormSet(initial=initial,
				form_kwargs={'queryset': etudiants})

	return render(request, 'pykol/colloscope/trinomes.html',
			context={'formset': formset,
				'classe': classe,})

@login_required
def trinome_detail(request, pk):
	trinome = get_object_or_404(Trinome, pk=pk)
	if not request.user.has_perm('pykol.change_trinome', trinome):
		raise PermissionDenied

	context = {'trinome': trinome}

	context['tous_etudiants'] = 'tous_etudiants' in request.GET
	if context['tous_etudiants']:
		etudiants_qs = Etudiant.objects.filter(classe__annee=Annee.objects.get_actuelle())
	else:
		etudiants_qs = None

	if request.method == 'POST':
		trinome_form = TrinomeDetailForm(request.POST, instance=trinome,
				prefix='trinome', etudiants=etudiants_qs)
		if trinome_form.is_valid():
			trinome_form.save()
			return redirect(trinome.classe)
	else:
		trinome_form = TrinomeDetailForm(instance=trinome,
				prefix='trinome', etudiants=etudiants_qs)

	context['trinome_form'] = trinome_form

	return render(request, 'pykol/colloscope/trinome_detail.html',
			context=context)

@login_required
@require_POST
def trinome_supprimer(request, pk):
	trinome = get_object_or_404(Trinome, pk=pk)
	classe = trinome.classe
	if not request.user.has_perm('pykol.delete_trinome', trinome):
		raise PermissionDenied

	trinome.delete()

	return redirect(classe)
