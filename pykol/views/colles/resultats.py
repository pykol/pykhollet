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
Vues d'affichage des résultats de colles des étudiants.
"""

from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from pykol.models.base import Classe

@login_required
def classe_resultats(request, slug):
	"""
	Affichage du tableau des résultats de colle pour la classe donnée

	Cette vue affiche les résultats de la classe uniquement pour les
	colles dans une matière enseignée dans la classe par le professeur
	actuellement connecté. Dans tous les autres cas (si le professeur
	n'enseigne pas dans la classe, si l'utilisateur n'est pas un
	professeur), l'accès aux résultats est interdit.
	"""
	classe = get_object_or_404(Classe, slug=slug)

	# TODO récupérer les résultats et les mettre en forme

	return render(request, 'pykol/colles/classe_resultats.html',
			context={})

@login_required
def etudiant_resultats(request, pk):
	"""
	Affichage des notes obtenues par un étudiant donné.

	L'accès n'est autorisé qu'aux professeurs de la classe ou qu'à
	l'étudiant lui-même.
	"""
	etudiant = get_object_or_404(Etudiant, pk=pk)

	# TODO récupérer les résultats

	return render(request, 'pykol/colles/etudiant_resultats.html',
			context={})
