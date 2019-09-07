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
from django.db.models import Q

from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table, TableColumn, TableRow, TableCell

from pykol.forms.user import FullUserForm, ColleursImportForm
from pykol.forms.permissions import ColloscopePermFormSet
from pykol.lib.odftools import tablecell_to_text
from pykol.models.base import Professeur
User = get_user_model()

@login_required
@permission_required('pykol.direction')
def direction_create_user(request):
	if request.method == 'POST':
		form = FullUserForm(request.POST)
		if form.is_valid():
			user = form.save()
			messages.success(request, "Utilisateur créé avec succès")
			return redirect('direction_list_user')
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
		for f in (form, perm_form):
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
def direction_delete_user(request):
	pass

@login_required
@permission_required('pykol.direction')
def import_colleurs_odf(request):
	"""
	Import de la liste des colleurs depuis un tableur OpenDocument
	"""
	if request.method == 'POST':
		form = ColleursImportForm(request.POST, request.FILES)

		if form.is_valid():
			colleurs_ods = load(request.FILES['colleurs'])
			table = colleurs_ods.spreadsheet.getElementsByType(Table)[0]
			lignes = table.getElementsByType(TableRow)
			for ligne in lignes[1:]:
				cells = ligne.getElementsByType(TableCell)

				colleur_data = {}

				if tablecell_to_text(cells[0]).strip() == "M.":
					colleur_data['sexe'] = Professeur.SEXE_HOMME
				else:
					colleur_data['sexe'] = Professeur.SEXE_FEMME

				try:
					colleur_data['last_name'] = tablecell_to_text(cells[1]).strip().title()
					colleur_data['first_name'] = tablecell_to_text(cells[2]).strip().title()
				except:
					continue

				if not (colleur_data['last_name'] and
						colleur_data['first_name']):
					continue

				try:
					colleur_data['email'] = tablecell_to_text(cells[3]).strip() or None
				except:
					colleur_data['email'] = None
				colleur_data['corps'] = Professeur.CORPS_AUTRE

				# On ne peut pas utiliser ici
				# Professeur.objects.update_or_create à cause de la
				# requête un peu plus compliquée pour identifier le
				# colleur.
				compte_query = Q(last_name__iexact=colleur_data['last_name'],
						first_name__iexact=colleur_data['first_name']) \
						| Q(email__isnull=False, email=colleur_data['email'])
				try:
					prof = Professeur.objects.get(compte_query)
					for field, val in colleur_data.items():
						setattr(prof, field, val)
					prof.save()
				except Professeur.DoesNotExist:
					try:
						if not form.cleaned_data.get('mise_a_jour'):
							prof = Professeur.objects.create(**colleur_data)
					except:
						# On est peut-être en train de mettre à jour le
						# compte d'un personnel de direction
						try:
							user = User.objects.get(compte_query)
							for field, val in colleur_data.items():
								setattr(user, field, val)
							user.save()
						except:
							# Là, on renonce
							# TODO signaler l'erreur
							pass

			return redirect('direction_list_user')

	else:
		form = ColleursImportForm()

	return render(request, 'pykol/direction/import_colleurs.html',
			context={'form': form})
