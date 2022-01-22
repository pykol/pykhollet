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

from pykol.models.base import Classe, Etudiant, Enseignement
from pykol.models.colles import Semaine, ColleNote, Colle, \
		PeriodeNotation
from pykol.models.fields import Moyenne, Note
from pykol.forms.colles import PeriodeNotationInlineFormset
from pykol.lib.auth import professeur_dans
from pykol.lib.sortedcollection import SortedCollection

SemaineTuple = namedtuple('SemaineTuple', ('debut', 'fin',
	'numero'))

class KeyedDefaultDict:
	"""
	Structure de données qui se comporte comme un defaultdict, mais
	dont la liste des clés est fixée par le paramètre keys. La liste des
	clés peut évoluer avec le temps. La valeur courante de keys est
	utilisée lorsque l'on itère un KeyedDefaultDict.
	"""
	def __init__(self, keys, default):
		self._values = defaultdict(default)
		self._keys = keys

	def items(self):
		for key in self._keys:
			yield (key, self._values[key])

	def keys(self):
		return self._keys

	def __getitem__(self, key):
		if key not in self._keys:
			raise KeyError(key)
		return self._values[key]

	def __setitem__(self, key, item):
		if key not in self._keys:
			raise KeyError(key)
		self._values[key] = item

	def __iter__(self):
		for key in self._keys:
			yield self._values[key]

def tableau_resultats(classe, enseignements):
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
			semaine = semaine_to_tuple(colleNoteEtudiant.colle.semaine)
			if semaine not in semaines:
				semaines.insert(semaine)
			return semaine
		else:
			return meilleure_semaine(colleNoteEtudiant.horaire.date(),
				semaines)

	def calculerRangs(resultats):
		"""
		Fonction qui prend en paramètre un itérable qui à chaque clé
		associe un dictionnaire qui contient deux clés "moyenne" et
		"rang". Pour chaque clé k, resultats[k]['rang'] est modifié pour
		stocker un entier qui donne le rang, calculé d'après les valeurs
		de resultat[k]['moyenne'].
		"""
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

	# On construit le dictionnaire qui à chaque enseignement associe la
	# liste des périodes de notation.
	periodes = defaultdict(list)
	for periode in PeriodeNotation.objects.filter(
			enseignement__in=list(enseignements)).order_by('debut'):
		periodes[periode.enseignement].append(periode)

	# Construction du tableau des résultats pour chaque matière
	for enseignement in enseignements:
		#TODO on devrait se restreindre aux étudiants qui suivent cette
		# matière au lieu de prendre tous les étudiants de la classe.
		etudiants = Etudiant.objects.filter(collenote__colle__enseignement=enseignement).order_by('last_name','first_name')

		resultats = OrderedDict()
		for etudiant in etudiants:
			resultats[etudiant] = {
				'moyenne': Moyenne(),
				'rang' : None,
				'notes': KeyedDefaultDict(keys=semaines, default=list),
				'periodes' : {},
			}
			for periode in periodes[enseignement]:
				resultats[etudiant]['periodes'][periode] = {
					'moyenne': Moyenne(),
					'rang': None,
				}

		colleNoteEtudiant_s = ColleNote.objects.filter(
			colle__enseignement=enseignement,
			eleve__in = etudiants
		)

		# Ajout de toutes les notes de colles au tableau des résultats
		for colleNoteEtudiant in colleNoteEtudiant_s:
			etudiant = colleNoteEtudiant.eleve
			semaineColle = getSemaine(colleNoteEtudiant, semaines)
			resultats[etudiant]['notes'][semaineColle].append(colleNoteEtudiant.note)
			resultats[etudiant]['moyenne'] += colleNoteEtudiant.note
			# Mise à jour de la moyenne sur la période concernée. On ne
			# sort pas de la boucle dès qu'une période est trouvée, car
			# un professeur peut envisager de faire compter une même
			# note sur plusieurs périodes qui se chevauchent.
			for periode in periodes[enseignement]:
				if periode.debut <= semaineColle.debut <= periode.fin:
					resultats[etudiant]['periodes'][periode]['moyenne'] += \
						colleNoteEtudiant.note

		# XXX Calcul du rang général et du rang pour chaque période
		#calculerRangs(resultats)
		#for periode in periodes[enseignement]:
		#	calculerRangs(resultats['periodes'][periode])

		# Ajout au tableau des colles qui sont en attente de notation
		colles_non_notees = Colle.objects.filter(
			enseignement = enseignement,
			etat = Colle.ETAT_PREVUE,
			mode = Colle.MODE_INTERROGATION,
			colledetails__actif=True,
			colledetails__horaire__lte=timezone.localtime(),
		).exclude(collenote__isnull = False)

		for colle in colles_non_notees:
			# Les élèves présents sur une colle peuvent ne pas tous être
			# de la même classe.
			for etudiant in colle.details.eleves.intersection(etudiants):
				if colle.semaine:
					semaine = semaine_to_tuple(colle.semaine)
				else:
					semaine = meilleure_semaine(colle.details.horaire.date(), semaines)
				resultats[etudiant]['notes'][semaine].append(
					mark_safe('<i class="far fa-hourglass"></i>'))

		# Calcul des semaines pour chaque période de notation
		for periode in periodes[enseignement]:
			periode.semaines = semaines.between(periode.debut,
					periode.fin)

		notesParEtudiantParMatiere[enseignement] = {
				'etudiants': resultats,
				'periodes': periodes[enseignement],
		}

	return {
			'enseignements': notesParEtudiantParMatiere,
			'semaines': semaines,
		}


