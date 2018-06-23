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

import zipfile

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages

from pykol.forms.import_bee import ImportBEEForm
import pykol.lib.bee

@login_required
@permission_required('direction')
def import_bee(request):
	if request.method == 'POST':
		form = ImportBEEForm(request.POST, request.FILES)
		if form.is_valid():
			import_success = []
			print(form.cleaned_data)

			if form.cleaned_data['structure']:
				with zipfile.ZipFile(request.FILES['structure']) as structure_zip:
					structure_xml = structure_zip.open('Structures.xml')
					pykol.lib.bee.import_divisions(structure_xml)
				import_success.append('Structures')

			if form.cleaned_data['nomenclature']:
				with zipfile.ZipFile(request.FILES['nomenclature']) as nomenclatures_zip:
					nomenclatures_xml = nomenclatures_zip.open('Nomenclature.xml')
					pykol.lib.bee.import_nomenclatures(nomenclatures_xml)
				import_success.append('Nomenclature')

			if form.cleaned_data['eleves']:
				with zipfile.ZipFile(request.FILES['eleves']) as eleves_zip:
					eleves_xml = eleves_zip.open('ElevesSansAdresses.xml')
					pykol.lib.bee.import_etudiants(eleves_xml)
				import_success.append('Élèves')

			# TODO améliorer la gestion des erreurs

			if import_success:
				messages.success(request,
						"L'import des données a été effectué avec succès "
						"pour les fichiers : "
						"{}.".format(", ".join(import_success)))
			else:
				messages.warning(request,
						"Vous n'avez fourni aucun fichier à importer.")

			form = ImportBEEForm()
			# TODO redirect pour éviter double soumission

	else:
		form = ImportBEEForm()

	return render(request, 'pykol/import_bee.html', {'form': form})
