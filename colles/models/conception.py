# -*- coding:utf8 -*-
from django.db import models
from django.db.models import Q, F
from django.core.exceptions import ValidationError

from base.models import Classe, Professeur, Matiere, Groupe

# Liste des jours de la semaine, numérotation ISO
LISTE_JOURS = enumerate(["lundi", "mardi", "mercredi", "jeudi",
	"vendredi", "samedi", "dimanche"], 1)

class Semaine(models.Model):
	debut = models.DateField(verbose_name="début")
	fin = models.DateField()
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
	numero = models.TextField(verbose_name="numéro")

	class Meta:
		ordering = ['debut']

	def __str__(self):
		return "{} ({}/{}-{}/{})".format(self.numero, self.debut.day,
				self.debut.month, self.fin.day, self.fin.month)

class Creneau(models.Model):
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
	jour = models.PositiveSmallIntegerField(choices=LISTE_JOURS)
	debut = models.TimeField(verbose_name="début")
	fin = models.TimeField()
	salle = models.CharField(max_length=30, blank=True)
	colleur = models.ForeignKey(Professeur, blank=True, null=True,
			on_delete=models.SET_NULL)
	matiere = models.ForeignKey(Matiere, blank=True, null=True,
			on_delete=models.SET_NULL, verbose_name="matière")

	class Meta:
		ordering = ['jour', 'debut', 'matiere']
		verbose_name = 'créneau'
		verbose_name_plural = 'créneaux'
	
	def __str__(self):
		return "{} {:%H:%M}-{:%H:%M}".format(self.get_jour_display(), self.debut, self.fin)

class Trinome(Groupe):
	dans_classe = models.ForeignKey(Classe, verbose_name="classe",
			on_delete=models.CASCADE, related_name='trinomes')
	commentaire = models.TextField(blank=True)

class Roulement(models.Model):
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
	semaines = models.ManyToManyField(Semaine, blank=True)

	def clean(self):
		for semaine_classe in self.semaines.classe:
			if semaine_classe != self.classe:
				raise ValidationError() #XXX

class RoulementLigne(models.Model):
	ordre = models.PositiveSmallIntegerField()
	creneau = models.ForeignKey(Creneau, on_delete=models.CASCADE)
	roulement = models.ForeignKey(Roulement, on_delete=models.CASCADE,
			related_name="lignes")

class RoulementGraine(models.Model):
	trinomes = models.ManyToManyField(Trinome)
