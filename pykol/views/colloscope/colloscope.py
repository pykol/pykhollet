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

"""Affichage et édition du colloscope."""

from collections import defaultdict, OrderedDict

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from pykol.models.base import Classe

@login_required
def colloscope(request, slug):
	"""
	Affichage du colloscope complet, en fonction du format qui a été
	demandé par l'utilisateur.
	"""
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.view_colloscope', classe):
		raise PermissionDenied

	res_format = request.GET.get('format', None)
	if res_format == 'odf':
		return colloscope_odf(request, classe)
	else:
		return colloscope_html(request, classe)

def colloscope_html(request, classe):
	"""
	Affichage du colloscope complet d'une classe au format HTML
	"""
	semaines = classe.semaine_set.order_by('debut')
	creneaux = classe.creneau_set.order_by('matiere', 'jour', 'debut')
	colles = classe.colle_set.all()

	colloscope = defaultdict(OrderedDict)
	for creneau in creneaux:
		colloscope[creneau.matiere][creneau] = OrderedDict([
				(semaine, []) for semaine in semaines])

	autres_colles = []
	for colle in colles:
		if colle.creneau is not None and colle.semaine is not None:
			colloscope[colle.matiere][colle.creneau][colle.semaine].append(colle)
		else:
			autres_colles.append(colle)

	perm_creation = request.user.has_perm('pykol.add_colle', classe)
	# La conversion de colloscope en dict est obligatoire, car les
	# gabarits Django ne peuvent pas itérer sur les defaultdict
	# facilement : l'appel colloscope.items est d'abord converti en
	# colloscope['items'] et non en colloscope.items().
	return render(request, 'pykol/colloscope/view_colloscope.html',
			context={
				'classe': classe,
				'semaines': semaines,
				'colloscope': dict(colloscope),
				'perm_creation': perm_creation,
				'autres_colles': autres_colles,
				})

def colloscope_odf(request, classe):
	"""
	Affichage du colloscope d'une classe au format OpenDocument
	"""
	pass
