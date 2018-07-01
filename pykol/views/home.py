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
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, \
		permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic.list import ListView

from pykol.forms.user import MonProfilForm, MonProfilPasswordForm, \
		FullUserForm, ProfesseurForm, EtudiantForm
from pykol.models.base import User

@login_required
def home(request):
	return render(request, 'pykol/base.html')

@login_required
def mon_profil(request):
	if request.method == 'POST':
		profil_form = MonProfilForm(request.POST, instance=request.user)
		pass_form = MonProfilPasswordForm(request.user, request.POST)
		if profil_form.is_valid() and pass_form.is_valid():
			profil_form.save()
			user = pass_form.save()
			update_session_auth_hash(request, user)
			return redirect('mon_profil')

	else:
		profil_form = MonProfilForm(instance=request.user)
		pass_form = MonProfilPasswordForm(request.user)

	return render(request, 'registration/profile.html',
			context={
				'profil_form': profil_form,
				'pass_form': pass_form,}
		)

@login_required
@permission_required('pykol.direction')
def direction_create_user(request):
	if request.method == 'POST':
		form = FullUserForm(request.POST)
		if form.is_valid():
			form.save()
			return redirect('direction_create_user')
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
			prof_form = ProfesseurForm(request.POST,
					instance=user.professeur)
		except ObjectDoesNotExist:
			prof_form = None

		try:
			etudiant_form = EtudiantForm(request.POST,
					instance=user.etudiant)
		except ObjectDoesNotExist:
			etudiant_form = None

		need_redirect = False
		if form.is_valid():
			form.save()
			need_redirect = True

		if prof_form is not None and prof_form.is_valid():
			prof_form.save()
			need_redirect = True

		if etudiant_form is not None and etudiant_form.is_valid():
			etudiant_form.save()
			need_redirect = True

		if need_redirect:
			return redirect('direction_edit_user', pk=user.pk)

	else:
		try:
			prof_form = ProfesseurForm(instance=user.professeur)
		except ObjectDoesNotExist:
			prof_form = None

		try:
			etudiant_form = EtudiantForm(instance=user.etudiant)
		except ObjectDoesNotExist:
			etudiant_form = None

		form = FullUserForm(instance=user)

	return render(request, 'pykol/direction/edit_user.html',
			context={
				'concerned_user': user,
				'form': form,
				'prof_form': prof_form,
				'etudiant_form': etudiant_form,
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
