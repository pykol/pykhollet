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
from django.contrib.auth.decorators import login_required

"""
Vues de gestion des colles destinées aux colleurs.

Ces vues permettent de déclarer les notes de colles, de déplacer des
colles ou de les annuler (ce qui ne les supprime pas de la base).

Elles ne permettent ni de créer des colles, ni de supprimer des colles :
ces tâches relèvent de la gestion du colloscope, et se trouvent dans le
fichier colloscope.py
"""

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

@login_required
def colle_list(request):
	"""
	Affichage de toutes les colles du colleur
	"""
	pass
