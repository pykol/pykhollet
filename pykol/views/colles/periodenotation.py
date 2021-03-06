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

from pykol.models.base import Classe, Enseignement
from pykol.models.colles import PeriodeNotation
from pykol.forms.colles import PeriodeNotationFormset
from pykol.lib.shortcuts import redirect_next

@login_required
def periode_notation(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	periodenotation_qs = PeriodeNotation.objects.filter(
			enseignement__classe=classe,
			enseignement__service__professeur=request.user)
	enseignement_qs = Enseignement.objects.filter(
			service__professeur=request.user,
			classe=classe)

	context = {'classe': classe}

	if request.method == 'POST':
		formset = PeriodeNotationFormset(request.POST,
				prefix='periodenotation_set',
				queryset=periodenotation_qs,
				form_kwargs={'enseignement_qs': enseignement_qs,})

		if formset.is_valid():
			formset.save(commit=False)
			for periode, _ in formset.changed_objects:
				if request.user.has_perm('pykol.change_periodenotation',
						periode):
					periode.save()
			for periode in formset.deleted_objects:
				if request.user.has_perm('pykol.delete_periodenotation',
						periode):
					periode.delete()
			for periode in formset.new_objects:
				if request.user.has_perm('pykol.add_periodenotation',
						periode):
					periode.save()
			return redirect_next('classe_periode_notation',
					classe.slug, request=request)

	else:
		formset = PeriodeNotationFormset(prefix='periodenotation_set',
				queryset=periodenotation_qs,
				form_kwargs={'enseignement_qs': enseignement_qs,})

	context['formset'] = formset

	return render(request, 'pykol/colles/periodenotation.html', context=context)
