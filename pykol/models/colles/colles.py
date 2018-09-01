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

from datetime import timedelta

from django.db import models, transaction
from django.urls import reverse

from pykol.models.base import Classe, Professeur, Matiere, Etudiant, \
		Enseignement
from pykol.models.fields import NoteField

# Liste des jours de la semaine, numérotation ISO
LISTE_JOURS = enumerate(["lundi", "mardi", "mercredi", "jeudi",
	"vendredi", "samedi", "dimanche"], 1)

class ColleConfirmeeManager(models.Manager):
	"""
	Gestionnaire personnalisé sur les colles qui permet de n'afficher
	que les colles confirmées.
	"""
	def get_queryset(self):
		return super().get_queryset().exclude(etat=Colle.ETAT_BROUILLON)

class AbstractBaseColle(models.Model):
	"""
	Classe abstraite qui contient les champs communs entre une colle et
	un créneau de colle.
	"""
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
	enseignement = models.ForeignKey(Enseignement, blank=True,
			null=True, on_delete=models.SET_NULL)
	colles_ens = models.ForeignKey('CollesEnseignement', blank=True,
			null=True, on_delete=models.SET_NULL)
	duree = models.DurationField(verbose_name="durée",
			default=timedelta(hours=1))

	MODE_INTERROGATION = 0
	MODE_TD = 1
	MODE_CHOICES = (
			(MODE_INTERROGATION, "interrogation"),
			(MODE_TD, "travaux dirigés"),
		)
	mode = models.PositiveSmallIntegerField(
			verbose_name="mode de déroulement",
			choices=MODE_CHOICES,
			default=MODE_INTERROGATION)

	class Meta:
		abstract = True

	def basecolle_fields(self):
		"""Dictionnaire qui contient les valeurs des champs de base
		définis par la classe AbstractBaseColle. C'est un raccourci qui
		permet de reprendre rapidement les informations d'un Creneau
		pour créer une Colle."""
		return {
				'classe': self.classe,
				'enseignement': self.enseignement,
				'colles_ens': self.colles_ens,
				'duree': self.duree,
				'mode': self.mode,
			}

class Colle(AbstractBaseColle):
	"""
	Représentation d'une séance de colle
	"""
	creneau = models.ForeignKey('Creneau', blank=True, null=True,
			on_delete=models.SET_NULL, verbose_name="créneau")
	semaine = models.ForeignKey('Semaine', blank=True, null=True,
			on_delete=models.SET_NULL)

	ETAT_PREVUE = 0
	ETAT_NOTEE = 1
	ETAT_EFFECTUEE = 4
	ETAT_RELEVEE = 2
	ETAT_ANNULEE = 3
	ETAT_BROUILLON = 5
	ETAT_CHOICES = (
			(ETAT_BROUILLON, "brouillon"),
			(ETAT_PREVUE, "prévue"),
			(ETAT_NOTEE, "notée"),
			(ETAT_EFFECTUEE, "effectuée"),
			(ETAT_RELEVEE, "relevée"),
			(ETAT_ANNULEE, "annulée"),
		)
	etat = models.PositiveSmallIntegerField(verbose_name="état",
			choices=ETAT_CHOICES, default=ETAT_PREVUE)
	groupe = models.ForeignKey('Trinome', blank=True, null=True,
			on_delete=models.SET_NULL)
	releve = models.ForeignKey('ColleReleve', blank=True, null=True,
			on_delete=models.SET_NULL)

	# On remplace le gestionnaire objects, mais en prenant soin de
	# laisser le gestionnaire par défaut all_objects en première
	# position (c'est lui qui est utilisé par Django comme gestionnaire
	# de base).
	all_objects = models.Manager()
	objects = ColleConfirmeeManager()

	@property
	def details(self):
		"""Renvoie le dernier ColleDetails actif pour cette colle"""
		return self.colledetails_set.get(actif=True)

	@property
	def colleur(self):
		"""Renvoie le colleur qui assure cette colle"""
		return self.details.colleur

	def _update_duree(self):
		if self.colles_ens.frequence == self.colles_ens.FREQUENCE_HEBDOMADAIRE:
			self.duree = timedelta(hours=1)
		else:
			self.duree = self.details.eleves.count() * \
					self.colles_ens.duree_frequentielle
		self.save()

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

		En revanche, dans le cas où la salle n'était auparavant pas
		connue et qu'il s'agit de la seule information renseignée lors
		de l'appel, on ne crée pas de nouvelle ligne ColleDetails.
		(C'est le cas d'un déplacement de colle par le professeur avec
		réservation un peu plus tard de la salle par la direction.)

		Cette méthode renvoie le nouvel objet ColleDetails actif pour la
		colle.
		"""

		try:
			ancien_detail = self.details

			if not colleur:
				colleur = ancien_detail.colleur
			if not etudiants:
				etudiants = ancien_detail.eleves.all()
			if not horaire:
				horaire = ancien_detail.horaire

			# On reprend la salle uniquement quand l'horaire n'a pas
			# changé.
			if not salle and horaire == ancien_detail.horaire:
				salle = ancien_detail.salle

			detail_modifie = \
				colleur != ancien_detail.colleur or \
				set(etudiants) != set(ancien_detail.eleves.all()) or \
				horaire != ancien_detail.horaire

			# Cas où l'on ajoute une salle qui n'était précédemment pas
			# renseignée. Dans ce cas, on ne crée pas de nouveau
			# ColleDetails mais on met à jour l'actuel.
			if not detail_modifie and \
					not ancien_detail.salle and salle:
				ancien_detail.salle = salle
				ancien_detail.save()
				return ancien_detail

			detail_modifie = detail_modifie or \
				ancien_detail.salle != salle

		except ColleDetails.DoesNotExist:
			ancien_detail = None
			detail_modifie = True

		# Ajout d'un nouveau ColleDetails s'il y a des modifications
		if detail_modifie:
			self.colledetails_set.update(actif=False)

			detail = ColleDetails(colle=self, horaire=horaire, salle=salle,
				colleur=colleur)
			detail.save()
			detail.eleves.set(etudiants)

		self._update_duree()
		return self.details

	def get_absolute_url(self):
		return reverse('colle_detail', kwargs={'pk': self.pk})

	@property
	def matiere(self):
		return self.enseignement.matiere

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
