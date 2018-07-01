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

import datetime

from django.db import models
from django.urls import reverse

class Periode(models.Model):
	"""
	Période de l'année scolaire
	"""
	nom = models.CharField(max_length=100)
	debut = models.DateField(verbose_name="début")
	fin = models.DateField()

	class Meta:
		abstract = True
		verbose_name = 'période'
		verbose_name_plural = 'périodes'

	def contains(self, date):
		return self.debut <= date <= self.fin

class AnneeActuelleManager(models.Manager):
	"""
	Gestionnaire de l'année actuelle

	Ce gestionnaire ne renvoie qu'une seule année, l'année actuelle
	trouvée en fonction de la date du jour.
	"""
	def get_queryset(self):
		today = datetime.date.today()

		return super(AnneeActuelleManager,
				self).get_queryset().filter(fin__gte=today).order_by('debut')[:1]

class Annee(Periode):
	"""
	Année scolaire

	La plupart des données (groupes, classes, etc.) sont rattachées à
	une année scolaire. Ceci permet notamment de n'afficher que les
	données pertinentes à l'année en cours tout en conservant des
	archives des années précédentes. Ces archives peuvent être
	supprimées simplement en cascade suite à la suppression de l'année
	scolaire de la base de données.
	"""
	nom = models.CharField(max_length=100)
	debut = models.DateField(verbose_name="début")
	fin = models.DateField()

	objects = models.Manager()
	actuelle = AnneeActuelleManager()

	class Meta:
		ordering = ['debut']
		verbose_name = 'année scolaire'
		verbose_name_plural = 'années scolaires'

	def est_travaille(self, date):
		if self.weekday() == 6:
			return False
		for vacance in self.vacances.all():
			if vacance.contains(date):
				return False
		return True

	def dotation_totale(self):
		return self.dotation_set.aggregate(total=models.Sum('heures'))['total']

	def __str__(self):
		return self.nom

	def get_absolute_url(self):
		return reverse('annee_detail', args=(self.pk,))

class Vacances(Periode):
	"""
	Périodes de vacances scolaires, ou jours fériés
	"""
	annee = models.ForeignKey(Annee, on_delete=models.CASCADE,
		related_name='vacances')

	class Meta:
		verbose_name = 'vacances'
		verbose_name_plural = 'vacances'

	def __str__(self):
		return self.nom

