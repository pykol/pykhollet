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

from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, \
		UserPassesTestMixin
from django.utils import timezone
from django.db.models import Func, F

from pykol.models.base import Etudiant
from pykol.models.colles import Colle
from pykol.forms.colles import ColleNoteFormSet

"""
Vues de gestion des colles destinées aux colleurs.

Ces vues permettent de déclarer les notes de colles, de déplacer des
colles ou de les annuler (ce qui ne les supprime pas de la base).

Elles ne permettent ni de créer des colles, ni de supprimer des colles :
ces tâches relèvent de la gestion du colloscope, et se trouvent dans le
fichier colloscope.py
"""

def colle_visible_par(user, colle):
	"""Renvoie True si et seulement si l'utilisateur a le droit de
	consulter les détails de la colle."""
	return user == colle.colleur or \
		user.has_perm('pykol.change_colle', colle.classe) or \
		user in colle.classe.profs_de(colle.matiere)

class ColleVisibleMixin(generic.detail.SingleObjectMixin,
		UserPassesTestMixin):
	"""Application du test colle_visible_par à une vue sur la colle"""
	model = Colle
	def test_func(self):
		return colle_visible_par(self.request.user, self.get_object())

class ColleDetailView(LoginRequiredMixin, ColleVisibleMixin, \
		generic.DetailView):
	"""
	Affichage de tous les détails d'une colle
	"""
	template_name = 'pykol/colles/colle_detail.html'
	model = Colle

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		colle = self.get_object()
		context['anciens_details'] = \
				colle.colledetails_set.filter(actif=False)
		context['supprimer_perm'] = \
				self.request.user.has_perm('pykol.change_colle',
						colle.classe)
		context['noter_perm'] = \
				self.request.user.professeur == colle.colleur
		return context

colle_detail = ColleDetailView.as_view()

@login_required
def colle_declarer(request, pk):
	"""
	Vue qui permet de déclarer les notes pour une colle déjà existante
	dans la base de données, identifiée par sa clé pk.
	"""
	colle = get_object_or_404(Colle, pk=pk)

	# Seul le colleur peut noter sa colle
	if request.user.professeur != colle.details.colleur:
		raise PermissionDenied

	# Les colles sous la forme de TD n'ont pas de notes, il suffit de
	# confirmer qu'elles ont été réalisées
	if colle.mode == Colle.MODE_TD:
		colle.etat = Colle.ETAT_EFFECTUEE
		colle.save()
		return redirect('colle_detail', colle.pk)

	# On peuple le formulaire avec les élèves qui n'ont pas encore été
	# notés
	eleves_sans_note = colle.details.eleves.difference(
		Etudiant.objects.filter(collenote__colle=colle))
	initial = []
	for eleve in eleves_sans_note:
		initial.append({'eleve' : eleve})

	if request.method == 'POST':
		form = ColleNoteFormSet(request.POST, instance=colle,
				initial=initial)
		form.extra = len(initial)
		if form.is_valid():
			form.save()

			# Quand tous les élèves sont notés, on indique que la colle
			# est notée.
			eleves_sans_note = colle.details.eleves.difference(
				Etudiant.objects.filter(collenote__colle=colle))
			if not eleves_sans_note:
				colle.etat = Colle.ETAT_NOTEE
				colle.save()

			return redirect('colle_detail', colle.pk)
	else:
		form = ColleNoteFormSet(instance=colle, initial=initial)
		form.extra = len(initial)

	return render(request, 'pykol/colles/noter.html', {'colle': colle, 'form': form})

@login_required
def colle_deplacer(request, pk):
	"""
	Vue qui permet de modifier les détails d'une colle (date, lieu,
	etc.)
	"""
	pass

@login_required
def colle_annuler(request, pk):
	"""
	Annulation d'une colle par le colleur
	"""
	colle = get_object_or_404(Colle, pk=pk)

	# On ne change pas les colles des copains
	if not request.user.has_perm('pykol.change_colle', colle):
		raise PermissionDenied

	if colle.etat == Colle.ETAT_PREVUE:
		colle.etat = Colle.ETAT_ANNULEE
		colle.save()
		messages.sucess(request, "La colle a bien été annulée")
	else:
		messages.error(request, "On ne peut pas annuler une colle déjà notée ou déjà relevée")

	return redirect('colle_list')

class ColleListView(LoginRequiredMixin, generic.ListView):
	"""
	Affichage des colles pour le colleur actuellement connecté
	"""
	template_name = 'pykol/colles/colle_list.html'

	def get_queryset(self):
		return Colle.objects.filter(
			colledetails__colleur=self.request.user,
			colledetails__actif=True).order_by('colledetails__horaire').annotate(
				a_noter=Func(F('colledetails__horaire'),
					timezone.localtime(), arity=2, arg_joiner='<',
					function='')
				)

colle_list = ColleListView.as_view()

class ColleANoterListView(ColleListView):
	"""
	Affichage des colles en attente de notation pour le colleur
	"""
	def get_queryset(self):
		return super().get_queryset().filter(etat=Colle.ETAT_PREVUE,
				colledetails__horaire__lte=timezone.localtime())

colle_a_noter_list = ColleANoterListView.as_view()
