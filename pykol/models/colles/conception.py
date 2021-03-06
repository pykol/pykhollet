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

from datetime import datetime, timedelta

from django.db import models, transaction
from django.db.models import Q, F
from django.core.exceptions import ValidationError
from django.utils.timezone import make_aware

from pykol.models import constantes
from pykol.models.base import Classe, Professeur, Matiere, \
		Enseignement, AbstractBaseGroupe
from .colles import Colle, AbstractBaseColle

# Liste des jours de la semaine, numérotation ISO
LISTE_JOURS = enumerate(["lundi", "mardi", "mercredi", "jeudi",
	"vendredi", "samedi", "dimanche"], 1)

class Semaine(models.Model):
	"""Semaine de colles prévue au colloscope"""
	debut = models.DateField(verbose_name="début")
	fin = models.DateField()
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
	numero = models.TextField(verbose_name="numéro")

	class Meta:
		ordering = ['debut']

	def __str__(self):
		return "{} ({}/{}-{}/{})".format(self.numero, self.debut.day,
				self.debut.month, self.fin.day, self.fin.month)
	
	def horaire_creneau(self, creneau):
		"""
		Renvoie un objet datetime.datetime qui donne l'horaire (jour et
		heure) de début d'une colle placée sur le créneau donné dans
		la semaine.
		"""
		horaire = make_aware(datetime.combine(self.debut, creneau.debut))
		# On trouve ensuite le premier jour de la semaine qui est égal à
		# creneau.jour
		delta = (7 + creneau.jour - horaire.isoweekday()) % 7
		horaire += timedelta(days=delta)
		return horaire

	@property
	def periode(self):
		"""
		Semestre auquel est associé la semaine de colle.

		Le semestre est déterminé en prenant la date du premier jour de
		la semaine de colle.
		"""
		return self.classe.annee.periode_enseignement(self.debut)

class Creneau(AbstractBaseColle):
	"""Créneau de colle programmé au colloscope

	Un créneau de colle sert de modèle pour créer les Colle et les
	ColleDetail lors de la génération du colloscope.
	"""
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
	jour = models.PositiveSmallIntegerField(choices=LISTE_JOURS)
	debut = models.TimeField(verbose_name="début")
	fin = models.TimeField()
	salle = models.CharField(max_length=30, blank=True)
	colleur = models.ForeignKey(Professeur, blank=True, null=True,
			on_delete=models.SET_NULL)

	class Meta:
		verbose_name = 'créneau'
		verbose_name_plural = 'créneaux'
	
	def __str__(self):
		if not self.enseignement:
			matiere = "(Matière non renseignée)"
		else:
			matiere = self.enseignement.matiere

		return "{} ({}) {} {:%H:%M}-{:%H:%M}".format(matiere,
				self.colleur, self.get_jour_display(),
				self.debut, self.fin)

	@property
	def matiere(self):
		return self.enseignement.matiere

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		Colle.objects.filter(creneau=self, etat__in=(
			Colle.ETAT_PREVUE, Colle.ETAT_BROUILLON)).synchro_creneau()

class Trinome(AbstractBaseGroupe):
	"""Groupe de colle dans une classe"""
	classe = models.ForeignKey(Classe, verbose_name="classe",
			on_delete=models.CASCADE, related_name='trinomes')
	commentaire = models.TextField(blank=True)

	PERIODE_ANNEE = constantes.PERIODE_ANNEE
	PERIODE_PREMIERE = constantes.PERIODE_PREMIERE
	PERIODE_DEUXIEME = constantes.PERIODE_DEUXIEME
	PERIODE_CHOICES = constantes.PERIODE_CHOICES
	periode = models.SmallIntegerField(verbose_name="période",
			choices=PERIODE_CHOICES, default=PERIODE_ANNEE)

	def save(self, *args, **kwargs):
		self.annee = self.classe.annee
		super().save(*args, **kwargs)
		self.update_colles()

	def update_colles(self):
		Colle.objects.filter(groupe=self, etat__in=(
			Colle.ETAT_PREVUE, Colle.ETAT_BROUILLON)).synchro_trinome()

	class Meta:
		unique_together = ('annee', 'classe', 'periode', 'nom')

class Roulement(models.Model):
	"""
	Modèle qui permet de stocker la liste des colles que doit suivre un
	groupe fixé, dans l'ordre des semaines.
	"""
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
	creneaux = models.ManyToManyField(Creneau, through='RoulementLigne')

class RoulementLigne(models.Model):
	"""
	Un élément d'un Roulement
	"""
	roulement = models.ForeignKey(Roulement, on_delete=models.CASCADE,
			related_name='lignes')
	# On considère que l'ordre doit commencer à 0 dans la base de
	# données.
	ordre = models.PositiveSmallIntegerField()
	creneau = models.ForeignKey(Creneau, on_delete=models.CASCADE)

class RoulementApplication(models.Model):
	"""
	Application d'un roulement à une liste de trinômes sur un ensemble
	de semaines.
	"""
	roulement = models.ForeignKey(Roulement, on_delete=models.CASCADE,
			related_name='graines')
	semaines = models.ManyToManyField(Semaine, blank=True)
	trinomes = models.ManyToManyField(Trinome, through='RoulementGraineLigne')

	def generer_colles(self):
		pass

class RoulementGraineLigne(models.Model):
	application = models.ForeignKey(RoulementApplication,
			on_delete=models.CASCADE,
			related_name='lignes')
	trinome = models.ForeignKey(Trinome,
			on_delete=models.CASCADE, related_name='+')
	decalage = models.PositiveSmallIntegerField()

	class Meta:
		unique_together = ['trinome', 'application']

	def generer_colles(self):
		pass

class CollesReglages(models.Model):
	"""Sauvegarde des paramètres utilisés pour générer les semaines de
	colles."""
	classe = models.OneToOneField(Classe, on_delete=models.CASCADE,
			unique=True)
	numeros_auto = models.BooleanField(default=False,
			verbose_name="numérotation automatique")
	numeros_format = models.CharField(max_length=100, blank=True,
			default="{numero}", verbose_name="format des numéros")

	def clean(self):
		errors = {}

		if self.numeros_auto and not self.numeros_format:
			errors['numero_format'] = ValidationError("Le format de "
					"numérotation est obligatoire.", code='required')

		#durees_errors = []
		#for enseignement in self.durees.enseignement:
		#	if enseignement not in self.classe.enseignements:
		#		durees_errors.append(ValidationError("Vous ne pouvez "
		#			"pas sélectionner l'enseignement %(enseignement)s "
		#			"car il n'appartient pas à la classe %(classe)s.",
		#			code='invalid',
		#			params={'enseignement': enseignement,
		#				'classe': self.classe}))
		#if len(duree_errors) > 0:
		#	errors['durees'] = ValidationError(durees_errors)

		if len(errors) > 0:
			raise ValidationError(errors)
