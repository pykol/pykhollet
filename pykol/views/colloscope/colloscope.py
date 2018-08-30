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

"""Affichage et édition du colloscope."""

from collections import defaultdict, OrderedDict

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table, TableColumn, TableRow, TableCell
from odf.style import Style, TableColumnProperties, TableRowProperties, \
        TextProperties, ParagraphProperties
from odf.text import P

from pykol.models import constantes
from pykol.models.base import Classe
from pykol.models.colles import Colle
from pykol.forms.colloscope import ColloscopeImportForm
from pykol.lib.odftools import tablecell_to_text, iter_columns

@login_required
def colloscope(request, slug):
	"""
	Affichage du colloscope complet, en fonction du format qui a été
	demandé par l'utilisateur.
	"""
	classe = get_object_or_404(Classe, slug=slug)
	if not request.user.has_perm('pykol.view_colloscope', classe):
		raise PermissionDenied

	res_format = request.GET.get('format', None)
	if res_format == 'odf':
		return colloscope_odf(request, classe)
	else:
		return colloscope_html(request, classe)

def colloscope_html(request, classe):
	"""
	Affichage du colloscope complet d'une classe au format HTML
	"""
	semaines = classe.semaine_set.order_by('debut')
	creneaux = classe.creneau_set.order_by('enseignement', 'jour', 'debut')
	colles = classe.colle_set.all()

	colloscope = defaultdict(OrderedDict)
	for creneau in creneaux:
		colloscope[creneau.matiere][creneau] = OrderedDict([
				(semaine, []) for semaine in semaines])

	autres_colles = []
	for colle in colles:
		try:
			colloscope[colle.matiere][colle.creneau][colle.semaine].append(colle)
		except:
			autres_colles.append(colle)

	perm_creation = request.user.has_perm('pykol.add_colle', classe)
	perm_change_colloscope = request.user.has_perm('pykol.change_colloscope', classe)
	# La conversion de colloscope en dict est obligatoire, car les
	# gabarits Django ne peuvent pas itérer sur les defaultdict
	# facilement : l'appel colloscope.items est d'abord converti en
	# colloscope['items'] et non en colloscope.items().
	return render(request, 'pykol/colloscope/view_colloscope.html',
			context={
				'classe': classe,
				'semaines': semaines,
				'colloscope': dict(colloscope),
				'perm_creation': perm_creation,
				'perm_change_colloscope': perm_change_colloscope,
				'autres_colles': autres_colles,
				})

def colloscope_odf(request, classe):
	"""
	Affichage du colloscope d'une classe au format OpenDocument
	"""
	response = HttpResponse(content_type='application/vnd.oasis.opendocument.spreadsheet')
	response['Content-Disposition'] = 'attachment; filename="colloscope_{}.ods"'.format(classe.slug)

	semaines = classe.semaine_set.order_by('debut')
	creneaux = classe.creneau_set.order_by('enseignement', 'jour', 'debut')
	colles = classe.colle_set.filter(semaine__in=semaines,
			creneau__in=creneaux)

	# On crée le dictionnaire qui à chaque créneau puis à chaque semaine
	# associe les groupes de colle
	colloscope = defaultdict(lambda: defaultdict(list))
	for colle in colles:
		colloscope[colle.creneau][colle.semaine].append(colle)

	ods = OpenDocumentSpreadsheet()
	# Styles
	style_entete = Style(parent=ods.automaticstyles,
			name='cell_entete', family='table-cell')
	TextProperties(parent=style_entete, fontweight='bold')

	table = Table(name=str(classe), parent=ods.spreadsheet)

	# Ajout des colonnes d'en-tête fixes
	entetes_fixes = ("ID", "Matière", "Colleur", "Jour", "Horaire", "Salle")
	table.addElement(TableColumn()) # ID
	table.addElement(TableColumn()) # Matière
	table.addElement(TableColumn()) # Colleur
	table.addElement(TableColumn()) # Jour
	table.addElement(TableColumn()) # Horaire
	table.addElement(TableColumn()) # Salle

	# Ajout des colonnes d'en-tête des semaines
	style_col_semaine = Style(parent=ods.automaticstyles,
			name='col_semaine', family='table-column')
	TableColumnProperties(parent=style_col_semaine, columnwidth='1cm')
	for _ in semaines:
		table.addElement(TableColumn(stylename=style_col_semaine))

	# Ligne d'en-tête avec les semestres au-dessus des semaines
	tr = TableRow(parent=table)
	for entete in entetes_fixes:
		P(parent=TableCell(parent=tr, valuetype='string',
			numberrowsspanned=2, numbercolumnsspanned=1,
			stylename=style_entete), text=entete)

	# On doit savoir combien de semaines se trouvent sur chaque période
	# pour afficher les en-têtes sur le bon nombre de colonnes
	nb_semaines = dict([
		(
			periode[0],
			0,
		)
		for periode in constantes.PERIODE_CHOICES
	])
	for semaine in semaines:
		nb_semaines[semaine.periode] += 1

	# Insertion des titres des périodes
	for periode_id, periode_nom in constantes.PERIODE_CHOICES:
		if nb_semaines[periode_id] > 0:
			P(parent=TableCell(parent=tr, valuetype='string',
				numbercolumnsspanned=nb_semaines[periode_id],
				numberrowsspanned=1,
				stylename=style_entete), text=periode_nom.capitalize())
			TableCell(parent=tr,
					numbercolumnsrepeated=nb_semaines[periode_id] - 1)

	tr = TableRow(parent=table)
	# Ligne d'en-tête avec seulement les semaines
	# On doit placer des cellules vides pour les case d'en-tête situées
	# avant les semaines
	TableCell(parent=tr, numbercolumnsrepeated=len(entetes_fixes))
	# Puis on ajoute les semaines
	for semaine in semaines:
		P(parent=TableCell(parent=tr, valuetype='string',
			stylename=style_entete), text=semaine.numero)

	# Colles par créneau
	for creneau in creneaux:
		tr = TableRow(parent=table)
		P(parent=TableCell(parent=tr, valuetype='string'),
				text=creneau.pk)
		P(parent=TableCell(parent=tr, valuetype='string'),
				text=creneau.matiere)
		P(parent=TableCell(parent=tr, valuetype='string'),
				text=creneau.colleur)
		P(parent=TableCell(parent=tr, valuetype='string'),
				text=creneau.get_jour_display())
		P(parent=TableCell(parent=tr, valuetype='string'),
				text=creneau.debut)
		P(parent=TableCell(parent=tr, valuetype='string'),
				text=creneau.salle)
		for semaine in semaines:
			P(parent=TableCell(parent=tr, valuetype='string'),
				text=','.join([str(c.groupe) for c in
					colloscope[creneau][semaine] if c.groupe]))

	ods.write(response)
	return response

