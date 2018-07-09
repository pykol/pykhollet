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

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, \
		permission_required
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic.list import ListView
from django.contrib.auth import get_user_model

from pykol.forms.user import FullUserForm
from pykol.forms.permissions import ColloscopePermFormSet
User = get_user_model()

@login_required
@permission_required('pykol.direction')
def direction_create_user(request):
	if request.method == 'POST':
		form = FullUserForm(request.POST)
		if form.is_valid():
			user = form.save()
			messages.success(request, "Utilisateur créé avec succès")
			return redirect('direction_edit_user', user.pk)
		else:
			messages.error(request, "Le formulaire contient des erreurs")
	else:
		form = FullUserForm()
	
	return render(request, 'pykol/direction/edit_user.html',
			context={'form': form, 'concerned_user': None,})

@login_required
@permission_required('pykol.direction')
def direction_edit_user(request, pk):
	user = get_object_or_404(User, pk=pk)

	if request.method == 'POST':
		form = FullUserForm(request.POST, instance=user)
		try:
			perm_form = ColloscopePermFormSet(request.POST,
					prefix='perm', instance=user.professeur)
		except ObjectDoesNotExist:
			perm_form = None

		need_redirect = False
		for f in (form, prof_form, etudiant_form, perm_form):
			if f is not None and f.is_valid():
				f.save()
				need_redirect = True

		if need_redirect:
			return redirect('direction_edit_user', pk=user.pk)

	else:
		try:
			perm_form = ColloscopePermFormSet(instance=user,
					prefix='perm')
		except ObjectDoesNotExist:
			perm_form = None

		form = FullUserForm(instance=user)

	return render(request, 'pykol/direction/edit_user.html',
			context={
				'concerned_user': user,
				'form': form,
				'perm_form': perm_form,
			}
		)

class DirectionListUser(PermissionRequiredMixin, ListView):
	model = User
	ordering = ('last_name', 'first_name',)
	template_name = 'pykol/direction/list_user.html'
	permission_required = 'pykol.direction'

@login_required
@permission_required('pykol.direction')
def direction_list_user(request):
	return render(request, 'pykol/direction/list_user.html')

@login_required
@permission_required('pykol.direction')
def direction_delete_user(request):
	pass
