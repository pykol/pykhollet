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
from django.db.models import Max

from pykol.forms.import_bee import ImportBEEForm
from pykol.models.base import Annee, ImportBeeLog
from pykol.lib.bee import BEEImporter

@login_required
@permission_required('pykol.direction')
def import_bee(request):
	if request.method == 'POST':
		form = ImportBEEForm(request.POST, request.FILES)
		if form.is_valid():
			xml_list = []

			for fpart in ('stsemp', 'structure', 'nomenclature',
					'eleves'):
				if form.cleaned_data[fpart]:
					try:
						fzip = zipfile.ZipFile(request.FILES[fpart])
						fxml_name = fzip.namelist()[0]
						fxml = fzip.open(fxml_name)
					except zipfile.BadZipFile:
						request.FILES[fpart].seek(0)
						fxml = request.FILES[fpart]

					xml_list.append(fxml)

			# Import des données des colles
			nomcolles_file = os.path.join(settings.BASE_DIR, 'pykol/data/NomenclatureColles.xml')
			xml_list.append(open(nomcolles_file, encoding="utf-8"))

			importer = BEEImporter(*xml_list)
			importer.full_import()
			messages.success(request,
					"L'import des données a été effectué avec succès.")

			return redirect('import_bee')

	else:
		form = ImportBEEForm()

	annee_actuelle = Annee.objects.get_actuelle()

	horodatages = ImportBeeLog.objects.filter(
		annee=annee_actuelle).values('import_type'
		).annotate(date_import=Max('date_import')
		).values('date_fichier', 'date_import', 'import_type')
	bee_types = dict(ImportBeeLog.IMPORT_TYPE_CHOICES)
	for horodatage in horodatages:
		horodatage['import_fichier'] = bee_types[horodatage['import_type']]

	return render(request, 'pykol/import_bee.html', context={
		'form': form,
		'annee_scolaire_none': not(Annee.objects.all()),
		'horodatages': horodatages,
		'annee': annee_actuelle,
	})
