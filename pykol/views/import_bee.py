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
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from pykol.forms.import_bee import ImportBEEForm
import pykol.lib.bee

@login_required
def import_bee(request):
	if request.method == 'POST':
		form = ImportBEEForm(request.POST, request.FILES)
		if form.is_valid():
			with zipfile.ZipFile(request.FILES['structure']) as structure_zip:
				structure_xml = structure_zip.open('Structures.xml')
				pykol.lib.bee.import_divisions(structure_xml)

			with zipfile.ZipFile(request.FILES['nomenclature']) as nomenclatures_zip:
				nomenclatures_xml = eleves_zip.open('Nomenclatures.xml')
				pykol.lib.bee.import_nomenclature(nomenclatures_xml)

			with zipfile.ZipFile(request.FILES['eleves']) as eleves_zip:
				eleves_xml = eleves_zip.open('ElevesSansAdresses.xml')
				pykol.lib.bee.import_etudiants(eleves_xml)

			# TODO améliorer la gestion des erreurs

			# TODO gérer le cas où les fichiers n'ont pas tous été
			# envoyés (on peut vouloir mettre à jour seulement l'un
			# d'entre eux, par exemple juste la liste des élèves).

			messages.success(request,
					"L'import des données a été effectué avec succès.")
			form = ImportBEEForm()
			# TODO redirect pour éviter double soumission

	else:
		form = ImportBEEForm()

	return render(request, 'pykol/import_bee.html', {'form': form})
