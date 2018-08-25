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

from collections import defaultdict, OrderedDict, namedtuple

from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin

from pykol.models.base import Etudiant, Matiere
from pykol.models.colles import Semaine, ColleNote
from pykol.models.fields import Moyenne
from pykol.lib.auth import professeur_dans

# TODO restreindre l'accès aux professeurs et colleurs qui ont
# l'étudiant en classe, à l'étudiant lui-même et à la direction.
class EtudiantDetailView(LoginRequiredMixin, generic.DetailView):
	model = Etudiant

	def get_context_data(self, **kwargs):
		"""
		Calcule un résumé des notes d'un étudiant pour les matières données.

		Cette fonction renvoie un dictionnaire indiquant les semaines de
		colles et les notes par matière de l'étudiant.
		"""
		context = super().get_context_data(**kwargs)
		etudiant = self.object

		# L'accès aux résultats n'est permis qu'à l'étudiant lui-même et aux
		# professeurs de la classe.
		if not (etudiant.user_ptr == self.request.user or
				professeur_dans(self.request.user, etudiant.classe)):
			return context

		# Récupération de la liste des matières, selon le profil de
		# l'utilisateur (professeur ou étudiant)
		try:
			matieres = list(Matiere.objects.filter(
				enseignement__classe__etudiant = etudiant,
				enseignement__service__professeur = self.request.user
			))
		except:
			try:
				matieres = list(Matiere.objects.filter(etudiant=self.request.user))
			except:
				matieres = []

		semaines = Semaine.objects.filter(classe__etudiant=etudiant).order_by('debut')

		collenotes = ColleNote.objects.filter(eleve=etudiant,
				colle__enseignement__matiere__in=matieres)

		NotesMatiere = namedtuple('NotesMatiere', ('moyenne', 'semaines'))
		notes = defaultdict(lambda: NotesMatiere(moyenne=Moyenne(),
			semaines=OrderedDict([(semaine, []) for semaine in semaines])))

		for collenote in collenotes:
			matiere = collenote.colle.matiere

			notes[matiere] = notes[matiere]._replace(moyenne=
					notes[matiere].moyenne + collenote.note)

			if collenote.colle.semaine:
				semaine = collenote.colle.semaine
			else:
				for sem in semaines:
					if sem.debut <= collenote.horaire <= sem.fin:
						semaine = sem
			notes[matiere].semaines[semaine].append(collenote.note)

		context.update({
			'notes': dict(notes),
			'semaines': semaines,
		})

		return context
