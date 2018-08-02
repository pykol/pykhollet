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


"""Modèles pour la gestion des relevés des heures de colles
effectuées et leur mise en paiement."""

from datetime import timedelta

from django.db import models, transaction
from django.utils.timezone import localtime

from pykol.models.base import Annee, Professeur, Classe
from pykol.models.colles import Colle

class ColleReleve(models.Model):
	def default_annee():
		return Annee.actuelle.get().pk

	annee = models.ForeignKey(Annee, default=default_annee,
			on_delete=models.CASCADE)
	date = models.DateTimeField()
	date_paiement = models.DateTimeField(blank=True, null=True)

	ETAT_NOUVEAU = 0
	ETAT_PAYE = 1
	ETAT_CHOICES = (
			(ETAT_NOUVEAU, "Nouveau"),
			(ETAT_PAYE, "Payé"),
		)
	etat = models.PositiveSmallIntegerField(verbose_name="état",
			choices=ETAT_CHOICES, default=ETAT_NOUVEAU)

	class Meta:
		verbose_name = "relevé des colles"
		verbose_name_plural = "relevés des colles"

	@transaction.atomic
	def payer(self, date=None):
		if date is None:
			self.date_paiement = localtime()
		else:
			self.date_paiement = date
		self.etat = ColleReleve.ETAT_PAYE
		self.save()

	def maj_etat(self):
		if not self.lignes.filter(etat=ColleReleve.ETAT_NOUVEAU).exists():
			self.payer()

	@property
	def total_heures(self):
		total = self.lignes.aggregate(
				total_heures=models.Sum('duree'))['total_heures'] \
				or timedelta()
		return total.total_seconds() / 3600

	@transaction.atomic
	def ajout_colle(self, colle):
		"""
		Ajout d'une colle au relevé en cours.

		Cette fonction crée ou modifie l'objet ColleReleveLigne
		correspondant à la colle.
		"""
		# On ne paie pas deux fois les colles
		if colle.releve is not None:
			return

		ligne, _ = ColleReleveLigne.objects.get_or_create(
				releve=self,
				colleur=colle.colleur,
				taux=ColleReleveLigne.taux_colle(colle.classe))
		colle.etat = Colle.ETAT_RELEVEE
		colle.releve = self
		colle.save()
		ligne.ajout_colle(colle)

	def lignes_par_prof(self):
		return self.lignes.order_by('colleur', 'taux')

class ColleReleveLigne(models.Model):
	releve = models.ForeignKey(ColleReleve, on_delete=models.CASCADE,
			related_name='lignes')
	colleur = models.ForeignKey(Professeur, on_delete=models.CASCADE)

	TAUX_1A_INF20 = 1
	TAUX_1A_INF35 = 2
	TAUX_1A_SUP36 = 3
	TAUX_2A_INF20 = 4
	TAUX_2A_INF35 = 5
	TAUX_2A_SUP36 = 6

	TAUX_CHOICES = (
		(TAUX_1A_INF20, "1è année - Moins de 20 étudiants"),
		(TAUX_1A_INF35, "1è année - Entre 21 et 35 étudiants"),
		(TAUX_1A_SUP36, "1è année - Plus de 35 étudiants"),
		(TAUX_2A_INF20, "2è année - Moins de 20 étudiants"),
		(TAUX_2A_INF35, "2è année - Entre 21 et 35 étudiants"),
		(TAUX_2A_SUP36, "2è année - Plus de 35 étudiants"),
		)
	taux = models.PositiveSmallIntegerField(verbose_name="taux",
			choices=TAUX_CHOICES)
	duree_interrogation = models.DurationField(
			verbose_name="durée d'interrogation", default=timedelta)
	duree = models.DurationField(verbose_name="nombre d'heures",
			default=timedelta)

	ETAT_NOUVEAU = 0
	ETAT_PAYE = 1
	ETAT_CHOICES = (
			(ETAT_NOUVEAU, "Nouveau"),
			(ETAT_PAYE, "Payé"),
		)
	etat = models.PositiveSmallIntegerField(verbose_name="état",
			choices=ETAT_CHOICES,
			default=ETAT_NOUVEAU)
	date_paiement = models.DateTimeField(blank=True, null=True)

	@classmethod
	def taux_colle(cls, classe):
		"""
		Détermine le taux d'une colle en fonction de la classe
		"""
		if classe.niveau == Classe.NIVEAU_PREMIERE_ANNEE:
			if classe.effectif <= 20:
				return cls.TAUX_1A_INF20
			elif classe.effectif <= 35:
				return cls.TAUX_1A_INF35
			else:
				return cls.TAUX_1A_SUP36
		else:
			if classe.effectif <= 20:
				return cls.TAUX_2A_INF20
			elif classe.effectif <= 35:
				return cls.TAUX_2A_INF35
			else:
				return cls.TAUX_2A_SUP36

	@property
	def heures(self):
		return self.duree.total_seconds() / 3600

	@property
	def heures_interrogation(self):
		return self.duree_interrogation.total_seconds() / 3600

	def ajout_colle(self, colle):
		"""
		Ajout d'une Colle à la ligne de relevé actuelle
		"""
		# Cette fonction ne vérifie rien du tout (ni que le colleur est
		# le même, ni que la colle a été notée, ni le code de paiement).
		for collenote in colle.collenote_set.all():
			self.duree_interrogation += collenote.duree
		self.duree += timedelta(hours=1)
		self.save()

	@transaction.atomic
	def payer(self, date=None):
		if date is None:
			self.date_paiement = localtime()
		else:
			self.date_paiement = date
		self.etat = ColleReleveLigne.ETAT_PAYE
		self.save()

		self.releve.maj_etat()
