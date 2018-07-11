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

from django.shortcuts import render, get_object_or_404
from django.views import generic
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone

from pykol.models.colles import Colle

"""
Vues de gestion des colles destinées aux colleurs.

Ces vues permettent de déclarer les notes de colles, de déplacer des
colles ou de les annuler (ce qui ne les supprime pas de la base).

Elles ne permettent ni de créer des colles, ni de supprimer des colles :
ces tâches relèvent de la gestion du colloscope, et se trouvent dans le
fichier colloscope.py
"""

@login_required
def colle_detail(request, pk):
	"""
	Affichage de tous les détails d'une colle
	"""
	pass

@login_required
def colle_declarer(request, pk):
	"""
	Vue qui permet de déclarer les notes pour une colle déjà existante
	dans la base de données, identifiée par sa clé pk.
	"""
	pass

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
	pass

class ColleListView(LoginRequiredMixin, generic.ListView):
	"""
	Affichage des colles pour le colleur actuellement connecté
	"""
	def get_queryset(self):
		return Colle.objects.filter(
			colledetails__colleur=self.request.user,
			colledetails__actif=True).order_by('colledetails__horaire')

colle_list = ColleListView.as_view()

class ColleANoterListView(ColleListView):
	"""
	Affichage des colles en attente de notation pour le colleur
	"""
	def get_queryset(self):
		return super().get_queryset().filter(etat=Colle.ETAT_PREVUE,
				colledetails__horaire__lte=timezone.localtime())

colle_a_noter_list = ColleANoterListView.as_view()
