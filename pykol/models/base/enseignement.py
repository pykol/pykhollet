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

from django.db import models

from .annee import Annee
from .utilisateurs import Professeur, Etudiant

class Matiere(models.Model):
	"""
	Matière enseignée dans l'établissement

	Ce modèle représente une unité d'enseignement telle qu'elle apparait
	dans l'emploi du temps des élèves. On peut regrouper dans une même
	matière plusieurs contenus différents (par exemple, la matière
	« mathématiques » pourra être utilisée pour les enseignements aussi
	bien en MPSI qu'en ECE).

	Une matière ne dépend d'aucune année scolaire, car on peut la
	retrouver à l'identique d'une année à l'autre.

	Il est possible de créer une hiérarchie de matières, par exemple
	pour distinguer une même langue enseignée en tant que LV1 ou en tant
	que LV2 et regrouper toutes les LV1 sous une même matière, et toutes
	les LV2 d'autre part. Ceci permettra ensuite d'exprimer, lors de la
	création d'une classe, le fait que tout étudiant doit avoir une
	LV1 à choisir parmi une liste donnée.

	La hiérarchie entre matières permet également de regrouper des
	enseignements partagés entre plusieurs disciplines, par exemple la
	culture générale en CPGE économique et commerciale est partagée
	entre un cours de lettres et un cours de philosophie.
	"""
	nom = models.CharField(max_length=100)
	parent = models.ForeignKey('self', null=True, blank=True,
			on_delete=models.SET_NULL)
	virtuelle = models.BooleanField()

	class Meta:
		verbose_name = "matière"
		verbose_name_plural = "matières"

	def __str__(self):
		if self.parent:
			return '{parent} - {current}'.format(parent=self.parent.nom,
					current=self.nom)
		else:
			return self.nom

class Groupe(models.Model):
	"""
	Groupe d'élèves

	Un groupe représente un ensemble d'élèves. Les motifs de créations
	de ces groupes peuvent être divers : un groupe de colles dans un
	colloscope, une classe entière, une partie de classe ayant choisi
	une option spécifique, un groupe partagé entre deux classes et
	suivant un enseignement commun, etc.

	Certains groupes sont créés automatiquement et leur composition est
	gérée par d'autres modèles. Dans ce cas, il n'est pas possible
	de modifier manuellement la liste des étudiants du groupe. Il faut
	pour cela passer par le modèle qui a créé le groupe.
	"""
	nom = models.CharField(max_length=100)
	annee = models.ForeignKey(Annee, on_delete=models.CASCADE,
			verbose_name="année")
	etudiants = models.ManyToManyField(Etudiant, blank=True,
			verbose_name="étudiants")
	slug = models.SlugField()

	MODE_MANUEL = 0
	MODE_AUTOMATIQUE = 1
	mode = models.PositiveSmallIntegerField(choices=(
		(MODE_MANUEL, "manuel"),
		(MODE_AUTOMATIQUE, "automatique"),
		), default=MODE_MANUEL)

	def __str__(self):
		return self.nom

class Service(models.Model):
	"""
	Service d'enseignement

	Ce modèle permet d'affecter un professeur donné pour réaliser un
	enseignement dans une classe.

	Un même enseignement peut être assuré par plusieurs professeurs, par
	exemple dans le cas de l'enseignement commun d'informatique qui peut
	être partagé entre plusieurs professeurs pendant l'année, ou encore
	lorsqu'un professeur remplace un autre.

	Il existe une instance de ce modèle pour chaque intervention d'un
	professeur sur un enseignement.
	"""
	professeur = models.ForeignKey(Professeur, null=True, blank=True,
			on_delete=models.SET_NULL)
	enseignement = models.ForeignKey('Enseignement',
			on_delete=models.CASCADE)
	debut = models.DateField(null=True, blank=True,
			verbose_name="Date de début")
	fin = models.DateField(null=True, blank=True,
			verbose_name="Date de fin")

class Enseignement(models.Model):
	"""
	Enseignement dispensé devant un groupe d'élèves

	Un enseignement correspond à l'ensemble des heures de cours
	dispensées par un (ou plusieurs) professeurs devant un groupe
	d'élèves fixé, dans une matière fixée.

	Chaque enseignement est attribué à un groupe, et non à une classe
	d'élèves, afin de permettre la création d'enseignements en barrette
	sur plusieurs classes.

	Les professeurs sont affectés aux enseignements grâce au modèle
	:model:`pykol.Service`.
	"""
	matiere = models.ForeignKey(Matiere, on_delete=models.SET_NULL,
			blank=True, null=True, verbose_name="matière",
			limit_choices_to={'virtuelle': False,})
	groupe = models.ForeignKey('Groupe', on_delete=models.CASCADE,
			related_name='+')
	option = models.BooleanField()
	specialite = models.BooleanField(verbose_name="spécialité")
	professeurs = models.ManyToManyField(Professeur, through=Service)

	class Meta:
		ordering = ['groupe', 'matiere']
	
	def __str__(self):
		return "{} - {}".format(self.groupe, self.matiere)

class ProfClasseManager(models.Manager):
	def get_queryset(self):
		pass
		Classe.objects.filter(enseignements__service__professeur=prof)

class Classe(Groupe):
	"""
	Classe

	Groupe de référence pour chaque élève, auquel il appartient durant
	toute l'année scolaire. La classe est l'unité qui permet d'organiser
	l'emploi du temps avec la liste des matières dispensées (et les
	enseignements correspondants), le colloscope, les conseils de classe.
	"""
	enseignements = models.ManyToManyField(Enseignement, blank=True)
	coordonnateur = models.ForeignKey(Professeur,
			on_delete=models.SET_NULL, blank=True, null=True)
	code_structure = models.CharField(max_length=20, unique=True)
	code_mef = models.CharField(max_length=11)

	NIVEAU_PREMIERE_ANNEE = 1
	NIVEAU_DEUXIEME_ANNEE = 2
	niveau = models.PositiveSmallIntegerField(choices=(
		(NIVEAU_PREMIERE_ANNEE, "1è année"),
		(NIVEAU_DEUXIEME_ANNEE, "2è année"),
		))

	class Meta:
		ordering = ['annee', 'niveau', 'nom']
	
	def __str__(self):
		return self.nom
