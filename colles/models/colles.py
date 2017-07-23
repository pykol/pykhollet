# -*- coding:utf8 -*-
from django.db import models

from base.models.enseignement import Classe, Professeur, Matiere, Etudiant

# Liste des jours de la semaine, numérotation ISO
LISTE_JOURS = enumerate(["lundi", "mardi", "mercredi", "jeudi",
	"vendredi", "samedi", "dimanche"], 1)

class Semaine(models.Model):
	debut = models.DateField()
	fin = models.DateField()
	classe = models.ForeignKey(Classe)
	numero = models.TextField(verbose_name="Numéro")

	class Meta:
		ordering = ['debut']

	def __str__(self):
		return "{} ({}/{}-{}/{})".format(self.numero, self.debut.day,
				self.debut.month, self.fin.day, self.fin.month)

class Creneau(models.Model):
	jour = models.PositiveSmallIntegerField(choices=LISTE_JOURS)
	debut = models.TimeField()
	fin = models.TimeField()
	salle = models.CharField(max_length=30)
	colleur = models.ForeignKey(Professeur)
	matiere = models.ForeignKey(Matiere)
	classe = models.ForeignKey(Classe)

	class Meta:
		ordering = ['jour', 'debut', 'matiere']
		verbose_name = 'créneau'
		verbose_name_plural = 'créneaux'
	
	def __str__(self):
		return "{} {}-{}".format(self.jour, self.debut, self.fin)

class Colle(models.Model):
	creneau = models.ForeignKey(Creneau, null=True,
			on_delete=models.SET_NULL)
	horaire = models.DateTimeField()
	colleur = models.ForeignKey(Professeur)
	matiere = models.ForeignKey(Matiere)
	classe = models.ForeignKey(Classe)

	ETATS_COLLE = enumerate([
		"Prévue", "Notation en attente", "Notée", "Relevée", "Annulée"
		])
	etat = models.PositiveSmallIntegerField(verbose_name="État",
			choices=ETATS_COLLE)

class ColleNote(models.Model):
	colle = models.ForeignKey(Colle)
	eleve = models.ForeignKey(Etudiant)
	note = models.SmallIntegerField() #XXX
	horaire = models.DateField()

class ColleReleve(models.Model):
	colles = models.ManyToManyField(Colle)
