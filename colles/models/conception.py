# -*- coding:utf8 -*-
from django.db import models
from django.db.models import Q, F
from django.core.exceptions import ValidationError

from base.models import Classe, Professeur, Matiere, Groupe, \
		Enseignement

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

	def save(self, *args, **kwargs):
		self.annee = self.dans_classe.annee
		super().save(*args, **kwargs)

class Roulement(models.Model):
	classe = models.ForeignKey(Classe, on_delete=models.CASCADE)
	semaines = models.ManyToManyField(Semaine, blank=True)

	#def clean(self):
	#	errors = []
	#	for semaine in self.semaines:
	#		if semaine.classe != self.classe:
	#			errors.append(ValidationError("Vous ne pouvez pas "
	#			"sélectionner la semaine %(semaine)s car elle "
	#			"n'appartient pas à la classe %(classe)s.",
	#			code='invalid',
	#			params={'semaine': semaine,
	#				'classe': self.classe,}))
	#	if len(errors) > 0:
	#		raise ValidationError({'semaines': errors})

class RoulementLigne(models.Model):
	ordre = models.PositiveSmallIntegerField()
	creneau = models.ForeignKey(Creneau, on_delete=models.CASCADE)
	roulement = models.ForeignKey(Roulement, on_delete=models.CASCADE,
			related_name="lignes")

class RoulementGraine(models.Model):
	trinomes = models.ManyToManyField(Trinome)

class CollesParMatiere(models.Model):
	enseignement = models.ForeignKey(Enseignement, on_delete=models.CASCADE)
	reglages = models.ForeignKey('CollesReglages',
			on_delete=models.CASCADE)
	duree = models.PositiveSmallIntegerField(verbose_name="durée hebdomadaire")

class CollesReglages(models.Model):
	classe = models.OneToOneField(Classe, on_delete=models.CASCADE)
	numeros_auto = models.BooleanField(default=False,
			verbose_name="numérotation automatique")
	numeros_format = models.CharField(max_length=100, blank=True,
			default="{numero}", verbose_name="format des numéros")
	durees = models.ManyToManyField(Enseignement, through=CollesParMatiere)

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

	class Meta:
		unique_together = ('classe',)
