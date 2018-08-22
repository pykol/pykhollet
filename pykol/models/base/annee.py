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

import requests
import isodate

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

class AnneeManager(models.Manager):
	"""
	Gestionnaire qui ajoute l'accès à l'année actuelle.
	"""

	def get_actuelle(self):
		"""
		Renvoie l'année actuelle
		"""
		today = datetime.date.today()
		try:
			return self.get(debut__lte=today, fin__gte=today)
		except Annee.DoesNotExist:
			return None

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
	objects = AnneeManager()

	class Meta:
		ordering = ['debut']
		verbose_name = 'année scolaire'
		verbose_name_plural = 'années scolaires'

	def est_travaille(self, date):
		"""
		Renvoie True si et seulement si le paramètre date correspond à
		un jour travaillé de l'année scolaire.
		"""
		if self.weekday() == 6:
			return False
		for vacance in self.vacances.all():
			if vacance.contains(date):
				return False
		return True

	def dotation_totale(self):
		nb_heures = self.dotation_set.aggregate(total=models.Sum('heures'))['total'] or 0
		return datetime.timedelta(hours=nb_heures)

	def __str__(self):
		return self.nom

	def get_absolute_url(self):
		return reverse('annee_detail', args=(self.pk,))

	def synchro_vacances(self, academie):
		"""
		Mise à jour de la liste des vacances depuis les données publiées
		en open-data par le ministère.
		"""
		# Les dates de vacances sont données en prenant le dernier
		# jour de cours (vacances après la classe) et le premier
		# jour de reprise (reprise des cours le matin de la date de
		# fin). Or, pyKol stocke les périodes en prenant en compte
		# les jours inclus dans la période. Il faut donc décaler les
		# dates d'un jour.
		un_jour = datetime.timedelta(days=1)

		# Lors de la requête au serveur, on demande toute période de
		# vacances qui une intersection non vide avec l'année en cours.
		api_url = 'https://data.education.gouv.fr/api/records/1.0/download/'
		query = '(location={academie} AND start_date < {fin} AND end_date > {debut})'.format(
			academie=academie.nom.title(),
			debut="{0:%Y/%m/%d}".format(self.debut),
			fin="{0:%Y/%m/%d}".format(self.fin),
			)
		calendrier = requests.get(api_url, params={
			'dataset': 'fr-en-calendrier-scolaire',
			'format': 'json',
			'q': query,
		}).json()

		# Pas de fantôme vieille période vacances restant
		self.vacances.filter(type_vacances=Vacances.TYPE_VACANCES).delete()

		for vacances_json in calendrier:
			debut = isodate.parse_date(vacances_json['fields']['start_date']) \
					+ un_jour
			fin   = isodate.parse_date(vacances_json['fields']['end_date']) \
					- un_jour
			vacances = Vacances(
					annee=self,
					type_vacances=Vacances.TYPE_VACANCES,
					nom=vacances_json['fields']['description'],
					debut=debut,
					fin=fin,
				)
			vacances.save()

class Vacances(Periode):
	"""
	Périodes de vacances scolaires, ou jours fériés
	"""
	annee = models.ForeignKey(Annee, on_delete=models.CASCADE,
		related_name='vacances')

	TYPE_VACANCES = 1
	TYPE_FERIE = 2
	TYPE_CHOICES = (
		(TYPE_VACANCES, "vacances"),
		(TYPE_FERIE, "férié"),
	)
	type_vacances = models.PositiveSmallIntegerField(
			choices=TYPE_CHOICES, default=TYPE_VACANCES)

	class Meta:
		verbose_name = 'vacances'
		verbose_name_plural = 'vacances'

	def __str__(self):
		return self.nom
