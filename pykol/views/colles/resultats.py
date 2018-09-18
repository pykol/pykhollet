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

"""
Vues d'affichage des résultats de colles des étudiants.
"""

from collections import defaultdict, OrderedDict, namedtuple
from datetime import timedelta

from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.http import HttpResponse

from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table, TableColumn, TableRow, TableCell, \
		CoveredTableCell, TableHeaderRows
from odf.style import Style, TableColumnProperties, TableRowProperties, \
        TextProperties, ParagraphProperties
from odf.number import Number, NumberStyle
from odf.text import P

from pykol.models.base import Classe, Matiere, Etudiant
from pykol.models.colles import Semaine, ColleNote, Colle
from pykol.models.fields import Moyenne, Note
from pykol.lib.auth import professeur_dans
from pykol.lib.sortedcollection import SortedCollection

SemaineTuple = namedtuple('SemaineTuple', ('debut', 'fin',
	'numero'))

def tableau_resultats(classe, matieres):
	"""
	Création du tableau des résultats de colles pour la classe donnée
	Cette vue affiche les résultats de la classe uniquement pour les
	colles dans les matières données en paramètres.
	"""

	def semaine_to_tuple(semaine):
		return SemaineTuple(debut=semaine.debut,
				fin=semaine.fin,
				numero=semaine.numero)

	def meilleure_semaine(date, semaines):
		"""
		Renvoie l'élément de la liste semaines (SortedCollection
		d'objets Semaine) dont les dates de début et de fin encadrent la
		date donnée en paramètre.

		Si une telle semaine n'existe pas, on en crée une fictive (non
		sauvée dans la base de données) et on l'insère dans la liste
		triée semaines.
		"""
		try:
			semaineColle = semaines.find_le(date)
			if semaineColle.fin >= date:
				return semaineColle
		except:
			pass

		# Quand aucune semaine de colle n'a été trouvée, on en crée
		# une fictive qui ne sera pas stockée dans la base de
		# données.
		debut_semaine = date - timedelta(days=date.weekday())
		fin_semaine = debut_semaine + timedelta(days=6)
		semaineColle = SemaineTuple(debut=debut_semaine, fin=fin_semaine,
			numero="({0}-{1})".format(*debut_semaine.isocalendar()))
		semaines.insert(semaineColle)

		return semaineColle

	def getSemaine(colleNoteEtudiant, semaines):
		"""
		Renvoie l'élément de la liste semaines (SortedCollection
		d'objets Semaine) dont les dates de début et de fin encadrent la
		date de la ColleNote.

		Si l'objet ColleNote fait référence à une colle qui a un
		attribut semaine, on utilise cette semaine : on affiche ainsi le
		résultat de la colle à la date où elle était initialement
		prévue, peu importe si elle a été déplacée par la suite.

		Sinon, on tente de trouver une semaine correspondante parmi les
		semaines du colloscope. Si une telle semaine n'existe pas, on en
		crée une fictive (non sauvée dans la base de données) et on
		l'insère dans la liste triée semaines.
		"""
		if colleNoteEtudiant.colle.semaine:
			return semaine_to_tuple(colleNoteEtudiant.colle.semaine)
		else:
			return meilleure_semaine(colleNoteEtudiant.horaire.date(),
				semaines)

	def calculerRangs(etudiants, moyennesParEtudiant):
		rangParEtudiant = defaultdict(lambda: '')
		couplesEtudiantMoyenne = sorted(moyennesParEtudiant.items(),
				key=lambda v:v[1], reverse=True)
		if couplesEtudiantMoyenne:
			noteCourante = couplesEtudiantMoyenne[0][1] # noteMax
			rangCourant = 1 # pour la gestion des exaequo
			idRang = 1
			for (etudiant, moyenne) in couplesEtudiantMoyenne:
				if moyenne < noteCourante:
					noteCourante = moyenne
					rangCourant = idRang
				idRang += 1
				rangParEtudiant[etudiant] = rangCourant
		return rangParEtudiant

	semaines = SortedCollection([
		semaine_to_tuple(s) for s in Semaine.objects.filter(classe=classe,
			debut__lte=timezone.localtime())],
			key=lambda semaine: semaine.debut)

	notesParEtudiantParMatiere = {}

	for matiere in matieres:
		# etudiants = Etudiant.objects.filter(classe = classe, groupe__enseignement__matiere = matiere).order_by('last_name','first_name')
		etudiants = Etudiant.objects.filter(classe = classe).order_by('last_name','first_name')

		notesParEtudiant = OrderedDict()
		moyennesParEtudiant = defaultdict(Moyenne)
		for etudiant in etudiants:
			notesParEtudiant[etudiant] = defaultdict(list)

		colleNoteEtudiant_s = ColleNote.objects.filter(
			colle__enseignement__matiere = matiere,
			eleve__in = etudiants
		)

		for colleNoteEtudiant in colleNoteEtudiant_s:
			semaineColle = getSemaine(colleNoteEtudiant, semaines)
			notesParEtudiant[colleNoteEtudiant.eleve][semaineColle].append(colleNoteEtudiant.note)
			moyennesParEtudiant[colleNoteEtudiant.eleve] += colleNoteEtudiant.note

		rangsParEtudiant = calculerRangs(etudiants, moyennesParEtudiant)

		# remarque : les deux requetes peuvent être mises avant la boucle sur les matieres si c'est plus rapide
		colles = Colle.objects.filter(
			classe = classe,
			enseignement__matiere = matiere,
			etat = Colle.ETAT_PREVUE,
			colledetails__actif=True,
			colledetails__horaire__lte=timezone.localtime(),
		).exclude(collenote__isnull = False)

		for colle in colles:
			for eleve in colle.details.eleves.all():
				if colle.semaine:
					semaine = semaine_to_tuple(colle.semaine)
				else:
					semaine = meilleure_semaine(colle.details.horaire.date(), semaines)
				notesParEtudiant[eleve][semaine].append(
					mark_safe('<i class="far fa-hourglass"></i>'))

		# On remplace les dictionnaires des semaines par des listes pour faciliter
		# l'affichage
		semaines = list(semaines)
		for etudiant in etudiants:
			notesParEtudiant[etudiant] = [[moyennesParEtudiant[etudiant]],
					[rangsParEtudiant[etudiant]]] + \
					[notesParEtudiant[etudiant][semaine] for semaine in
							semaines]

		notesParEtudiantParMatiere[matiere] = notesParEtudiant

	return {'matieres': notesParEtudiantParMatiere,
			'semaines': semaines}

