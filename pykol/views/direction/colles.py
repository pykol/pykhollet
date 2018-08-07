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

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect
from django.utils import timezone

from pykol.models.colles import ColleDetails
from pykol.forms.colles import ResaPonctuellesFormSet

@login_required
@permission_required('pykol.direction')
def reservations_ponctuelles(request):
	"""
	Formulaire qui affiche toutes les colles futures qui n'ont pas de
	salle.
	"""
	colles = ColleDetails.objects.filter(salle='', actif=True,
			horaire__gte=timezone.localtime()
			).order_by('horaire', 'colleur')

	if request.method == 'POST':
		formset = ResaPonctuellesFormSet(request.POST, queryset=colles)
		if formset.is_valid():
			formset.save()
			return redirect('reservations_ponctuelles')
	else:
		formset = ResaPonctuellesFormSet(queryset=colles)

	return render(request,
			'pykol/direction/reservations_ponctuelles.html',
			context={'formset': formset, 'colles': colles})
