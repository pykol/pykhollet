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

from django.shortcuts import render, redirect, get_object_or_404
from django.views import generic, View
from django.contrib.auth.mixins import LoginRequiredMixin, \
	PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.utils.timezone import localtime
from django.db import transaction
from django.db.models import F
from django.views.decorators.http import require_POST
from django.http import JsonResponse

from pykol.models.colles import ColleReleve, Colle, ColleReleveLigne
from pykol.lib.auth import user_est_professeur

@login_required
@permission_required('pykol.add_collereleve')
@transaction.atomic
@require_POST
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

@login_required
@permission_required('pykol.view_collereleve')
def releve_detail_json(request, pk):
	lignes = list(ColleReleveLigne.objects.filter(releve__pk=pk).annotate(
		nom=F('colleur__last_name'),
		prenom=F('colleur__first_name'),
		id_acad=F('colleur__id_acad')
		).values(
			'pk', 'releve',
			'colleur', 'nom', 'prenom', 'id_acad',
			'taux', 'duree', 'duree_interrogation'))
	data = {
		'taux': dict(ColleReleveLigne.TAUX_CHOICES),
		'lignes': lignes,
	}
	return JsonResponse(data)

@login_required
def releve_detail_dispatch(request, pk):
	if request.GET.get('format', 'html') == 'json':
		return releve_detail_json(request, pk)
	else:
		return ReleveDetailView.as_view()(request, pk=pk)

class ReleveListView(LoginRequiredMixin, PermissionRequiredMixin,
		generic.ListView):
	permission_required = ('pykol.view_collereleve',)
	model = ColleReleve
	ordering = ('date',)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['nouvelles_colles'] = Colle.objects.filter(etat__in=(Colle.ETAT_NOTEE,
			Colle.ETAT_EFFECTUEE), releve__isnull=True).count()
		return context

@login_required
@permission_required('pykol.change_collereleve')
def releve_list_json(request):
	releves = list(ColleReleve.objects.values('id', 'date', 'date_paiement',
			'etat'))
	data = {
		'etat_releve': dict(ColleReleve.ETAT_CHOICES),
		'releves': releves,
	}
	return JsonResponse(data)

@login_required
@user_est_professeur
def releve_prof_detail(request):
	lignes = ColleReleveLigne.objects.filter(colleur=request.user.professeur).order_by(
		'releve__date', 'releve', 'taux')

	futures_lignes = {}
	futures_colles = Colle.objects.filter(etat__in=(Colle.ETAT_NOTEE,
		Colle.ETAT_EFFECTUEE), releve__isnull=True,
		colledetails__colleur=request.user, colledetails__actif=True)
	for colle in futures_colles:
		taux = ColleReleveLigne.taux_colle(colle.classe)
		ligne = futures_lignes.setdefault(taux, {
			'get_taux_display': dict(ColleReleveLigne.TAUX_CHOICES).get(taux),
			'heures': timedelta(),
			'heures_interrogation': timedelta(),
			})
		ligne['heures'] += colle.duree

		if colle.mode == Colle.MODE_INTERROGATION:
			for collenote in colle.collenote_set.all():
				ligne['heures_interrogation'] += collenote.duree
		else:
			ligne['heures_interrogation'] += colle.duree

	return render(request, 'pykol/colles/releve_prof.html', context={
		'lignes': lignes,
		'futures_lignes': futures_lignes.values(),})

@login_required
def releve_dispatch(request):
	if request.user.has_perm('pykol.view_collereleve'):
		if request.GET.get('format', 'html') == 'json':
			return releve_list_json(request)
		else:
			return ReleveListView.as_view()(request)
	else:
		return releve_prof_detail(request)

@login_required
@permission_required('pykol.change_collereleve')
@require_POST
def releveligne_payer(request, pk):
	ligne = get_object_or_404(ColleReleveLigne, pk=pk)
	ligne.payer()
	return redirect('releve_detail', pk=ligne.releve.pk)

@login_required
@permission_required('pykol.change_collereleve')
@require_POST
def releveligne_saisie_asie(request, pk):
	ligne = get_object_or_404(ColleReleveLigne, pk=pk)
	ligne.etat = ColleReleveLigne.ETAT_SAISIE_ASIE
	ligne.save()
	return redirect('releve_detail', pk=ligne.releve.pk)
