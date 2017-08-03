# -*- coding:utf8 -*-
from django.db import models

from base.models.enseignement import Classe, Professeur, Matiere, Etudiant, Groupe
from base.notes import NoteField
from .conception import Creneau

# Liste des jours de la semaine, numérotation ISO
LISTE_JOURS = enumerate(["lundi", "mardi", "mercredi", "jeudi",
	"vendredi", "samedi", "dimanche"], 1)

class Colle(models.Model):
	creneau = models.ForeignKey(Creneau, blank=True, null=True,
			on_delete=models.SET_NULL)
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)

	ETATS = enumerate([
		"Prévue", "Notation en attente", "Notée", "Relevée", "Annulée"
		])
	etat = models.PositiveSmallIntegerField(verbose_name="état",
			choices=ETATS)

class ColleDetails(models.Model):
	colle = models.ForeignKey(Colle, on_delete=models.CASCADE)
	horaire = models.DateTimeField()
	salle = models.CharField(max_length=30)
	colleur = models.ForeignKey(Professeur, blank=True, null=True,
			on_delete=models.SET_NULL)
	matiere = models.ForeignKey(Matiere, blank=True, null=True,
			on_delete=models.SET_NULL)
	groupe = models.ForeignKey(Groupe, blank=True, null=True,
			on_delete=models.SET_NULL)
	eleves = models.ManyToManyField(Etudiant, blank=True)
	actif = models.BooleanField()

class ColleNote(models.Model):
	colle = models.ForeignKey(Colle, on_delete=models.CASCADE)
	eleve = models.ForeignKey(Etudiant)
	note = NoteField()
	horaire = models.DateTimeField()

class ColleReleve(models.Model):
	colles = models.ManyToManyField(Colle, blank=True)
