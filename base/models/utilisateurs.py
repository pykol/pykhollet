# -*- coding:utf8 -*-

import re

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator

from base.uppercasecharfield import Lettre23Field
from .etablissement import Etablissement

class User(AbstractUser):
	"""
	Compte utilisateur de pyKol

	Ce modèle reprend le modèle de base de Django pour les utilisateurs,
	en ajoutant un champ supplémentaire pour stocker le sexe de
	l'utilisateur. Cette information est toujours nécessaire pour les
	traitements administratifs des différentes catégories
	d'utilisateurs.
	"""
	SEXE_HOMME=1
	SEXE_FEMME=2
	sexe = models.PositiveSmallIntegerField(choices=(
		(SEXE_HOMME, 'homme'),
		(SEXE_FEMME, 'femme'),
		), default=SEXE_HOMME)

	REQUIRED_FIELDS = ['email', 'sexe',]

	def civilite(self, abrege=True):
		if self.sexe == SEXE_HOMME:
			if abrege:
				return 'M.'
			else:
				return 'Monsieur'

		if self.sexe == SEXE_FEMME:
			if abrege:
				return 'Mme'
			else:
				return 'Madame'

	def __str__(self):
		nom = '{last} {first}'.format(last=self.last_name.upper(),
				first=self.first_name)
		if nom.strip():
			return nom
		else:
			return '({})'.format(self.username)

	def short_display_name(self):
		return '{initials} {last_name}'.format(
				initials=re.sub(r'(\w)\w*', r'\1.', self.first_name),
				last_name=self.last_name.upper())

class Etudiant(User):
	"""
	Étudiant inscrit dans l'établissement
	"""
	origine = models.ForeignKey(Etablissement,
			blank=True, null=True,
			verbose_name="Établissement d'origine",
			on_delete=models.SET_NULL)
	classe = models.ForeignKey('Classe', on_delete=models.PROTECT)
	entree = models.DateField(null=True, blank=True,
			verbose_name="entrée")
	sortie = models.DateField(null=True, blank=True)
	ine = Lettre23Field(length=11, verbose_name="INE (numéro d'étudiant)")
	options = models.ManyToManyField('Matiere', blank=True)

	class Meta:
		verbose_name = "étudiant"
		verbose_name_plural = "étudiants"
		unique_together = ['ine']

	def clean(self):
		super().clean()
		if not self.entree:
			self.entree = self.classe.annee.debut

class Professeur(User):
	"""
	Professeur intervenant dans l'établissement

	Ce modèle peut servir à représenter aussi bien les professeurs
	affectés à l'établissement que les intervenants extérieurs. Le
	statut est précisé grâce au champ corps.
	"""
	CORPS_AUTRE = 0
	CORPS_CERTIFIE = 1
	CORPS_AGREGE = 2
	CORPS_CHAIRESUP = 3
	LISTE_CORPS = (
			(CORPS_AUTRE, "autre"),
			(CORPS_CERTIFIE, "certifié"),
			(CORPS_AGREGE, "agrégé"),
			(CORPS_CHAIRESUP, "chaire supérieure"),
		)
	corps = models.PositiveSmallIntegerField(choices=LISTE_CORPS,
			default=2)
	etablissement = models.ForeignKey(Etablissement, null=True,
			blank=True, on_delete=models.SET_NULL,
			verbose_name="établissement")

	class Meta:
		verbose_name = "professeur"
		verbose_name_plural = "professeurs"
