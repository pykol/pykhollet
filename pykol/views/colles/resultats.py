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

from pykol.models.base import Classe, Matiere, Etudiant
from pykol.models.colles import Semaine, ColleNote, Colle
from pykol.models.fields import Moyenne
from pykol.lib.auth import professeur_dans
from pykol.lib.sortedcollection import SortedCollection

@login_required
def classe_resultats(request, slug):
	"""
	Affichage du tableau des résultats de colle pour la classe donnée
	Cette vue affiche les résultats de la classe uniquement pour les
	colles dans une matière enseignée dans la classe par le professeur
	actuellement connecté. Dans tous les autres cas (si le professeur
	n'enseigne pas dans la classe, si l'utilisateur n'est pas un
	professeur), l'accès aux résultats est interdit.
	"""

	SemaineTuple = namedtuple('SemaineTuple', ('debut', 'fin',
		'numero'))

	def semaine_to_tuple(semaine):
		return SemaineTuple(debut=semaine.debut,
				fin=semaine.fin,
				numero=semaine.numero)

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

		date_colle = colleNoteEtudiant.horaire.date()

		try:
			semaineColle = semaines.find_le(date_colle)
			if semaineColle.fin >= date_colle:
				return semaineColle
		except:
			pass

		# Quand aucune semaine de colle n'a été trouvée, on en crée
		# une fictive qui ne sera pas stockée dans la base de
		# données.
		debut_semaine = date_colle - timedelta(days=date_colle.weekday())
		fin_semaine = debut_semaine + timedelta(days=6)
		semaineColle = SemaineTuple(debut=debut_semaine, fin=fin_semaine,
			numero="({0}-{1})".format(*debut_semaine.isocalendar()))
		semaines.insert(semaineColle)

		return semaineColle

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

	classe = get_object_or_404(Classe, slug=slug)
	# L'accès n'est autorisé qu'aux professeurs de la classe
	if not professeur_dans(request.user, classe):
		raise PermissionDenied

	matieres = Matiere.objects.filter(
		enseignement__classe = classe,
		enseignement__service__professeur = request.user
	).union(Matiere.objects.filter(
		enseignement__classe=classe,
		enseignement__creneau__colleur=request.user
	)).order_by('nom')

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
				notesParEtudiant[eleve][colle.semaine].append(
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

	context = {
		'matieres':notesParEtudiantParMatiere,
		'semaines':semaines,
	}

	return render(request, 'pykol/colles/classe_resultats.html', context=context)
