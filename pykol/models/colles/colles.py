# -*- coding:utf8 -*-
from django.db import models

from pykol.models.enseignement import Classe, Professeur, Matiere, Etudiant, Groupe
from pykol.notes import NoteField
from .conception import Creneau

# Liste des jours de la semaine, numérotation ISO
LISTE_JOURS = enumerate(["lundi", "mardi", "mercredi", "jeudi",
	"vendredi", "samedi", "dimanche"], 1)

class Colle(models.Model):
	creneau = models.ForeignKey(Creneau, blank=True, null=True,
			on_delete=models.SET_NULL, verbose_name="créneau")
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)

	ETATS = enumerate([
		"Prévue", "Notation en attente", "Notée", "Relevée", "Annulée"
		])
	etat = models.PositiveSmallIntegerField(verbose_name="état",
			choices=ETATS, default=0)
	matiere = models.ForeignKey(Matiere, blank=True, null=True,
			on_delete=models.SET_NULL, verbose_name="matière")
	groupe = models.ForeignKey(Groupe, blank=True, null=True,
			on_delete=models.SET_NULL, related_name='+')

class ColleDetails(models.Model):
	colle = models.ForeignKey(Colle, on_delete=models.CASCADE)
	horaire = models.DateTimeField()
	salle = models.CharField(max_length=30)
	colleur = models.ForeignKey(Professeur, blank=True, null=True,
			on_delete=models.SET_NULL)
	eleves = models.ManyToManyField(Etudiant, blank=True,
			verbose_name="élèves")
	actif = models.BooleanField(default=True)

	class Meta:
		verbose_name = "détails de la colle"
		verbose_name_plural = "détails de la colle"

class ColleNote(models.Model):
	colle = models.ForeignKey(Colle, on_delete=models.CASCADE)
	eleve = models.ForeignKey(Etudiant, on_delete=models.CASCADE)
	note = NoteField()
	horaire = models.DateTimeField()

	class Meta:
		verbose_name = "note de colle"
		verbose_name_plural = "notes de colle"

class ColleReleve(models.Model):
	colles = models.ManyToManyField(Colle, blank=True)

	class Meta:
		verbose_name = "relevé des colles"
		verbose_name_plural = "relevés des colles"
