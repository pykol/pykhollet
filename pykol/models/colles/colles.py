# -*- coding:utf8 -*-

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

from django.db import models, transaction
from django.urls import reverse

from pykol.models.base import Classe, Professeur, Matiere, Etudiant, Groupe
from pykol.models.fields import NoteField

# Liste des jours de la semaine, numérotation ISO
LISTE_JOURS = enumerate(["lundi", "mardi", "mercredi", "jeudi",
	"vendredi", "samedi", "dimanche"], 1)

class Colle(models.Model):
	"""
	Représentation d'une séance de colle
	"""
	creneau = models.ForeignKey('Creneau', blank=True, null=True,
			on_delete=models.SET_NULL, verbose_name="créneau")
	semaine = models.ForeignKey('Semaine', blank=True, null=True,
			on_delete=models.SET_NULL)
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)

	ETAT_PREVUE = 0
	ETAT_NOTEE = 1
	ETAT_RELEVEE = 2
	ETAT_ANNULEE = 3
	ETAT_CHOICES = (
			(ETAT_PREVUE, "Prévue"),
			(ETAT_NOTEE, "Notée"),
			(ETAT_RELEVEE, "Relevée"),
			(ETAT_ANNULEE, "Annulée"),
		)
	etat = models.PositiveSmallIntegerField(verbose_name="état",
			choices=ETAT_CHOICES, default=ETAT_PREVUE)
	matiere = models.ForeignKey(Matiere, blank=True, null=True,
			on_delete=models.SET_NULL, verbose_name="matière")
	groupe = models.ForeignKey(Groupe, blank=True, null=True,
			on_delete=models.SET_NULL, related_name='+')
	releve = models.ForeignKey('ColleReleve', blank=True, null=True,
			on_delete=models.SET_NULL)
	duree = models.DurationField(verbose_name="durée d'interrogation")

	@property
	def details(self):
		"""Renvoie le dernier ColleDetails actif pour cette colle"""
		return self.colledetails_set.get(actif=True)

	@property
	def colleur(self):
		"""Renvoie le colleur qui assure cette colle"""
		return self.details.colleur

	@transaction.atomic
	def ajout_details(self, horaire=None, salle='', colleur=None,
			etudiants=[]):
		"""
		Ajouter un ColleDetails qui met à jour le précédent.

		Si les étudiants, le colleur ou l'horaire ne sont pas précisés, on
		reprend ceux qui existaient déjà dans le ColleDetails précédent.

		Si la salle n'est pas indiquée, on ne reprend l'ancienne salle
		que si l'horaire de la colle n'a pas changé. Sinon, la
		réservation de salle n'est pas garantie et il vaut mieux laisser
		le champ vide.
		"""
		try:
			ancien_detail = self.details
			if not colleur:
				colleur = ancien_detail.colleur
			if not etudiants:
				etudiants = ancien_detail.eleves
			if not horaire:
				horaire = ancien_detail.horaire
			if not salle and horaire == ancien_detail.horaire:
				salle = ancien_horaire.salle

		except ColleDetails.DoesNotExist:
			ancien_detail = None

		self.colledetails_set.update(actif=False)

		detail = ColleDetails(colle=self, horaire=horaire, salle=salle,
				colleur=colleur)
		detail.save()
		detail.eleves.set(etudiants)

		return detail

	def get_absolute_url(self):
		return reverse('colle_detail', kwargs={'pk': self.pk})

class ColleDetails(models.Model):
	"""
	Détails sur le déroulement d'une colle (date, heure, lieu, élèves).

	Un seul ColleDetails peut être actif par colle. La liste des
	ColleDetails pour une même colle permet de conserver l'historique
	des modifications apportées à une colle (déplacement, changement de
	groupe ou de colleur).
	"""
	colle = models.ForeignKey(Colle, on_delete=models.CASCADE,
			db_index=True)
	horaire = models.DateTimeField()
	salle = models.CharField(max_length=30, blank=True)
	colleur = models.ForeignKey(Professeur, blank=True, null=True,
			on_delete=models.SET_NULL, db_index=True)
	eleves = models.ManyToManyField(Etudiant, blank=True,
			verbose_name="élèves", db_index=True)
	actif = models.BooleanField(default=True)

	class Meta:
		verbose_name = "détails de la colle"
		verbose_name_plural = "détails de la colle"

class ColleNote(models.Model):
	"""
	Note attribuée à une colle pour un étudiant.
	"""
	colle = models.ForeignKey(Colle, on_delete=models.CASCADE,
			db_index=True)
	eleve = models.ForeignKey(Etudiant, on_delete=models.CASCADE,
			db_index=True)
	note = NoteField()
	horaire = models.DateTimeField()
	duree = models.DurationField(verbose_name="durée d'interrogation")

	class Meta:
		verbose_name = "note de colle"
		verbose_name_plural = "notes de colle"
