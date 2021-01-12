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
from itertools import zip_longest
import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table, TableColumn, TableRow, TableCell, \
		CoveredTableCell, TableHeaderRows
from odf.style import Style, TableColumnProperties, TableRowProperties, \
		TextProperties, ParagraphProperties
from odf.text import P

from pykol.models import constantes
from pykol.models.base import Classe
from pykol.models.colles import Colle
from pykol.forms.colloscope import ColloscopeImportForm
from pykol.lib.odftools import tablecell_to_text, iter_columns
from pykol.views.generic import OdfResponse

logger = logging.getLogger(__name__)

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
	style_col_semaine = Style(parent=ods.automaticstyles,
			name='col_semaine', family='table-column')
	TableColumnProperties(parent=style_col_semaine, columnwidth='1cm')
	style_col_matiere = Style(parent=ods.automaticstyles,
			name='col_matiere', family='table-column')
	TableColumnProperties(parent=style_col_matiere, columnwidth='5cm')
	style_col_colleur = Style(parent=ods.automaticstyles,
			name='col_colleur', family='table-column')
	TableColumnProperties(parent=style_col_colleur, columnwidth='5cm')
	style_col_salle = Style(parent=ods.automaticstyles,
			name='col_salle', family='table-column')
	TableColumnProperties(parent=style_col_salle, columnwidth='2cm')

	table = Table(name=str(classe), parent=ods.spreadsheet)

	# Ajout des colonnes d'en-tête fixes
	entetes_fixes = ("ID", "Matière", "Colleur", "Jour", "Horaire", "Salle")
	table.addElement(TableColumn(stylename=style_col_semaine)) # ID
	table.addElement(TableColumn(stylename=style_col_matiere)) # Matière
	table.addElement(TableColumn(stylename=style_col_colleur)) # Colleur
	table.addElement(TableColumn()) # Jour
	table.addElement(TableColumn()) # Horaire
	table.addElement(TableColumn(stylename=style_col_salle)) # Salle

	# Ajout des colonnes d'en-tête des semaines
	for _ in semaines:
		table.addElement(TableColumn(stylename=style_col_semaine))

	# Container pour les lignes d'en-tête
	th = TableHeaderRows(parent=table)
	# Ligne d'en-tête avec les semestres au-dessus des semaines
	tr = TableRow(parent=th)
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
			CoveredTableCell(parent=tr,
					numbercolumnsrepeated=nb_semaines[periode_id] - 1)

	tr = TableRow(parent=th)
	# Ligne d'en-tête avec seulement les semaines
	# On doit placer des cellules vides pour les case d'en-tête situées
	# avant les semaines
	CoveredTableCell(parent=tr, numbercolumnsrepeated=len(entetes_fixes))
	# Puis on ajoute les semaines
	for semaine in semaines:
		P(parent=TableCell(parent=tr, valuetype='string',
			stylename=style_entete), text=semaine.numero)

	# Colles par créneau
	for creneau in creneaux:
		tr = TableRow(parent=table)
		P(parent=TableCell(parent=tr, valuetype='float', value=creneau.pk),
			text=creneau.pk)
		P(parent=TableCell(parent=tr, valuetype='string'),
				text=creneau.matiere)
		P(parent=TableCell(parent=tr, valuetype='string'),
				text=creneau.colleur)
		P(parent=TableCell(parent=tr, valuetype='string'),
				text=creneau.get_jour_display())
		P(parent=TableCell(parent=tr, valuetype='time',
				timevalue=creneau.debut.strftime("PT%HH%MM%SS")),
				text=creneau.debut.strftime("%H:%M"))
		P(parent=TableCell(parent=tr, valuetype='string'),
				text=creneau.salle)
		for semaine in semaines:
			groupes_texte = ','.join([str(c.groupe) for c in
					colloscope[creneau][semaine] if c.groupe])
			cell = TableCell(parent=tr)
			if groupes_texte:
				cell.valuetype="string"
				P(parent=cell, text=groupes_texte)

	return OdfResponse(ods, filename="colloscope_{}.ods".format(classe.slug))

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
						# On ignore les lignes qui commencent par un
						# numéro vide.
						creneau_text = tablecell_to_text(next(cells)).strip()
						if not creneau_text:
							continue
						id_creneau = int(creneau_text)
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
					for sem_num, (sem_cell, semaine) in enumerate(zip_longest(cells, semaines)):
						# On récupére le contenu de la cellule et on tente de
						# deviner la semaine. En fonction des quatre cas
						# possibles pour ce couple de valeurs (vide ou non pour
						# chacune), le traitement est différent.
						if sem_cell is None:
							groupes_text = None
						else:
							groupes_text = tablecell_to_text(sem_cell).strip()

						if semaine is None:
							# On trouve du contenu dans une case qui ne
							# correspond à aucune semaine du colloscope. On
							# signale l'erreur. Si le contenu de la case est
							# vide, on ne signale rien : c'est juste un
							# reliquat fantôme du tableur.
							if groupes_text:
								import_erreurs.append(('semaine_invalide',
									(ligne_num, sem_num + nb_entetes_fixes),
									"Case située au-delà de la dernière "
									"semaine de colles."))

							# Et dans tous les cas on passe à ligne suivante,
							# il n'y a plus aucune semaine intéressante à
							# attendre sur cette ligne.
							break

						elif groupes_text:
							# Cas où on trouve une liste de groupes pour une
							# semaine connue. On met à jour les colles.
							groupes_colles = [g.strip()
									for g in groupes_text.split(",")
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

								try:
									Colle.objects.update_or_create_from_creneau(creneau, semaine, groupe)
								except:
									import_erreurs.append(('update_echoue',
										(ligne_num, sem_num + nb_entetes_fixes),
										"Échec de la mise à jour de cette "
										"colle."))

						else:
							# Cas où la case de la semaine est vide. On
							# supprime les colles qui s'y trouveraient déjà
							# dans la base de données.
							for colle in Colle.objects.filter(creneau=creneau, semaine=semaine):
								if not colle.est_effectuee:
									colle.annuler_mouvement()
									colle.delete()

				if not import_erreurs:
					return redirect('colloscope', slug=classe.slug)

			except Exception as e:
				import_erreurs.append(('fichier_invalide', None,
					"Votre fichier n'est pas au format demandé."))
				logger.exception("Erreur inconnue lors de l'importation d'un colloscope",
						exc_info=e)
	else:
		form = ColloscopeImportForm()

	return render(request, 'pykol/colloscope/import_odf.html', context={
		'classe': classe,
		'form': form,
		'import_erreurs': import_erreurs,
	})
