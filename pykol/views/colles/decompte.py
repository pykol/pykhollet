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
Vues destinées à l'administration pour le décompte et le paiement des
colles.
"""

@login_required
def decompte_list(request):
	"""Liste des décomptes de colles existants"""
	pass

@login_required
def decompte_detail(request):
	"""Détail d'un décompte de colles"""
	pass

@login_required
def decompte_creer(request):
	"""Création d'un décompte de colles"""
	pass
