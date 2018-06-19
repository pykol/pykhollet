# -*- coding:utf8 -*-

import datetime

from django.db import models

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

	def __str__(self):
		return self.nom

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

