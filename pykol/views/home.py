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
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, \
		permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin

from pykol.forms.user import MonProfilForm, MonProfilPasswordForm

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
