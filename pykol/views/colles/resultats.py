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

from django.core.exceptions import PermissionDenied
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.safestring import mark_safe

from pykol.models.base import Classe, Matiere, Etudiant
from pykol.models.colles import Semaine, ColleNote, Colle
from pykol.models.fields import Moyenne
from pykol.lib.auth import professeur_dans

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

	def getSemaine(colleNoteEtudiant):
		""" renvoie la semaine d'un colleNote
		TODO les langues """
		if colleNoteEtudiant.colle.semaine:
			semaineColle = colleNoteEtudiant.colle.semaine
		else:
			horaire = colleNoteEtudiant.horaire
			for semaine in semaines:
				if semaine.debut <= horaire.date() <= semaine.fin:
					semaineColle = semaine
		return semaineColle

	def calculerRangs(etudiants, moyennesParEtudiant):
		rangParEtudiant = defaultdict(lambda: '')
		couplesEtudiantMoyenne = sorted(moyennesParEtudiant.items(),
				key=lambda v:v[1], reverse=True)
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
	)
	semaines = Semaine.objects.filter(classe = classe)

	notesParEtudiantParMatiere = {}

	for matiere in matieres:
		etudiants = Etudiant.objects.filter(classe = classe, groupe__enseignement__matiere = matiere).order_by('last_name','first_name')

		notesParEtudiant = OrderedDict()
		moyennesParEtudiant = defaultdict(Moyenne)
		for etudiant in etudiants:
			notesParEtudiant[etudiant] = defaultdict(list)

		colleNoteEtudiant_s = ColleNote.objects.filter(
			colle__matiere = matiere,
			eleve__in = etudiants
		)

		for colleNoteEtudiant in colleNoteEtudiant_s:
			semaineColle = getSemaine(colleNoteEtudiant)
			notesParEtudiant[colleNoteEtudiant.eleve][semaineColle].append(colleNoteEtudiant.note)
			moyennesParEtudiant[colleNoteEtudiant.eleve] += colleNoteEtudiant.note

		rangsParEtudiant = calculerRangs(etudiants, moyennesParEtudiant)

		# remarque : les deux requetes peuvent être mises avant la boucle sur les matieres si c'est plus rapide
		colles = Colle.objects.filter(
			classe = classe,
			matiere = matiere,
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


@login_required
def etudiant_resultats(request, pk):
	"""
	Affichage des notes obtenues par un étudiant donné.

	L'accès n'est autorisé qu'aux professeurs de la classe ou qu'à
	l'étudiant lui-même.
	"""
	etudiant = get_object_or_404(Etudiant, pk=pk)

	if not (etudiant.user_ptr == request.user or
			professeur_dans(request.user, etudiant.classe)):
		raise PermissionDenied

	# Récupération de la liste des matières, selon le profil de
	# l'utilisateur (professeur ou étudiant)
	try:
		matieres = list(Matiere.objects.filter(
			enseignement__classe__etudiant = etudiant,
			enseignement__service__professeur = request.user
		))
	except:
		try:
			matieres = list(Matiere.objects.filter(etudiant=request.user))
		except:
			matieres = []

	semaines = Semaine.objects.filter(classe__etudiant=etudiant).order_by('debut')

	collenotes = ColleNote.objects.filter(eleve=etudiant, colle__matiere__in=matieres)

	NotesMatiere = namedtuple('NotesMatiere', ('moyenne', 'semaines'))
	notes = defaultdict(lambda: NotesMatiere(moyenne=Moyenne(),
		semaines=OrderedDict([(semaine, []) for semaine in semaines])))

	for collenote in collenotes:
		matiere = collenote.colle.matiere

		# notes[matiere].moyenne += collenote.note

		if collenote.colle.semaine:
			semaine = collenote.colle.semaine
		else:
			for sem in semaines:
				if sem.debut <= collenote.horaire <= sem.fin:
					semaine = sem
		notes[matiere].semaines[semaine].append(collenote.note)

	context = {
		'notes': dict(notes),
		'semaines': semaines,
		'etudiant': etudiant,
	}

	return render(request, 'pykol/colles/etudiant_resultats.html',
			context=context)
