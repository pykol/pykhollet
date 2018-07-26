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

from django.db import models

from pykol.models.base import Annee, Enseignement

class Dotation(models.Model):
	"""Délégation d'heures de colles par le rectorat"""

	annee = models.ForeignKey(Annee, on_delete=models.CASCADE)
	date = models.DateField()
	heures = models.IntegerField(verbose_name="nombre d'heures")

class CollesEnseignement(models.Model):
	"""
	Dotation en heures de colle pour les différents enseignements.
	"""
	enseignement = models.ForeignKey(Enseignement,
			on_delete=models.CASCADE)

	FREQUENCE_HEBDOMADAIRE = 1
	FREQUENCE_TRIMESTRIELLE = 2
	FREQUENCE_CHOICES = (
			(FREQUENCE_HEBDOMADAIRE, 'par semaine'),
			(FREQUENCE_TRIMESTRIELLE, 'par trimestre'),
		)
	frequence = models.SmallIntegerField(verbose_name="fréquence",
			choices=FREQUENCE_CHOICES)
	duree_frequentielle = models.DurationField(
			verbose_name="durée fréquentielle")

	PERIODE_ANNEE = 0
	PERIODE_PREMIERE = 1
	PERIODE_DEUXIEME = 2
	PERIODE_CHOICES = (
			(PERIODE_ANNEE, 'année complète'),
			(PERIODE_PREMIERE, 'première période'),
			(PERIODE_DEUXIEME, 'deuxième période'),
		)
	periode = models.SmallIntegerField(verbose_name="période",
			choices=PERIODE_CHOICES, default=PERIODE_ANNEE)

	@property
	def duree(self):
		"""
		Durée d'une interrogation.

		Par défaut, on considère que les colles à fréquence
		hebdomadaire d'après la réglementation sont effectuées à un
		rythme qui permet des interrogations de 20 minutes. Ainsi, si la
		réglementation prévoit 5 minutes par semaine et par élève, la
		colle est programmée une fois toutes les 4 semaines.

		Pour les colles trimestrielles, on prend la durée indiquée pour
		la période.
		"""
		if self.frequence == CollesEnseignement.FREQUENCE_HEBDOMADAIRE:
			return timedelta(minutes=20)
		else:
			return self.duree_frequentielle

	def dotation_heures_colles(self, classe):
		"""
		Calcule la dotation en heures de colles théorique pour cet
		enseignement dans la classe donnée.
		"""
		nb_etudiants = self.enseignement.etudiants_classe(classe).count()

		if self.frequence == CollesEnseignement.FREQUENCE_HEBDOMADAIRE:
			if self.periode == CollesEnseignement.PERIODE_ANNEE:
				mult = classe.get_nb_semaines()
			elif self.periode == CollesEnseignement.PERIODE_PREMIERE:
				# Fixé par l'arrêté du 10 février 1995 (RESK9500109A)
				mult = 18
			else: # Deuxième période
				mult = classe.get_nb_semaines() - 18
		else:
			mult = classe.get_nb_trimestres()

		return nb_etudiants * self.duree_frequentielle * mult

	def __str__(self):
		return str(self.enseignement)