def classe_resultats_html(request, resultats):
	return render(request, 'pykol/colles/classe_resultats.html',
			context=resultats)

def classe_resultats_odf(request, resultats):
	response = HttpResponse(content_type='application/vnd.oasis.opendocument.spreadsheet')
	response['Content-Disposition'] = 'attachment; filename="resultats_{}.ods"'.format(resultats['classe'])

	ods = OpenDocumentSpreadsheet()

	# Style numérique pour les notes
	style_number_note = NumberStyle(name="Note")
	ods.styles.addElement(style_number_note)
	Number(parent=style_number_note, minintegerdigits=1, decimalplaces=2)
	style_note = Style(datastylename=style_number_note,
			parent=ods.styles, name="Note", family='table-cell')

	for matiere, etudiants in resultats['matieres'].items():
		table = Table(name="{} - {}".format(resultats['classe'], matiere),
				parent=ods.spreadsheet)

		# Création des colonnes
		table.addElement(TableColumn()) # Étudiant
		table.addElement(TableColumn()) # Moyenne
		table.addElement(TableColumn()) # Rang
		for _ in range(len(resultats['semaines'])):
			table.addElement(TableColumn())

		# Ligne d'en-tête
		th = TableHeaderRows(parent=table)
		tr = TableRow(parent=th)
		P(parent=TableCell(parent=tr, valuetype='string'), text="Étudiant")
		P(parent=TableCell(parent=tr, valuetype='string'), text="Moyenne")
		P(parent=TableCell(parent=tr, valuetype='string'), text="Rang")
		for semaine in resultats['semaines']:
			P(parent=TableCell(parent=tr, valuetype='string'),
				text=semaine.numero)

		# Ligne pour chaque étudiant
		for etudiant, notes in etudiants.items():
			tr = TableRow(parent=table)
			P(parent=TableCell(parent=tr, valuetype='string'), text=str(etudiant))
			for note in notes:
				tc = TableCell(parent=tr)

				if isinstance(note, list) and len(note) == 1:
					note = note[0]

				if isinstance(note, int):
					tc.setAttribute('valuetype', 'float')
					tc.setAttribute('value', note)
					tc.setAttribute('stylename', style_note)
					P(text="{}".format(note), parent=tc)

				elif isinstance(note, Note):
					if note.est_note():
						tc.setAttribute('valuetype', 'float')
						tc.setAttribute('value', note.value)
						tc.setAttribute('stylename', style_note)
					P(text="{:.2f}".format(note), parent=tc)

				elif isinstance(note, list):
					P(text=', '.join(["{:.2f}".format(n) for n in note
						if isinstance(n, Note)]), parent=tc)

	ods.write(response)
	return response

@login_required
def classe_resultats(request, slug):
	classe = get_object_or_404(Classe, slug=slug)
	# L'accès n'est autorisé qu'aux professeurs de la classe
	if not request.user.has_perm('pykol.view_resultats', classe):
		raise PermissionDenied

	matieres = Matiere.objects.filter(
		enseignement__classe = classe,
		enseignement__service__professeur=request.user
	).union(Matiere.objects.filter(
		enseignement__classe=classe,
		enseignement__creneau__colleur=request.user
	)).order_by('nom')

	resultats = tableau_resultats(classe, matieres)
	resultats['classe'] = classe

	if request.GET.get('format', 'html') == 'odf':
		return classe_resultats_odf(request, resultats)
	else:
		return classe_resultats_html(request, resultats)
