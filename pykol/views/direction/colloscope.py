# -*- coding: utf-8

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2018-2019 Florian Hatat
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

from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.views.generic.base import View

from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableColumn, TableRow, TableCell, \
		CoveredTableCell, TableHeaderRows
from odf.text import P
from odf.style import Style, TableColumnProperties, TextProperties

from pykol.models.base import Annee
from pykol.models.colles import Creneau
from pykol.forms.colloscope import CreneauSalleFormSet
from pykol.views.generic import OdfResponse

class CreneauOdfView(View):
	"""
	Liste de créneaux de colles au format OpenDocument
	"""
	def get(self, request, queryset, annee=None):
		creneaux_ods = OpenDocumentSpreadsheet()

		# Styles
		style_entete = Style(parent=creneaux_ods.automaticstyles,
				name='cell_entete', family='table-cell')
		TextProperties(parent=style_entete, fontweight='bold')
		style_col_colleur = Style(parent=creneaux_ods.automaticstyles,
				name='col_colleur', family='table-column')
		TableColumnProperties(parent=style_col_colleur, columnwidth='5cm')
		style_col_matiere = Style(parent=creneaux_ods.automaticstyles,
				name='col_matiere', family='table-column')
		TableColumnProperties(parent=style_col_matiere, columnwidth='5cm')
		style_col_standard = Style(parent=creneaux_ods.automaticstyles,
				name='col_standard', family='table-column')
		TableColumnProperties(parent=style_col_standard, columnwidth='2cm')

		table = Table(name="Créneaux de colles",
				parent=creneaux_ods.spreadsheet)

		# Définition des colonnes
		table.addElement(TableColumn(stylename=style_col_colleur)) # Colleur
		table.addElement(TableColumn(stylename=style_col_standard)) # Classe
		table.addElement(TableColumn(stylename=style_col_matiere)) # Matière
		table.addElement(TableColumn(stylename=style_col_standard)) # Début
		table.addElement(TableColumn(stylename=style_col_standard)) # Fin
		table.addElement(TableColumn(stylename=style_col_standard)) # Salle

		# En-tête de tableau
		# Container pour les lignes d'en-tête
		th = TableHeaderRows(parent=table)
		# Ligne d'en-tête
		tr = TableRow(parent=th)
		P(parent=TableCell(parent=tr, valuetype='string',
			stylename=style_entete), text="Colleur")
		P(parent=TableCell(parent=tr, valuetype='string',
			stylename=style_entete), text="Classe")
		P(parent=TableCell(parent=tr, valuetype='string',
			stylename=style_entete), text="Matière")
		P(parent=TableCell(parent=tr, valuetype='string',
			stylename=style_entete), text="Début")
		P(parent=TableCell(parent=tr, valuetype='string',
			stylename=style_entete), text="Fin")
		P(parent=TableCell(parent=tr, valuetype='string',
			stylename=style_entete), text="Salle")

		for creneau in queryset:
			tr = TableRow(parent=table)
			P(parent=TableCell(parent=tr, valuetype='string'), text=str(creneau.colleur))
			P(parent=TableCell(parent=tr, valuetype='string'), text=str(creneau.classe))
			P(parent=TableCell(parent=tr, valuetype='string'), text=str(creneau.matiere))
			P(parent=TableCell(parent=tr, valuetype='string'), text=str(creneau.debut))
			P(parent=TableCell(parent=tr, valuetype='string'), text=str(creneau.fin))
			P(parent=TableCell(parent=tr, valuetype='string'), text=str(creneau.salle))

		return OdfResponse(creneaux_ods,
			filename="creneaux-{annee}.ods".format(annee=annee))

@login_required
@permission_required('pykol.direction')
def creneau_list(request):
	"""Gestion de tous les créneaux de colle par la direction"""
	# On trie par nom de colleur, puis par colleur pour départager les
	# homonymes.
	creneaux_qs = Creneau.objects.filter(
			classe__annee=Annee.objects.get_actuelle()).order_by('colleur__last_name',
			'colleur__first_name', 'colleur', 'jour', 'debut')

	if request.method == 'GET' and request.GET.get('format', None) == 'odf':
		return CreneauOdfView.as_view()(request, creneaux_qs,
			annee=Annee.objects.get_actuelle())

	if request.method == 'POST':
		formset = CreneauSalleFormSet(request.POST, queryset=creneaux_qs)

		if formset.is_valid():
			formset.save()

	else:
		formset = CreneauSalleFormSet(queryset=creneaux_qs)

	return render(request, 'pykol/direction/creneau_list.html',
			context={'formset': formset})