@login_required
def import_odf(request, slug):
	"""
	Import du colloscope au format OpenDocument

	Le fichier doit avoir le même format que celui produit par la vue
	colloscope_odf. L'utilisateur doit seulement avoir indiqué les
	numéros des groupes pour chaque créneau et pour chaque semaine.
	"""
	classe = get_object_or_404(Classe, slug=slug)

	if not request.user.has_perm('pykol.change_colloscope', classe):
		raise PermissionDenied

	semaines = list(classe.semaine_set.order_by('debut'))
	creneaux = dict([(c.pk, c) for c in classe.creneau_set.all()])
	groupes = {
		constantes.PERIODE_PREMIERE:
			dict([(g.nom, g) for g in classe.trinomes.filter(
				periode__in=(constantes.PERIODE_ANNEE,
					constantes.PERIODE_PREMIERE)
			)]),
		constantes.PERIODE_DEUXIEME:
			dict([(g.nom, g) for g in classe.trinomes.filter(
				periode__in=(constantes.PERIODE_ANNEE,
					constantes.PERIODE_DEUXIEME)
			)]),
	}

	# Liste des erreurs rencontrées lors de l'import du fichier. C'est
	# un triplet de la forme (code_erreur, (ligne, colonne), message),
	# où ligne, colonne et/ou leur couple peuvent être None si l'erreur
	# ne concerne pas une position particulière dans le fichier.
	import_erreurs = []

	if request.method == 'POST':
		form = ColloscopeImportForm(request.POST, request.FILES)

		if form.is_valid():
			# Supprimer toutes les anciennes colles pas encore réalisées
			if form.cleaned_data.get('supprimer'):
				Colle.objects.filter(classe=classe,
						etat__in=(Colle.ETAT_PREVUE,
							Colle.ETAT_BROUILLON)).delete()

			# Un grand try attrape toute erreur d'import qui nous aurait
			# échappée à l'intérieur du traitement.
			try:
				# Créer les colles à partir du fichier
				colloscope_ods = load(request.FILES['colloscope_ods'])
				table = colloscope_ods.spreadsheet.getElementsByType(Table)[0]
				lignes = table.getElementsByType(TableRow)

				# Colonnes fixées par l'export ODF
				nb_entetes_fixes = 5

				for ligne_num, ligne in enumerate(lignes[2:], 2):
					cells = iter_columns(ligne)

					try:
						id_creneau = int(tablecell_to_text(next(cells)))
						creneau = creneaux[id_creneau]
					except:
						import_erreurs.append(('creneau_invalide',
							(ligne_num, 0),
							"La valeur n'est pas un numéro de créneau "
							"valide pour cette classe."))
						continue

					try:
						# On ignore les colonnes fixes suivantes
						for _ in range(nb_entetes_fixes):
							next(cells)
					except:
						# S'il n'y a plus aucune cellule à parcourir, on
						# considère que la ligne est vide et on passe à
						# la suivante.
						continue

					# Et on arrive aux semaines
					for sem_num, sem_cell in enumerate(cells):

						try:
							semaine = semaines[sem_num]
						except:
							import_erreurs.append(('semaine_invalide',
								(ligne_num, sem_num + nb_entetes_fixes),
								"Case située au-delà de la dernière "
								"semaine de colles."))
							break

						groupes_colles = [g.strip()
								for g in tablecell_to_text(sem_cell).split(",")
								if g.strip()]

						for num_groupe in groupes_colles:
							try:
								groupe = groupes[semaine.periode][num_groupe]
							except:
								# On signale les groupes qui n'existent
								# pas et on passe aux suivants.
								import_erreurs.append(('groupe_invalide',
									(ligne_num, sem_num + nb_entetes_fixes),
									"Identifiant de groupe de colle "
									"inconnu."))
								continue

							creneau.update_or_create_colle(semaine, groupe)

				if not import_erreurs:
					return redirect('colloscope', slug=classe.slug)

			except Exception as e:
				# TODO il pourrait être utile de logger l'exception e
				# pour dénicher des bugs
				import_erreurs.append(('fichier_invalide', None,
					"Votre fichier n'est pas au format demandé."))
	else:
		form = ColloscopeImportForm()

	return render(request, 'pykol/colloscope/import_odf.html', context={
		'classe': classe,
		'form': form,
		'import_erreurs': import_erreurs,
	})
