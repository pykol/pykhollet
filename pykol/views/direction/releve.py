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

from django.shortcuts import render, redirect, get_object_or_404
from django.views import generic, View
from django.contrib.auth.mixins import LoginRequiredMixin, \
	PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.timezone import localtime
from django.db import transaction

from pykol.models.colles import ColleReleve, Colle, ColleReleveLigne

@login_required
@permission_required('pykol.add_collereleve')
@transaction.atomic
def releve_creer(request):
	# Création d'un nouveau relevé
	releve = ColleReleve(date=localtime())
	releve.save()

	# On attache à ce relevé toutes les colles qui sont notées mais qui
	# n'ont pas encore été payées
	colles_faites = Colle.objects.filter(etat__in=(Colle.ETAT_NOTEE,
		Colle.ETAT_EFFECTUEE), releve__isnull=True)

	for colle in colles_faites:
		releve.ajout_colle(colle)

	# On redirige ensuite vers la vue qui affiche le détail de ce relevé
	return redirect('releve_detail', pk=releve.pk)

class ReleveDetailView(LoginRequiredMixin, PermissionRequiredMixin,
		generic.DetailView):
	permission_required = ('pykol.view_collereleve',)
	model = ColleReleve

class ReleveListView(LoginRequiredMixin, PermissionRequiredMixin,
		generic.ListView):
	permission_required = ('pykol.view_collereleve',)
	model = ColleReleve
	ordering = ('date',)

@login_required
@permission_required('pykol.change_collereleve')
def releveligne_payer(request, pk):
	ligne = get_object_or_404(ColleReleveLigne, pk=pk)
	ligne.payer()
	return redirect('releve_detail', pk=ligne.releve.pk)
