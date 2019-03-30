# -*- coding: utf-8

# pyKol - Gestion de colles en CPGE
# Copyright (c) 2019 Florian Hatat
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

from django.db import models, transaction
from django.urls import reverse

from pykol.models.base import Etudiant, Classe, Enseignement, \
		AbstractPeriode
from .grille import Grille, GrilleLigne

class JuryManager(models.Manager):
	@transaction.atomic
	def create_from_classe(self, classe, periode, **kwargs):
		"""
		Crée un jury pour une classe, en peuplant ce jury de mentions
		vierges pour toutes les matières suivies par les étudiants,
		selon les grilles ECTS présentes dans la base de données.
		"""
		jury = Jury(classe=classe, periode=periode, **kwargs)
		jury.save()

		# On recherche toutes les grilles qui peuvent s'appliquer à
		# cette classe.
		grilles = Grille.objects.filter(code_mef=classe.mef)

		if periode != Jury.PERIODE_ANNEE:
			grilles = grilles.filter(semestre=periode)

		# Pour chaque étudiant, on crée toutes les mentions qui
		# s'appliquent, en fonction des matières suivies par l'étudiant.
		for etudiant in classe.etudiants.all():
			grilles_applicables = grilles.filter_applicables(classe=classe,
					etudiant=etudiant)
			periodes_traitees = set()

			for grille in grilles_applicables:
				# On ne garde qu'une grille par semestre
				if grille.semestre in periodes_traitees:
					continue
				periodes_traitees.add(grille.semestre)

				enseignements = Enseignement.objects.filter_etudiant(
					etudiant=etudiant,
					classe=classe,
				)

				for ligne in grille.lignes.all():
					# On cherche un enseignement qui correspond à cette
					# ligne. Oui, c'est quadratique, mais vu le tout
					# petit nombre d'enseignements en pratique, il ne
					# semble pas bien pertinent d'optimiser la
					# complexité asymptotique.
					for enseignement in enseignements:
						if enseignement.matiere != ligne.matiere.matiere or \
							enseignement.rang_option != ligne.matiere.rang_option or \
							enseignement.modalite_option != ligne.matiere.modalite_option:
							continue

						Mention(etudiant=etudiant, jury=jury,
							enseignement=enseignement,
							credits=ligne.credits,
							grille_ligne=ligne).save()
						break
					else:
						# Code exécuté quand on n'a trouvé aucun
						# enseignement correspondant à la ligne parmi
						# les enseignements suivi par l'élève.
						# Certaines lignes doivent être créées de force
						# même si aucun enseignement n'est présent.
						if ligne.force_creation:
							Mention(etudiant=etudiant, jury=jury,
								credits=ligne.credits,
								grille_ligne=ligne).save()

				# TODO créer des mentions pour les enseignements
				# facultatifs suivis par l'élève.

		return jury

class Jury(AbstractPeriode, models.Model):
	"""
	Réunion de jury pour l'attribution des ECTS.
	"""
	date = models.DateTimeField()
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)

	ETAT_PREVU = 1
	ETAT_TERMINE = 2
	ETAT_CHOICES = (
		(ETAT_PREVU, "prévu"),
		(ETAT_TERMINE, "terminé"),
	)
	etat = models.PositiveSmallIntegerField(verbose_name="état",
		choices=ETAT_CHOICES, default=ETAT_PREVU)

	objects = JuryManager()

	def __str__(self):
		return "Jury {pk}".format(pk=self.pk)

	def get_absolute_url(self):
		return reverse('ects_jury_detail', kwargs={'pk': self.pk,})

class Mention(models.Model):
	"""
	Mention attribuée à un étudiant pour une matière donnée et un jury
	donné.

	La mention est considérée comme globale (pour l'ensemble de toutes
	les matières suite au jury pour l'étudiant) si l'enseignement est
	laissé vide.
	"""
	etudiant = models.ForeignKey(Etudiant, on_delete=models.CASCADE,
			verbose_name="étudiant")
	jury = models.ForeignKey(Jury, on_delete=models.CASCADE)
	enseignement = models.ForeignKey(Enseignement,
			on_delete=models.CASCADE, blank=True, null=True)

	MENTION_F = MENTION_INSUFFISANT = 0
	MENTION_E = MENTION_PASSABLE = 1
	MENTION_D = MENTION_CONVENABLE = 2
	MENTION_C = MENTION_ASSEZ_BIEN = 3
	MENTION_B = MENTION_BIEN = 4
	MENTION_A = MENTION_TRES_BIEN = 5
	MENTION_CHOICES = (
		(MENTION_F, "insuffisant"),
		(MENTION_E, "passable"),
		(MENTION_D, "convenable"),
		(MENTION_C, "assez bien"),
		(MENTION_B, "bien"),
		(MENTION_A, "très bien"),
	)
	mention = models.PositiveSmallIntegerField(choices=MENTION_CHOICES,
			blank=True, null=True)
	credits = models.PositiveSmallIntegerField(verbose_name="crédits")
	grille_ligne = models.ForeignKey(GrilleLigne,
			on_delete=models.PROTECT, blank=True, null=True)

	globale = models.BooleanField(help_text="Champ qui indique si "
		"cette mention est la mention globale de l'étudiant pour ce "
		"jury.", default=False)

	def __str__(self):
		return "Mention {}".format(self.pk)

	MENTION_LETTRES = ['F', 'E', 'D', 'C', 'B', 'A']
	def get_mention_lettre_display(self):
		return self.MENTION_LETTRES[self.mention]
