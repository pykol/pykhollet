# -*- coding:utf8 -*-
from django.db import models

from .utilisateurs import Professeur, Etudiant

class Annee(models.Model):
	nom = models.CharField(max_length=100)
	debut = models.DateField()
	fin = models.DateField()

	class Meta:
		ordering = ['debut']
		verbose_name = ['année scolaire']
		verbose_name_plural = ['années scolaires']

	def __str__(self):
		return self.nom

class Matiere(models.Model):
	nom = models.CharField(max_length=100)
	parent = models.ForeignKey('self', null=True, blank=True,
			on_delete=models.SET_NULL)

	class Meta:
		verbose_name = "matière"
		verbose_name_plural = "matières"

	def __str__(self):
		return self.nom

class Groupe(models.Model):
	nom = models.CharField(max_length=100)
	annee = models.ForeignKey(Annee, on_delete=models.CASCADE)
	etudiants = models.ManyToManyField(Etudiant)

	MODE_MANUEL = 0
	MODE_AUTOMATIQUE = 1
	mode = models.PositiveSmallIntegerField(choices=(
		(MODE_MANUEL, "manuel"),
		(MODE_AUTOMATIQUE, "automatique"),
		), default=MODE_MANUEL)

	enseignements = models.ManyToManyField('Enseignement')

	def __str__(self):
		return self.nom

class Service(models.Model):
	professeur = models.ForeignKey(Professeur, null=True, blank=True,
			on_delete=models.SET_NULL)
	enseignement = models.ForeignKey('Enseignement',
			on_delete=models.CASCADE)
	debut = models.DateField(null=True, blank=True,
			verbose_name="Date de début")
	fin = models.DateField(null=True, blank=True,
			verbose_name="Date de fin")

class Enseignement(models.Model):
	matiere = models.ForeignKey(Matiere, on_delete=models.SET_NULL,
			blank=True, null=True)
	classe = models.ForeignKey('Classe', on_delete=models.CASCADE)
	option = models.BooleanField()
	specialite = models.BooleanField()
	professeurs = models.ManyToManyField(Professeur, through=Service)

	class Meta:
		ordering = ['classe', 'matiere']
	
	def __str__(self):
		return "{} - {}".format(self.classe, self.matiere)

class Classe(Groupe):
	matieres = models.ManyToManyField(Matiere, through=Enseignement)
	coordonnateur = models.ForeignKey(Professeur,
			on_delete=models.SET_NULL, blank=True, null=True)

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
