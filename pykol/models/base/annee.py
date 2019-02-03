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

from datetime import date, timedelta

from django.db import models
from django.urls import reverse

import requests
import isodate

from pykol.models import constantes

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

	@property
	def duree(self):
		return self.fin - self.debut + timedelta(days=1)

	def __str__(self):
		return self.nom

class AnneeManager(models.Manager):
	"""
	Gestionnaire qui ajoute l'accès à l'année actuelle.
	"""

	def get_actuelle(self):
		"""
		Renvoie l'année actuelle
		"""
		today = date.today()
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

	def est_vacances(self, date, seulement_vacances=True):
		"""
		Renvoie True si et seulement si la date correspond à un jour de
		vacances scolaires.

		Si le paramètre seulement_vacances vaut False, on regarde si
		la date tombe sur n'importe quel jour non travaillé (vacances ou
		jour férié).

		Si le paramètre seulement_vacances vaut True, on regarde
		uniquement si la date tombe sur une période de vacances.
		"""
		qs = self.vacances.filter(debut__lte=date, fin__gte=date)
		if seulement_vacances:
			qs = qs.filter(type_vacances=Vacances.TYPE_VACANCES)
		return qs.exists()

	def est_travaille(self, date, seulement_vacances=True):
		"""
		Renvoie True si et seulement si le paramètre date correspond à
		un jour travaillé de l'année scolaire.
		"""
		if date.weekday() == 6:
			return False

		return not self.est_vacances(date, seulement_vacances=seulement_vacances)

	def dotation_totale(self):
		nb_heures = self.dotation_set.aggregate(total=models.Sum('heures'))['total'] or 0
		return timedelta(hours=nb_heures)

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
		un_jour = timedelta(days=1)

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

	def lundi_premiere_semaine(self):
		"""
		Renvoie le lundi de la première semaine de cours de l'année
		scolaire.

		On suit la même convention que la norme ISO8601 : la première
		semaine est la première qui contient au moins quatre jours dans
		l'année scolaire.
		"""
		jour4 = self.debut + timedelta(days=3)
		lundi = jour4 - timedelta(days=jour4.weekday())
		return lundi

	def numero_semaine(self, date):
		"""
		Renvoie le numéro de la semaine d'enseignement qui contient la
		date donnée. Si aucune semaine de correspond, la fonction
		renvoie None.

		Les semaines sont numérotées à partir de 1.
		"""
		if date < self.debut or date > self.fin or \
				not self.est_travaille(date):
			return None

		depuis_debut = date - self.lundi_premiere_semaine()

		# On retire les jours contenus dans les vacances
		jours_vacances = sum([v.duree
			for v in self.vacances.filter(fin__lte=date,
				type_vacances=Vacances.TYPE_VACANCES
				)], timedelta())

		return (depuis_debut - jours_vacances).days // 7 + 1

	def periode_enseignement(self, date):
		"""
		Renvoie le numéro du semestre qui contient la date donnée.

		Le nombre de semaines du premier semestre est défini dans
		pykol.models.constantes.SEMAINES_PREMIERE_PERIODE.
		"""
		numero_semaine = self.numero_semaine(date)
		if numero_semaine is None:
			return None

		if numero_semaine <= constantes.SEMAINES_PREMIERE_PERIODE:
			return constantes.PERIODE_PREMIERE
		else:
			return constantes.PERIODE_DEUXIEME

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

	@property
	def duree(self):
		return self.fin - max(self.debut + timedelta(days=1), self.annee.debut)
