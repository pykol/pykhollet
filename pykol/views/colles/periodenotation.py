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

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from pykol.models.colles import PeriodeNotation
from pykol.forms.colles import PeriodeNotationFormset
from pykol.lib.shortcuts import redirect_next

@login_required
def periode_notation(request):
	prof = request.user.professeur
	enseignements = Enseignement.objects.filter(professeur=prof)

	if request.method == 'POST':
		form = PeriodeNotationFormset(request.POST,
				enseignements=enseignements)
		if form.is_valid():
			form.save()
			return redirect_next('periodenotation_list', request=request)
	else:
		form = PeriodeNotationFormset(enseignements=enseignements)
	
	return render('periodenotation_list')

@login_required
def periode_notation_detail(request, pk):
	periode = get_object_or_404(PeriodeNotation, pk=pk)
