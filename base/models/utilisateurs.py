# -*- coding:utf8 -*-
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

from .etablissement import Etablissement, validateur_lettre23

class User(AbstractUser):
	SEXE_HOMME=1
	SEXE_FEMME=2
	sexe = models.PositiveSmallIntegerField(choices=(
		(SEXE_HOMME, 'homme'),
		(SEXE_FEMME, 'femme'),
		), default=SEXE_HOMME)

	REQUIRED_FIELDS = ['sexe',]

class Etudiant(User):
	origine = models.ForeignKey(Etablissement,
			blank=True, null=True,
			verbose_name="Établissement d'origine",
			on_delete=models.SET_NULL)
	classe = models.ForeignKey('Classe', on_delete=models.PROTECT)
	entree = models.DateField(null=True, blank=True)
	sortie = models.DateField(null=True, blank=True)
	#XXX sensibilité à la casse de la lettre code INE
	ine = models.CharField(max_length=11,
			verbose_name="INE (numéro d'étudiant)",
			validators=[RegexValidator(regex='\d{10,10}[a-z][A-Z]', message="Un numéro INE doit être constitué de dix chiffres suivis d'une lettre code"), validateur_lettre23])
	options = models.ManyToManyField('Matiere')

	class Meta:
		verbose_name = "étudiant"
		verbose_name_plural = "étudiants"
		unique_together = ['ine']

class Professeur(User):
	CORPS_AUTRE = 0
	CORPS_CERTIFIE = 1
	CORPS_AGREGE = 2
	CORPS_CHAIRESUP = 3
	LISTE_CORPSS = (
			(CORPS_AUTRE, "autre"),
			(CORPS_CERTIFIE, "certifié"),
			(CORPS_AGREGE, "agrégé"),
			(CORPS_CHAIRESUP, "chaire supérieure"),
		)
	corps = models.PositiveSmallIntegerField(choices=LISTE_CORPSS,
			default=2)
	etablissement = models.ForeignKey(Etablissement, null=True,
			blank=True, on_delete=models.SET_NULL)

	class Meta:
		verbose_name = "professeur"
		verbose_name_plural = "professeurs"