def classe_resultats_html(request, resultats):
	classe = resultats['classe']
	for enseignement in resultats['enseignements']:
		# Ajout des formulaires pour créer les périodes de notation
		if request.user.has_perm('pykol.change_periodenotation',
				enseignement):
			resultats['enseignements'][enseignement]['periode_form'] = \
				PeriodeNotationInlineFormset(instance=enseignement)

		# Ajout d'un itérateur pour créer l'en-tête en présence de périodes
		# de notation. Cet itérateur renvoie des couples (periode,
		# semaines) où semaines est la liste ordonnée des semaines
		# contenues dans la période periode. Lorsque des semaines
		# n'appartiennent à aucune période, l'itérateur renvoie un
		# couple (None, semaines).
		if resultats['enseignements'][enseignement]['periodes']:
			semaines = resultats['semaines']
			periodes = resultats['enseignements'][enseignement]['periodes']
			def periodes_entete():
				semaines_debut = semaines.items_lt(periodes[0].debut)
				if semaines_debut:
					yield (None, semaines_debut)

				prev_periode = None
				for periode in periodes:
					if prev_periode is not None:
						semaines_intercalaires = semaines.between(
							prev_periode.fin, periode.debut)
						if semaines_intercalaires:
							yield (None, semaines_intercalaires)
					yield (periode, semaines.between(periode.debut,
						periode.fin))
					prev_periode = periode

				if prev_periode is not None:
					semaines_fin = semaines.items_ge(prev_periode.fin)
					if semaines_fin:
						yield (None, semaines_fin)

			resultats['enseignements'][enseignement]['periodes_entete'] = periodes_entete

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

	# Style pour le rang
	style_number_rang = NumberStyle(name="Rang", parent=ods.styles)
	Number(parent=style_number_rang, minintegerdigits=1, decimalplaces=0)
	style_rang = Style(datastylename=style_number_rang,
			parent=ods.styles, name="Rang", family='table-column')

	for matiere, ens_resultats in resultats['enseignements'].items():
		table = Table(name="{} - {}".format(resultats['classe'], matiere),
				parent=ods.spreadsheet)

		# Création des colonnes
		table.addElement(TableColumn()) # Étudiant
		table.addElement(TableColumn()) # Moyenne
		table.addElement(TableColumn(stylename=style_rang)) # Rang
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
		for etudiant, etu_resultats in ens_resultats['etudiants'].items():
			tr = TableRow(parent=table)

			# Nom de l'étudiant
			P(parent=TableCell(parent=tr, valuetype='string'), text=str(etudiant))

			# Moyenne de l'étudiant
			P(parent=TableCell(parent=tr, valuetype='float',
					value=etu_resultats['moyenne'], stylename=style_note),
				text="{:.2f}".format(etu_resultats['moyenne']))

			# Rang de l'étudiant
			P(parent=TableCell(parent=tr, valuetype='float',
					value=etu_resultats['rang']),
				text="{}".format(etu_resultats['rang']))

			# Notes
			for note in etu_resultats['notes']:
				tc = TableCell(parent=tr)

				if isinstance(note, list) and len(note) == 1:
					note = note[0]

				if isinstance(note, Note):
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

	enseignements = Enseignement.objects.filter(
		classe = classe,
		service__professeur=request.user,
		collesenseignement__isnull=False,
	).union(Enseignement.objects.filter(
		classe=classe,
		creneau__colleur=request.user,
		collesenseignement__isnull=False,
	)).order_by('matiere')

	resultats = tableau_resultats(classe, enseignements)
	resultats['classe'] = classe

	if request.GET.get('format', 'html') == 'odf':
		return classe_resultats_odf(request, resultats)
	else:
		return classe_resultats_html(request, resultats)
