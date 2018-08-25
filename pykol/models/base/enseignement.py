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
from django.urls import reverse

from .annee import Annee
from .utilisateurs import Professeur, Etudiant

class Matiere(models.Model):
	"""
	Matière enseignée dans l'établissement

	Ce modèle représente une unité d'enseignement telle qu'elle apparait
	dans l'emploi du temps des étudiants. On peut regrouper dans une même
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
			on_delete=models.SET_NULL, related_name='filles')
	virtuelle = models.BooleanField()
	code_matiere = models.CharField(max_length=20, null=False,
			blank=True, unique=True)

	class Meta:
		verbose_name = "matière"
		verbose_name_plural = "matières"

	def __str__(self):
		if self.parent:
			return '{parent} - {current}'.format(parent=self.parent.nom,
					current=self.nom)
		else:
			return self.nom

class GroupeEffectif(models.Model):
	"""
	Appartenance d'un groupe à une classe, en donnant la part de
	l'effectif du groupe qui est dans cette classe tel qu'il est indiqué
	dans l'export STS.
	"""
	groupe = models.ForeignKey('Groupe', on_delete=models.CASCADE)
	classe = models.ForeignKey('Classe', on_delete=models.CASCADE,
			related_name='+')
	effectif_sts = models.PositiveSmallIntegerField(blank=True, null=True)

class AbstractBaseGroupe(models.Model):
	"""
	Classe qui fournit les champs de base pour manipuler des listes
	d'étudiants.
	"""
	nom = models.CharField(max_length=100)
	annee = models.ForeignKey(Annee, on_delete=models.CASCADE,
			verbose_name="année")
	etudiants = models.ManyToManyField(Etudiant, blank=True,
			verbose_name="étudiants")
	slug = models.SlugField()

	class Meta:
		abstract = True

	def __str__(self):
		return self.nom

	@property
	def emails(self):
		"""
		Liste des e-mails des étudiants du groupe
		"""
		return list(self.etudiants.filter(email__isnull=False
				).values_list('email', flat=True))


class Groupe(AbstractBaseGroupe):
	"""
	Groupe d'étudiants

	Un groupe représente un ensemble d'étudiants. Les motifs de créations
	de ces groupes peuvent être divers : un groupe de colles dans un
	colloscope, une classe entière, une partie de classe ayant choisi
	une option spécifique, un groupe partagé entre deux classes et
	suivant un enseignement commun, etc.

	Certains groupes sont créés automatiquement et leur composition est
	gérée par d'autres modèles. Dans ce cas, il n'est pas possible
	de modifier manuellement la liste des étudiants du groupe. Il faut
	pour cela passer par le modèle qui a créé le groupe.
	"""
	MODE_MANUEL = 0
	MODE_AUTOMATIQUE = 1
	mode = models.PositiveSmallIntegerField(choices=(
		(MODE_MANUEL, "manuel"),
		(MODE_AUTOMATIQUE, "automatique"),
		), default=MODE_MANUEL)

	effectif_sts = models.PositiveSmallIntegerField(blank=True,
			null=True)

	classes_appartenance = models.ManyToManyField('Classe', through=GroupeEffectif)

	class Meta:
		unique_together = ('nom', 'annee')

	def update_etudiants(self):
		"""Méthode de mise à jour de la composition du groupe.

		Lorsque le mode d'un groupe vaut MODE_MANUEL, la composition du
		groupe est renseignée manuellement par les utilisateurs.

		Lorsque ce mode vaut MODE_AUTOMATIQUE, la composition du groupe
		est générée automatiquement par pyKol grâce à un appel à la
		méthode update_etudiants.

		La méthode de base Groupe.update_etudiants ne fait rien du tout.
		Cette méthode doit être surchargée par les modèles qui héritent
		de Groupe, afin de mettre à jour les étudiants automatiquement
		en fonction des contraintes spécifiques de ces modèles.
		"""
		pass

	@property
	def effectif(self):
		"""
		Calcul de l'effectif du groupe. Quand la liste des étudiants est
		renseignée, on renvoie le nombre d'étudiants d'après ce champ.
		Cependant, il arrive que la liste des étudiants ne soit pas
		disponible (car pas renseignée dans SIECLE ou STS) mais que
		l'effectif soit indiqué dans l'export STS. Si cet effectif a été
		stocké dans le champ effectif_sts, on renvoie sa valeur.
		"""
		if self.etudiants.all():
			return self.etudiants.count()
		else:
			return self.effectif_sts or 0

	def effectif_classe(self, classe=None):
		"""
		Renvoie l'effectif de la partie du groupe qui appartient à la
		classe donnée en paramètre. Cet effectif est calculé d'après la
		composition du groupe, si elle est renseignée, ou bien d'après
		les données importées de STS.
		"""
		if self.etudiants.all():
			return self.etudiants.filter(classe=classe).count()
		else:
			return self.groupeeffectif_set.get(classe=classe).effectif_sts or 0

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
	Enseignement dispensé devant un groupe d'étudiants

	Un enseignement correspond à l'ensemble des heures de cours
	dispensées par un (ou plusieurs) professeurs devant un groupe
	d'étudiants fixé, dans une matière fixée.

	Chaque enseignement est attribué à un groupe, et non à une classe
	d'étudiants, afin de permettre la création d'enseignements en barrette
	sur plusieurs classes.

	Les professeurs sont affectés aux enseignements grâce au modèle
	:model:`pykol.Service`.
	"""
	matiere = models.ForeignKey(Matiere, on_delete=models.SET_NULL,
			blank=True, null=True, verbose_name="matière",
			limit_choices_to={'virtuelle': False,})
	groupe = models.ForeignKey('Groupe', on_delete=models.CASCADE)
	option = models.BooleanField()
	specialite = models.BooleanField(verbose_name="spécialité")
	professeurs = models.ManyToManyField(Professeur, through=Service)

	PERIODE_ANNEE = 0
	PERIODE_PREMIERE = 1
	PERIODE_DEUXIEME = 2
	PERIODE_CHOICES = (
			(PERIODE_ANNEE, 'année complète'),
			(PERIODE_PREMIERE, 'première période'),
			(PERIODE_DEUXIEME, 'deuxième période'),
		)
	periode = models.PositiveSmallIntegerField(verbose_name="période",
			choices=PERIODE_CHOICES,
			default=PERIODE_ANNEE)

	class Meta:
		ordering = ['groupe', 'matiere']

	def __str__(self):
		return "{} - {}".format(self.groupe, self.matiere)

	def etudiants_classe(self, classe):
		"""
		Renvoie la liste des étudiants qui suivent cet enseignement et
		qui sont présents également dans la classe donnée.
		"""
		return self.groupe.etudiants.filter(classe=classe)

