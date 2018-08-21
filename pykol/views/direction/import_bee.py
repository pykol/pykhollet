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

import os

import zipfile

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.conf import settings

from pykol.forms.import_bee import ImportBEEForm
from pykol.models.base import Annee
import pykol.lib.bee

@login_required
@permission_required('pykol.direction')
def import_bee(request):
	if request.method == 'POST':
		form = ImportBEEForm(request.POST, request.FILES)
		if form.is_valid():
			import_success = []

			annee = form.cleaned_data.get('annee')

			if form.cleaned_data['stsemp']:
				try:
					stsemp_zip = zipfile.ZipFile(request.FILES['stsemp'])
					xml_name = stsemp_zip.namelist()[0]
					stsemp_xml = stsemp_zip.open(xml_name)
				except zipfile.BadZipFile:
					request.FILES['stsemp'].seek(0)
					stsemp_xml = request.FILES['stsemp']

				# On privilégie l'année scolaire provenant de STS
				annee_sts = pykol.lib.bee.import_stsemp(stsemp_xml)
				if annee_sts != annee:
					messages.warning(request,
							"Le champ « Année scolaire » a été ignoré "
							"car l'année scolaire est présente dans le "
							"fichier STS. L'année qui se trouve dans "
							"ce fichier a été utilisée pour stocker les "
							"données")
				annee = annee_sts

				stsemp_xml.close()
				import_success.append('STS-EMP')

			if form.cleaned_data['structure']:
				with zipfile.ZipFile(request.FILES['structure']) as structure_zip:
					xml_name = structure_zip.namelist()[0]
					structure_xml = structure_zip.open(xml_name)
					pykol.lib.bee.import_structures(structure_xml, annee)
				import_success.append('Structures')

			if form.cleaned_data['nomenclature']:
				with zipfile.ZipFile(request.FILES['nomenclature']) as nomenclatures_zip:
					xml_name = nomenclatures_zip.namelist()[0]
					nomenclatures_xml = nomenclatures_zip.open(xml_name)
					pykol.lib.bee.import_nomenclatures(nomenclatures_xml)
				import_success.append('Nomenclature')

			if form.cleaned_data['eleves']:
				with zipfile.ZipFile(request.FILES['eleves']) as eleves_zip:
					xml_name = eleves_zip.namelist()[0]
					eleves_xml = eleves_zip.open(xml_name)
					pykol.lib.bee.import_etudiants(eleves_xml, annee)
				import_success.append('Élèves')

			# Import des données des colles
			nomcolles_file = os.path.join(settings.BASE_DIR, 'pykol/data/NomenclatureColles.xml')
			with open(nomcolles_file, encoding="utf-8") as nomcolles_xml:
				pykol.lib.bee.import_nomenclature_colles(nomcolles_xml, annee)

			# TODO améliorer la gestion des erreurs

			if import_success:
				messages.success(request,
						"L'import des données a été effectué avec succès "
						"pour les fichiers : "
						"{}.".format(", ".join(import_success)))
			else:
				messages.warning(request,
						"Vous n'avez fourni aucun fichier à importer.")

			return redirect('import_bee')

	else:
		form = ImportBEEForm()

	return render(request, 'pykol/import_bee.html', context={
		'form': form,
		'annee_scolaire_none': not(Annee.objects.all()),
	})
