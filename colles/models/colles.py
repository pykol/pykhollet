# -*- coding:utf8 -*-
from django.db import models

from base.models.enseignement import Classe, Professeur, Matiere, Etudiant
from .conception import Creneau

# Liste des jours de la semaine, numérotation ISO
LISTE_JOURS = enumerate(["lundi", "mardi", "mercredi", "jeudi",
	"vendredi", "samedi", "dimanche"], 1)

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
	etat = models.PositiveSmallIntegerField(verbose_name="état",
			choices=ETATS_COLLE)

class ColleNote(models.Model):
	colle = models.ForeignKey(Colle)
	eleve = models.ForeignKey(Etudiant)
	note = models.SmallIntegerField() #XXX
	horaire = models.DateField()

class ColleReleve(models.Model):
	colles = models.ManyToManyField(Colle)
