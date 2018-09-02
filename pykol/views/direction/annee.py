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

from datetime import timedelta

from django.views import generic, View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, \
	PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum

from pykol.models.base import Annee
from pykol.models.colles import Dotation, CollesEnseignement
from pykol.forms.annee import DotationFormSet

class AnneeListView(LoginRequiredMixin, generic.ListView):
	model = Annee
	ordering = ('debut',)

@login_required
@permission_required('pykol.direction')
def annee_detail(request, pk):
	annee = get_object_or_404(Annee, pk=pk)

	if request.method == 'POST':
		dotation_formset = DotationFormSet(request.POST, instance=annee)
		if dotation_formset.is_valid():
			dotation_formset.save()
			return redirect('annee_detail', pk=annee.pk)
	else:
		dotation_formset = DotationFormSet(instance=annee)

	# Calcul des dotations théoriques pour les classes et des heures
	# prévues aux colloscopes
	colles_ens = CollesEnseignement.objects.filter(
			classe__annee=annee).order_by('classe__nom')
	dotations = {}
	total_heures = timedelta()
	total_heures_colloscopes = timedelta()

	for ligne in colles_ens:
		classe = ligne.classe
		dotation = dotations.setdefault(classe, {
			'total_heures': timedelta(),
			'total_heures_colloscope': timedelta(),
			'matieres': []
		})

		heures = ligne.dotation()
		heures_colloscope = ligne.colle_set.aggregate(Sum('duree'))['duree__sum'] \
				or timedelta()
		dotations[classe]['matieres'].append({
			'matiere': ligne,
			'heures': heures,
			'heures_colloscope': heures_colloscope})
		dotations[classe]['total_heures'] += heures
		total_heures += heures
		dotations[classe]['total_heures_colloscope'] += heures_colloscope
		total_heures_colloscopes += heures_colloscope



	return render(request, 'pykol/annee_detail.html', context={
		'annee': annee,
		'dotation_formset': dotation_formset,
		'dotations': dotations,
		'total_heures': total_heures,
		'total_heures_colloscopes': total_heures_colloscopes,
		})

@login_required
@permission_required('pykol.direction')
def annee_supprimer(request, pk):
	pass