class ProfClasseManager(models.Manager):
	def get_queryset(self):
		pass
		Classe.objects.filter(enseignements__service__professeur=prof)

class ModuleElementaireFormation(models.Model):
	"""
	MEF
	"""
	code_mef = models.CharField(max_length=11)
	matieres = models.ManyToManyField(Matiere, through='MEFMatiere')
	libelle = models.CharField(max_length=100)

	def __str__(self):
		return self.code_mef

class MEFMatiere(models.Model):
	"""
	Appartenance d'une matière à un MEF
	"""
	matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE)
	mef = models.ForeignKey(ModuleElementaireFormation,
			on_delete=models.CASCADE)
	mode_election = models.CharField(max_length=10)
	rang = models.SmallIntegerField()

class ClasseAnneeActuelleManager(models.Manager):
	"""
	Manager de Classe qui ne donne accès qu'aux classes de l'année en
	cours.
	"""
	def get_queryset(self):
		return super().get_queryset().filter(annee=Annee.objects.get_actuelle())

class Classe(Groupe):
	"""
	Classe

	Groupe de référence pour chaque étudiant, auquel il appartient durant
	toute l'année scolaire. La classe est l'unité qui permet d'organiser
	l'emploi du temps avec la liste des matières dispensées (et les
	enseignements correspondants), le colloscope, les conseils de classe.
	"""
	enseignements = models.ManyToManyField(Enseignement, blank=True)
	coordonnateur = models.ForeignKey(Professeur,
			on_delete=models.SET_NULL, blank=True, null=True)
	code_structure = models.CharField(max_length=20, unique=True)
	mef = models.ForeignKey(ModuleElementaireFormation,
			on_delete=models.CASCADE)

	# On instancie le manager par défaut et un manager qui ne donne
	# accès qu'aux classes de l'année en cours.
	all_objects = models.Manager()
	objects = ClasseAnneeActuelleManager()

	NIVEAU_PREMIERE_ANNEE = 1
	NIVEAU_DEUXIEME_ANNEE = 2
	niveau = models.PositiveSmallIntegerField(choices=(
		(NIVEAU_PREMIERE_ANNEE, "1è année"),
		(NIVEAU_DEUXIEME_ANNEE, "2è année"),
		))

	class Meta:
		ordering = ['annee', 'niveau', 'nom']
		permissions = (
			('change_colloscope', "Modification du colloscope de la classe"),
			('view_colloscope', "Consultation du colloscope de la classe"),
		)

	def __str__(self):
		return self.nom

	def update_etudiants(self):
		"""Mise à jour de la composition du groupe.

		Le modèle Etudiant contient une clé étrangère vers le modèle
		Classe, qui indique pour chaque étudiant à quelle classe il
		appartient.

		Cette méthode met à jour le champ etudiants (hérité du modèle
		Groupe) afin que la liste des étudiants corresponde
		effectivement aux étudiants qui pointent vers cette classe.
		"""
		self.etudiants.set(Etudiant.objects.filter(classe=self))

	def get_absolute_url(self):
		return reverse('classe_detail', args=(self.slug,))

	def get_nb_semaines_colles(self):
		if self.niveau == Classe.NIVEAU_PREMIERE_ANNEE:
			return 30
		return 25

	def get_nb_trimestres_colles(self):
		if self.niveau == Classe.NIVEAU_PREMIERE_ANNEE:
			return 3
		return 2

	def profs_de(self, matiere):
		"""
		Renvoie la liste des professeurs qui enseignent la matière
		donnée dans cette classe.
		"""
		return Professeur.objects.filter(service__enseignement__classe=self,
				service__enseignement__matiere=matiere)
